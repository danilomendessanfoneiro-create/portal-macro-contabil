import streamlit as st
import pandas as pd
import json
import os
import glob
import plotly.express as px

st.set_page_config(layout="wide", page_title="Portal BI - Macro Contábil")

# ---------------- VISUAL ----------------

colors = {
    "accent": "#38bdf8",
    "custos": "#475569",
    "texto": "white"
}

# ---------------- USUÁRIOS ----------------

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

# ---------------- FORMATADORES ----------------

def format_br(valor):
    if valor is None or pd.isna(valor):
        return "R$ 0,00"
    return f"R$ {valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

def format_pct(valor):
    if valor is None or pd.isna(valor):
        return "0,00%"
    return f"{valor*100:.2f}%".replace(".", ",")

def comp_br(c):
    return f"{c[4:6]}/{c[:4]}"

# ---------------- LEITOR JSON ROBUSTO ----------------

@st.cache_data(show_spinner=False)
def ler_json_arquivo(file, mtime):
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
            if "documentos" in res:
                data.extend(res["documentos"])
            elif "recibos" in res:
                data.extend(res["recibos"])
            elif "totais" in res:
                data.extend(res["totais"])
            else:
                data.append(res)

        df = pd.DataFrame(data)
        if not df.empty:
            df.columns = [c.split(".")[-1] for c in df.columns]
        return df
    except Exception:
        return pd.DataFrame()

def ler_pasta(path):
    files = glob.glob(path)
    dfs = []
    for f in files:
        mtime = os.path.getmtime(f)
        dfs.append(ler_json_arquivo(f, mtime))
    if dfs:
        return pd.concat(dfs, ignore_index=True)
    return pd.DataFrame()

# ---------------- PROCESSAMENTO ----------------

def carregar_dados(cnpj, comp):
    pasta = "dados_powerbi"

    df_f = ler_pasta(os.path.join(pasta, "notas_detalhe", f"*{cnpj}_{comp}.json"))
    df_d = ler_pasta(os.path.join(pasta, "folha_recibos_totais", f"*{cnpj}_{comp}.json"))
    df_a = ler_pasta(os.path.join(pasta, "resumo_apuracao", f"*{cnpj}_{comp}.json"))
    df_t = ler_pasta(os.path.join(pasta, "totais_faturamento", f"*{cnpj}_{comp}.json"))

    vals = {"fat":0,"ent":0,"fgts":0,"inss":0,"sn":0,"f_liq":0,"f_tot":0}

    # FATURAMENTO DETALHADO
    if not df_f.empty and "tipoMovimento" in df_f.columns:
        df_f["valorTotal"] = pd.to_numeric(df_f.get("valorTotal",0), errors="coerce").fillna(0)
        vals["fat"] = df_f[df_f["tipoMovimento"].isin(["Prestado","Saída"])]["valorTotal"].sum()
        vals["ent"] = df_f[df_f["tipoMovimento"].isin(["Entrada","Tomado"])]["valorTotal"].sum()

    # FALLBACK TOTAL
    if vals["fat"] == 0 and not df_t.empty:
        df_t["valorTotal"] = pd.to_numeric(df_t.get("valorTotal",0), errors="coerce").fillna(0)
        if "situacao" in df_t.columns:
            df_t = df_t[df_t["situacao"] == "Emitido"]
        if "tipoMovimento" in df_t.columns:
            vals["fat"] = df_t[df_t["tipoMovimento"].isin(["Prestado","Saída"])]["valorTotal"].sum()
            vals["ent"] = df_t[df_t["tipoMovimento"].isin(["Entrada","Tomado"])]["valorTotal"].sum()

    # FOLHA
    if not df_d.empty:
        vals["f_liq"] = pd.to_numeric(df_d.get("totalLiquido",0), errors="coerce").fillna(0).sum()
        vals["fgts"] = pd.to_numeric(df_d.get("valorFGTS",0), errors="coerce").fillna(0).sum()
        vals["inss"] = pd.to_numeric(df_d.get("INSSSegurado",0), errors="coerce").fillna(0).sum()
        vals["f_tot"] = pd.to_numeric(df_d.get("totalProventos",0), errors="coerce").fillna(0).sum()

    # SIMPLES
    if not df_a.empty:
        try:
            vals["sn"] = df_a.iloc[0].get("TOTAL_APURADO",0)
        except:
            vals["sn"] = 0

    # CALCULOS
    vals["res"] = vals["fat"] - (vals["ent"] + vals["f_liq"] + vals["inss"] + vals["fgts"])
    vals["al_fgts"] = vals["fgts"] / vals["f_tot"] if vals["f_tot"] > 0 else 0
    vals["al_inss"] = vals["inss"] / vals["f_tot"] if vals["f_tot"] > 0 else 0
    vals["al_sn"] = vals["sn"] / vals["fat"] if vals["fat"] > 0 else 0

    return vals, df_f, df_d


# ---------------- LOGIN ----------------

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

# ---------------- DASHBOARD ----------------

user = st.session_state.user

with st.sidebar:
    st.title("Macro Contábil")
    st.write(f"Bem-vindo **{user['nome']}**")
    comps = ["202601","202602","202603","202604","202605"]
    comp = st.selectbox("Competência", comps, format_func=lambda x: comp_br(x))
    if st.button("Sair"):
        st.session_state.auth = False
        st.rerun()

