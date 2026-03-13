import streamlit as st
import pandas as pd
import json
import os
import glob
import plotly.express as px

st.set_page_config(layout="wide", page_title="Portal BI - Macro Contábil")

colors = {
    "faturamento": "#38bdf8",
    "custos": "#475569",
    "texto": "white"
}

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

def format_br(valor):
    return f"R$ {valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

def format_pct(valor):
    return f"{valor*100:.2f}%".replace(".", ",")

def comp_br(c):
    return f"{c[4:6]}/{c[:4]}"

# ---------------- LEITOR DE JSON ----------------

def ler_json(path):
    files = glob.glob(path)
    data = []
    for f in files:
        with open(f, "r", encoding="utf-8") as file:
            js = json.load(file)
            if isinstance(js, dict):
                res = js.get("result", js)
            elif isinstance(js, list):
                res = js
            else:
                res = []

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

# ---------------- CARREGAR DADOS (COM CACHE CONTROLADO) ----------------

# ttl=3600 faz com que o cache expire a cada 1 hora. 
# Se você quiser atualização instantânea absoluta, remova a linha abaixo.
@st.cache_data(ttl=3600) 
def carregar_dados(cnpj, comp):
    pasta = "dados_powerbi"

    df_f = ler_json(os.path.join(pasta, "notas_detalhe", f"*{cnpj}_{comp}.json"))
    df_d = ler_json(os.path.join(pasta, "folha_recibos_totais", f"*{cnpj}_{comp}.json"))
    df_a = ler_json(os.path.join(pasta, "resumo_apuracao", f"*{cnpj}_{comp}.json"))
    df_t = ler_json(os.path.join(pasta, "totais_faturamento", f"*{cnpj}_{comp}.json"))

    vals = {"fat":0,"ent":0,"fgts":0,"inss":0,"sn":0,"f_liq":0,"f_tot":0}

    # ---------------- FATURAMENTO / ENTRADAS (NOTAS DETALHE) ----------------
    if not df_f.empty and "tipoMovimento" in df_f.columns:
        df_f["tipoMovimento"] = df_f["tipoMovimento"].astype(str).str.strip()
        if "valorTotal" in df_f.columns:
            df_f["valorTotal"] = pd.to_numeric(df_f["valorTotal"], errors="coerce").fillna(0)
            vals["fat"] = df_f[df_f["tipoMovimento"].isin(["Prestado","Saída"])]["valorTotal"].sum()
            vals["ent"] = df_f[df_f["tipoMovimento"].isin(["Entrada","Tomado"])]["valorTotal"].sum()

    # ---------------- FALLBACK PARA TOTAIS (PLANO B) ----------------
    if vals["fat"] == 0 and not df_t.empty:
        if "valorTotal" in df_t.columns:
            df_t["valorTotal"] = pd.to_numeric(df_t["valorTotal"], errors="coerce").fillna(0)
        
        # Limpeza de strings para evitar erros de comparação
        for col in ["situacao", "tipoMovimento"]:
            if col in df_t.columns:
                df_t[col] = df_t[col].astype(str).str.strip()

        df_emit = df_t[df_t.get("situacao") == "Emitido"] if "situacao" in df_t.columns else df_t
        
        if "tipoMovimento" in df_emit.columns:
            vals["fat"] = df_emit[df_emit["tipoMovimento"].isin(["Saída","Prestado"])]["valorTotal"].sum()
            vals["ent"] = df_emit[df_emit["tipoMovimento"].isin(["Entrada","Tomado"])]["valorTotal"].sum()
        else:
            # Caso a chave tipoMovimento falhe (aquele erro do Tomado sem chave)
            def check_val(row, lista):
                return any(str(v).strip() in lista for v in row.values)
            
            vals["fat"] = df_emit[df_emit.apply(lambda r: check_val(r, ["Saída", "Prestado"]), axis=1)]["valorTotal"].sum()
            vals["ent"] = df_emit[df_emit.apply(lambda r: check_val(r, ["Entrada", "Tomado"]), axis=1)]["valorTotal"].sum()

    # ---------------- FOLHA ----------------
    if not df_d.empty:
        vals["f_liq"] = df_d.get("totalLiquido",0).sum()
        vals["fgts"] = df_d.get("valorFGTS",0).sum()
        vals["inss"] = df_d.get("INSSSegurado",0).sum()
        vals["f_tot"] = df_d.get("totalProventos",0).sum()

    # ---------------- SIMPLES ----------------
    if not df_a.empty:
        if isinstance(df_a.iloc[0], pd.Series):
            vals["sn"] = df_a.iloc[0].get("TOTAL_APURADO",0)

    # ---------------- RESULTADOS ----------------
    vals["res"] = vals["fat"] - (vals["ent"] + vals["f_liq"] + vals["inss"] + vals["fgts"])
    vals["al_fgts"] = vals["fgts"]/vals["f_tot"] if vals["f_tot"]>0 else 0
    vals["al_inss"] = vals["inss"]/vals["f_tot"] if vals["f_tot"]>0 else 0
    vals["al_sn"] = vals["sn"]/vals["fat"] if vals["fat"]>0 else 0

    return vals,df_f,df_d

