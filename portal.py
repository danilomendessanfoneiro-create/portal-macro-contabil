import streamlit as st
import pandas as pd
import json
import os
import glob
import plotly.express as px

st.set_page_config(layout="wide", page_title="Portal BI - Macro Contábil")

# Configurações Visuais
colors = {
    "faturamento": "#38bdf8",
    "custos": "#475569",
    "texto": "white"
}

# Banco de Dados de Usuários
usuarios_db = {
    "Danilo": {"senha": "ABCdef123!", "cnpj": "44796416000133", "nome": "Danilo"},
    "Tamara53786": {"senha": "ABCdef123!", "cnpj": "53786069000159", "nome": "Tamara"},
    "Edirsabino": {"senha": "ABCdef123!", "cnpj": "41721197000135", "nome": "Edir Sabino"},
    "GSPrest": {"senha": "ABCdef123!", "cnpj": "31958666000180", "nome": "GS Prest"},
    "HamiltonAdriano": {"senha": "ABCdef123!", "cnpj": "00000000000000", "nome": "Hamilton Adriano"},
    "Paulaes": {"senha": "ABCdef123!", "cnpj": "21805265000137", "nome": "Paula ES"},
    "Solution": {"senha": "ABCdef123!", "cnpj": "22834381000147", "nome": "Solution"},
    "Tptransporte": {"senha": "ABCdef123!", "cnpj": "59001330000144", "nome": "TP Transporte"}
}

# Funções de Formatação
def format_br(valor):
    return f"R$ {valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

def format_pct(valor):
    return f"{valor*100:.2f}%".replace(".", ",")

def comp_br(c):
    return f"{c[4:6]}/{c[:4]}"

# ---------------- LEITOR OTIMIZADO COM CACHE POR ARQUIVO ----------------

@st.cache_data(show_spinner=False)
def ler_json_arquivo(file, mtime):
    """
    O Streamlit usa o 'mtime' (data de modificação) como chave. 
    Se o arquivo mudar no disco, ele reprocessa automaticamente.
    """
    try:
        with open(file, "r", encoding="utf-8") as f:
            js = json.load(f)

        if isinstance(js, dict):
            res = js.get("result", js)
        elif isinstance(js, list):
            res = js
        else:
            res = []

        data = []
        if isinstance(res, list):
            data.extend(res)
        elif isinstance(res, dict):
            if "documentos" in res: data.extend(res["documentos"])
            elif "recibos" in res: data.extend(res["recibos"])
            elif "totais" in res: data.extend(res["totais"])
            else: data.append(res)

        df = pd.DataFrame(data)
        if not df.empty:
            # Limpa nomes de colunas (ex: 'documento.valorTotal' vira 'valorTotal')
            df.columns = [c.split(".")[-1] for c in df.columns]
        return df
    except Exception:
        return pd.DataFrame()

def ler_pasta(path):
    files = glob.glob(path)
    dfs = []
    for f in files:
        mtime = os.path.getmtime(f) # Captura a data/hora do arquivo
        dfs.append(ler_json_arquivo(f, mtime))
    
    if dfs:
        return pd.concat(dfs, ignore_index=True)
    return pd.DataFrame()

# ---------------- LÓGICA DE PROCESSAMENTO ----------------