dados, df_f, df_d = carregar_dados(user["cnpj"], comp)

st.title(user["nome"])
st.subheader("Análise Contábil Preliminar")

# ---------------- MÉTRICAS ----------------

c1,c2,c3,c4 = st.columns(4)
c1.metric("Faturamento", format_br(dados["fat"]))
c2.metric("Entradas", format_br(dados["ent"]))
c3.metric("Folha Líquida", format_br(dados["f_liq"]))
c4.metric("Resultado", format_br(dados["res"]))

c1,c2,c3,c4 = st.columns(4)
c1.metric("FGTS", format_br(dados["fgts"]), format_pct(dados["al_fgts"]))
c2.metric("INSS", format_br(dados["inss"]), format_pct(dados["al_inss"]))
c3.metric("Simples Nacional", format_br(dados["sn"]), format_pct(dados["al_sn"]))
c4.metric("Folha Total", format_br(dados["f_tot"]))

st.divider()

# ---------------- CUSTOS ----------------

st.subheader("Composição de Custos")
custos = pd.DataFrame({
    "Categoria":["Compras","Folha","Impostos"],
    "Valor":[dados["ent"],dados["f_tot"],dados["sn"]]
})
custos["valor_fmt"] = custos["Valor"].apply(format_br)
fig = px.pie(custos, values="Valor", names="Categoria", hole=0.45)
fig.update_traces(text=custos["valor_fmt"], textposition="inside")
fig.update_layout(
    plot_bgcolor="rgba(0,0,0,0)",
    paper_bgcolor="rgba(0,0,0,0)",
    font_color="white",
    height=420
)
st.plotly_chart(fig, use_container_width=True)

st.divider()

# ---------------- FORNECEDORES E CLIENTES ----------------

col1, col2 = st.columns([1.3, 1])

with col1:
    st.subheader("Maiores Fornecedores")
    if not df_f.empty:
        df_forn = df_f[df_f["tipoMovimento"].isin(["Entrada","Tomado"])]
        df_forn = df_forn.sort_values("valorTotal", ascending=False)

        for _, row in df_forn.iterrows():
            fornecedor = row.get("razaoSocialClienteFornecedor", "Fornecedor")
            valor_nf = row.get("valorTotal", 0)
            nf = row.get("numero", "")

            with st.expander(f"📄 NF {nf} | {fornecedor} | {format_br(valor_nf)}"):
                if "itens" in row and isinstance(row["itens"], list):
                    df_itens = pd.DataFrame(row["itens"])
                    
                    if not df_itens.empty:
                        # Limpa nomes de colunas (remove prefixos do JSON)
                        df_itens.columns = [c.split(".")[-1] for c in df_itens.columns]

                        # Mapeamento de colunas solicitadas
                        cols_desejadas = {
                            "descricao": "Descrição",
                            "quantidade": "Qtd",
                            "valorUnitario": "Vlr. Unitário",
                            "valorTotal": "Vlr. Total"
                        }

                        # Filtra apenas as que existem no dataframe para evitar erro
                        cols_finais = [c for c in cols_desejadas.keys() if c in df_itens.columns]
                        df_exibir = df_itens[cols_finais].copy()
                        df_exibir.rename(columns=cols_desejadas, inplace=True)

                        st.dataframe(df_exibir, use_container_width=True, hide_index=True)
                    else:
                        st.info("Itens não detalhados nesta nota.")

with col2:
    st.subheader("Maiores Clientes")
    if not df_f.empty and "razaoSocialClienteFornecedor" in df_f.columns:
        df_cli = df_f[df_f["tipoMovimento"].isin(["Prestado","Saída"])]
        top_cli = df_cli.groupby("razaoSocialClienteFornecedor")["valorTotal"].sum().reset_index()
        top_cli = top_cli.sort_values("valorTotal").tail(8)

        fig = px.bar(
            top_cli,
            x="valorTotal",
            y="razaoSocialClienteFornecedor",
            orientation="h",
            text=top_cli["valorTotal"].apply(format_br),
            color_discrete_sequence=[colors["accent"]]
        )
        fig.update_layout(
            plot_bgcolor="rgba(0,0,0,0)",
            paper_bgcolor="rgba(0,0,0,0)",
            font_color="white",
            height=400
        )
        st.plotly_chart(fig, use_container_width=True)

st.divider()

# ---------------- FOLHA ----------------

st.subheader("Folha de Pagamento")
if not df_d.empty:
    nome_col = "nome" if "nome" in df_d.columns else "nomeTrabalhador"
    # Garante que as colunas existam antes de filtrar
    cols_folha = [nome_col, "tipoRecibo", "totalProventos", "totalLiquido"]
    cols_existentes = [c for c in cols_folha if c in df_d.columns]
    
    df_view = df_d[cols_existentes].copy()
    
    # Renomeia para exibição se todas estiverem lá
    mapeamento_folha = {
        nome_col: "Nome",
        "tipoRecibo": "Função/Recibo",
        "totalProventos": "Salário Bruto",
        "totalLiquido": "Salário Líquido"
    }
    df_view.rename(columns=mapeamento_folha, inplace=True)

    st.dataframe(
        df_view.style.format({
            "Salário Bruto": format_br,
            "Salário Líquido": format_br
        }),
        use_container_width=True,
        hide_index=True
    )