@st.cache_data(ttl=3600)
def carregar_historico(cnpj,lista_comps):
    hist=[]
    for c in lista_comps:
        v,_,_ = carregar_dados(cnpj,c)
        hist.append({
            "Competência":comp_br(c),
            "Faturamento":v["fat"],
            "Custos":v["ent"]+v["f_tot"]+v["sn"]
        })
    return pd.DataFrame(hist)

# -------- LOGIN --------
if "auth" not in st.session_state:
    st.session_state.auth=False

if not st.session_state.auth:
    st.title("Portal Macro Contábil")
    user_input=st.text_input("Usuário")
    senha_input=st.text_input("Senha",type="password")
    if st.button("Entrar"):
        if user_input in usuarios_db and usuarios_db[user_input]["senha"]==senha_input:
            st.session_state.auth=True
            st.session_state.user=usuarios_db[user_input]
            st.rerun()
        else:
            st.error("Usuário ou senha inválidos")
    st.stop()

# -------- DASHBOARD --------
user=st.session_state.user
comps=["202601","202602","202603"]

with st.sidebar:
    st.title("Macro Contábil")
    st.write(f"Bem-vindo **{user['nome']}**")
    comp=st.selectbox("Competência",comps,format_func=lambda x:comp_br(x))
    if st.button("Sair"):
        st.session_state.auth=False
        st.rerun()

dados,df_f,df_d=carregar_dados(user["cnpj"],comp)

st.title(user["nome"])
st.subheader("Análise Contábil Preliminar")

c1,c2,c3,c4=st.columns(4)
c1.metric("Faturamento Total",format_br(dados["fat"]))
c2.metric("Entradas/Compras",format_br(dados["ent"]))
c3.metric("Folha Líquida",format_br(dados["f_liq"]))
c4.metric("Resultado Estimado",format_br(dados["res"]))

c1,c2,c3,c4=st.columns(4)
c1.metric("FGTS",format_br(dados["fgts"]),format_pct(dados["al_fgts"]))
c2.metric("INSS",format_br(dados["inss"]),format_pct(dados["al_inss"]))
c3.metric("Simples Nacional",format_br(dados["sn"]),format_pct(dados["al_sn"]))
c4.metric("Custo Total Folha",format_br(dados["f_tot"]))

st.divider()

st.subheader("📊 Evolução Mensal (Faturamento vs Custos)")
df_hist=carregar_historico(user["cnpj"],comps)

fig_evolucao=px.bar(
    df_hist,
    x="Competência",
    y=["Faturamento","Custos"],
    barmode="group",
    color_discrete_map={"Faturamento":colors["faturamento"],"Custos":colors["custos"]},
    text_auto='.2s'
)

fig_evolucao.update_layout(
    legend_title_text="",
    xaxis_title="",
    yaxis_title="Valor (R$)",
    plot_bgcolor="rgba(0,0,0,0)",
    paper_bgcolor="rgba(0,0,0,0)",
    font_color="white",
    height=400
)

st.plotly_chart(fig_evolucao,use_container_width=True)