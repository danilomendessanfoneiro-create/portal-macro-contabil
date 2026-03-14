import streamlit as st
import pandas as pd
import json
import os
import glob
import plotly.express as px
import re

st.set_page_config(layout="wide", page_title="Portal BI - Macro Contábil")

# ---------------- CONFIGURAÇÕES E CORES ----------------
colors = {
    "faturamento": "#38bdf8",
    "compras": "#475569",
    "folha": "#94a3b8",
    "impostos": "#1e293b",
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

# ---------------- LEITURA DE DADOS ----------------
def carregar_dados(cnpj, comp):
    pasta = "dados_powerbi"

    def ler(sub):
        path = os.path.join(pasta, sub, f"*{cnpj}_{comp}.json")
        files = glob.glob(path)
        data = []
        for f in files:
            with open(f, "r", encoding="utf-8") as file:
                js = json.load(file)
                res = js.get("result", js) if isinstance(js, dict) else js
                if isinstance(res, list): data.extend(res)
                elif isinstance(res, dict):
                    if "documentos" in res: data.extend(res["documentos"])
                    elif "recibos" in res: data.extend(res["recibos"])
                    elif "totais" in res: data.extend(res["totais"])
                    else: data.append(res)
        df = pd.DataFrame(data)
        if not df.empty:
            df.columns = [c.split(".")[-1] for c in df.columns]
            # Limpeza de tipos para garantir soma
            for col in ["valorTotal", "totalLiquido", "valorFGTS", "INSSSegurado", "totalProventos"]:
                if col in df.columns:
                    df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)
        return df

    df_f = ler("notas_detalhe")
    df_d = ler("folha_recibos_totais")
    df_a = ler("resumo_apuracao")
    df_t = ler("totais_faturamento")

    vals = {"fat":0,"ent":0,"fgts":0,"inss":0,"sn":0,"f_liq":0,"f_tot":0}

    # FATURAMENTO
    if not df_f.empty and "tipoMovimento" in df_f.columns:
        df_f["tipoMovimento"] = df_f["tipoMovimento"].astype(str).str.strip()
        vals["fat"] = df_f[df_f["tipoMovimento"].isin(["Prestado","Saída"])]["valorTotal"].sum()
        vals["ent"] = df_f[df_f["tipoMovimento"].isin(["Entrada","Tomado"])]["valorTotal"].sum()
    elif not df_t.empty:
        df_emit = df_t[df_t.get("situacao") == "Emitido"] if "situacao" in df_t.columns else df_t
        vals["fat"] = df_emit[df_emit.get("tipoMovimento").isin(["Saída","Prestado"])]["valorTotal"].sum()
        vals["ent"] = df_emit[df_emit.get("tipoMovimento").isin(["Entrada","Tomado"])]["valorTotal"].sum()

    # FOLHA
    if not df_d.empty:
        vals["f_liq"] = df_d.get("totalLiquido", 0).sum()
        vals["fgts"] = df_d.get("valorFGTS", 0).sum()
        vals["inss"] = df_d.get("INSSSegurado", 0).sum()
        vals["f_tot"] = df_d.get("totalProventos", 0).sum()

    # SIMPLES
    if not df_a.empty:
        vals["sn"] = pd.to_numeric(df_a.iloc[0].get("TOTAL_APURADO", 0), errors="coerce")

    vals["res"] = vals["fat"] - (vals["ent"] + vals["f_liq"] + vals["inss"] + vals["fgts"])
    vals["al_fgts"] = vals["fgts"]/vals["f_tot"] if vals["f_tot"]>0 else 0
    vals["al_inss"] = vals["inss"]/vals["f_tot"] if vals["f_tot"]>0 else 0
    vals["al_sn"] = vals["sn"]/vals["fat"] if vals["fat"]>0 else 0

    return vals, df_f, df_d

# ---------------- DASHBOARD ----------------
if "auth" not in st.session_state: st.session_state.auth = False
if not st.session_state.auth:
    st.title("Portal Macro Contábil")
    u = st.text_input("Usuário")
    p = st.text_input("Senha", type="password")
    if st.button("Entrar"):
        if u in usuarios_db and usuarios_db[u]["senha"] == p:
            st.session_state.auth = True
            st.session_state.user = usuarios_db[u]
            st.rerun()
        else: st.error("Erro")
    st.stop()

user = st.session_state.user
comps = ["202601", "202602", "202603", "202604", "202605"]

with st.sidebar:
    st.title("Macro Contábil")
    comp = st.selectbox("Competência", comps, format_func=lambda x: comp_br(x))
    if st.button("Sair"):
        st.session_state.auth = False
        st.rerun()

dados, df_f, df_d = carregar_dados(user["cnpj"], comp)

st.title(user["nome"])
st.subheader(f"Análise Contábil - {comp_br(comp)}")

# Métricas
c1,c2,c3,c4 = st.columns(4)
c1.metric("Faturamento Total", format_br(dados["fat"]))
c2.metric("Entradas/Compras", format_br(dados["ent"]))
c3.metric("Folha Líquida", format_br(dados["f_liq"]))
c4.metric("Resultado Estimado", format_br(dados["res"]))

c1,c2,c3,c4 = st.columns(4)
c1.metric("FGTS", format_br(dados["fgts"]), format_pct(dados["al_fgts"]))
c2.metric("INSS", format_br(dados["inss"]), format_pct(dados["al_inss"]))
c3.metric("Simples Nacional", format_br(dados["sn"]), format_pct(dados["al_sn"]))
c4.metric("Custo Total Folha", format_br(dados["f_tot"]))

st.divider()

# --- NOVO GRÁFICO CATEGORIZADO ---
st.subheader("📊 Composição Mensal (Faturamento vs Detalhe de Custos)")
hist_list = []
for c in comps:
    v, _, _ = carregar_dados(user["cnpj"], c)
    hist_list.append({"Mes": comp_br(c), "Categoria": "Faturamento", "Valor": v["fat"]})
    hist_list.append({"Mes": comp_br(c), "Categoria": "Compras", "Valor": v["ent"]})
    hist_list.append({"Mes": comp_br(c), "Categoria": "Folha", "Valor": v["f_tot"]})
    hist_list.append({"Mes": comp_br(c), "Categoria": "Simples", "Valor": v["sn"]})

df_plot = pd.DataFrame(hist_list)
fig = px.bar(df_plot, x="Mes", y="Valor", color="Categoria", barmode="group",
             color_discrete_map={"Faturamento": colors["faturamento"], "Compras": colors["compras"], "Folha": colors["folha"], "Simples": colors["impostos"]})
st.plotly_chart(fig, use_container_width=True)

# --- NOVA TABELA DE FOLHA ---
if not df_d.empty:
    st.divider()
    st.subheader("📝 Detalhamento da Folha de Pagamento")
    cols = ["nomeFuncionario", "totalProventos", "totalLiquido", "valorFGTS"]
    df_exibir = df_d[[c for c in cols if c in df_d.columns]].copy()
    
    # Formata moedas para a tabela
    for col in df_exibir.columns:
        if col != "nomeFuncionario":
            df_exibir[col] = df_exibir[col].apply(format_br)
    
    st.dataframe(df_exibir, use_container_width=True, hide_index=True)