def carregar_dados(cnpj, comp):
    pasta = "dados_powerbi"

    df_f = ler_pasta(os.path.join(pasta, "notas_detalhe", f"*{cnpj}_{comp}.json"))
    df_d = ler_pasta(os.path.join(pasta, "folha_recibos_totais", f"*{cnpj}_{comp}.json"))
    df_a = ler_pasta(os.path.join(pasta, "resumo_apuracao", f"*{cnpj}_{comp}.json"))
    df_t = ler_pasta(os.path.join(pasta, "totais_faturamento", f"*{cnpj}_{comp}.json"))

    vals = {"fat":0,"ent":0,"fgts":0,"inss":0,"sn":0,"f_liq":0,"f_tot":0}

    # --- FATURAMENTO / ENTRADAS (DETALHADO) ---
    if not df_f.empty and "tipoMovimento" in df_f.columns:
        df_f["valorTotal"] = pd.to_numeric(df_f.get("valorTotal", 0), errors="coerce").fillna(0)
        df_f["tipoMovimento"] = df_f["tipoMovimento"].astype(str).str.strip()
        
        vals["fat"] = df_f[df_f["tipoMovimento"].isin(["Prestado", "Saída"])]["valorTotal"].sum()
        vals["ent"] = df_f[df_f["tipoMovimento"].isin(["Entrada", "Tomado"])]["valorTotal"].sum()

    # --- FALLBACK PARA TOTAIS (Se o detalhado estiver zerado) ---
    if vals["fat"] == 0 and not df_t.empty:
        df_t["valorTotal"] = pd.to_numeric(df_t.get("valorTotal", 0), errors="coerce").fillna(0)
        
        # Limpeza e Filtro de Situação (Garante que só pega notas válidas)
        for col in ["situacao", "tipoMovimento"]:
            if col in df_t.columns:
                df_t[col] = df_t[col].astype(str).str.strip()

        df_emit = df_t[df_t.get("situacao") == "Emitido"] if "situacao" in df_t.columns else df_t
        
        if "tipoMovimento" in df_emit.columns:
            vals["fat"] = df_emit[df_emit["tipoMovimento"].isin(["Prestado", "Saída"])]["valorTotal"].sum()
            vals["ent"] = df_emit[df_emit["tipoMovimento"].isin(["Entrada", "Tomado"])]["valorTotal"].sum()

    # --- FOLHA DE PAGAMENTO ---
    if not df_d.empty:
        vals["f_liq"] = df_d.get("totalLiquido", 0).sum()
        vals["fgts"] = df_d.get("valorFGTS", 0).sum()
        vals["inss"] = df_d.get("INSSSegurado", 0).sum()
        vals["f_tot"] = df_d.get("totalProventos", 0).sum()

    # --- SIMPLES NACIONAL ---
    if not df_a.empty:
        # Segurança: Verifica se há dados antes de acessar a linha 0
        try:
            vals["sn"] = df_a.iloc[0].get("TOTAL_APURADO", 0)
        except:
            vals["sn"] = 0

    # --- CÁLCULOS FINAIS ---
    vals["res"] = vals["fat"] - (vals["ent"] + vals["f_liq"] + vals["inss"] + vals["fgts"])
    vals["al_fgts"] = vals["fgts"] / vals["f_tot"] if vals["f_tot"] > 0 else 0
    vals["al_inss"] = vals["inss"] / vals["f_tot"] if vals["f_tot"] > 0 else 0
    vals["al_sn"] = vals["sn"] / vals["fat"] if vals["fat"] > 0 else 0

    return vals

def carregar_historico(cnpj, lista_comps):
    hist = []
    for c in lista_comps:
        v = carregar_dados(cnpj, c)
        hist.append({
            "Competência": comp_br(c),
            "Faturamento": v["fat"],
            "Custos": v["ent"] + v["f_tot"] + v["sn"]
        })
    return pd.DataFrame(hist)

# ---------------- INTERFACE (LOGIN) ----------------

if "auth" not in st.session_state:
    st.session_state.auth = False

if not st.session_state.auth:
    st.title("Portal Macro Contábil")
    user_input = st.text_input("Usuário")
    senha_input = st.text_input("Senha", type="password")

    if st.button("Entrar"):
        if user_input in usuarios_db and usuarios_db[user_input]["senha"] == senha_input:
            st.session_state.auth = True
            st.session_state.user = usuarios_db[user_input]
            st.rerun()
        else:
            st.error("Usuário ou senha inválidos")
    st.stop()

# ---------------- DASHBOARD PRINCIPAL ----------------

user = st.session_state.user
comps = ["202601", "202602", "202603", "202604", "202605"]

with st.sidebar:
    st.title("Macro Contábil")
    st.write(f"Bem-vindo **{user['nome']}**")
    comp = st.selectbox("Competência", comps, format_func=lambda x: comp_br(x))
    if st.button("Sair"):
        st.session_state.auth = False
        st.rerun()

# Carregamento dos dados do mês selecionado
dados = carregar_dados(user["cnpj"], comp)

st.title(user["nome"])
st.subheader("Análise Contábil Preliminar")

# Primeira Linha de Métricas
c1, c2, c3, c4 = st.columns(4)
c1.metric("Faturamento Total", format_br(dados["fat"]))
c2.metric("Entradas/Compras", format_br(dados["ent"]))
c3.metric("Folha Líquida", format_br(dados["f_liq"]))
c4.metric("Resultado Estimado", format_br(dados["res"]))

# Segunda Linha de Métricas (Impostos e Custo Folha)
c1, c2, c3, c4 = st.columns(4)
c1.metric("FGTS", format_br(dados["fgts"]), format_pct(dados["al_fgts"]))
c2.metric("INSS", format_br(dados["inss"]), format_pct(dados["al_inss"]))
c3.metric("Simples Nacional", format_br(dados["sn"]), format_pct(dados["al_sn"]))
c4.metric("Custo Total Folha", format_br(dados["f_tot"]))

st.divider()

# Gráfico de Evolução
st.subheader("📊 Evolução Mensal (Faturamento vs Custos)")
df_hist = carregar_historico(user["cnpj"], comps)

fig = px.bar(
    df_hist,
    x="Competência",
    y=["Faturamento", "Custos"],
    barmode="group",
    color_discrete_map={"Faturamento": colors["faturamento"], "Custos": colors["custos"]},
    text_auto=".2s"
)

fig.update_layout(
    legend_title_text="",
    xaxis_title="",
    yaxis_title="Valor (R$)",
    plot_bgcolor="rgba(0,0,0,0)",
    paper_bgcolor="rgba(0,0,0,0)",
    font_color="white",
    height=400
)

st.plotly_chart(fig, use_container_width=True)