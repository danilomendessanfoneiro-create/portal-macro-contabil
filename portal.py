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
    "saidas": "#475569",
    "folha": "#6366f1",
    "impostos": "#f43f5e",
    "compras": "#fbbf24"
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
            for col in ["valorTotal", "totalLiquido", "valorFGTS", "INSSSegurado", "totalProventos"]:
                if col in df.columns:
                    df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)
        return df

    df_f = ler("notas_detalhe")
    df_d = ler("folha_recibos_totais")
    df_a = ler("resumo_apuracao")
    df_t = ler("totais_faturamento")

    vals = {"fat":0,"ent":0,"fgts":0,"inss":0,"sn":0,"f_liq":0,"f_tot":0}

    # FATURAMENTO E ENTRADAS
    if not df_f.empty:
        df_f["tipoMovimento"] = df_f["tipoMovimento"].astype(str).str.strip()
        vals["fat"] = df_f[df_f["tipoMovimento"].isin(["Prestado","Saída"])]["valorTotal"].sum()
        vals["ent"] = df_f[df_f["tipoMovimento"].isin(["Entrada","Tomado"])]["valorTotal"].sum()
    elif not df_t.empty:
        df_t["tipoMovimento"] = df_t["tipoMovimento"].astype(str).str.strip()
        df_emit = df_t[df_t.get("situacao") == "Emitido"] if "situacao" in df_t.columns else df_t
        vals["fat"] = df_emit[df_emit["tipoMovimento"].isin(["Saída","Prestado"])]["valorTotal"].sum()
        vals["ent"] = df_emit[df_emit["tipoMovimento"].isin(["Entrada","Tomado"])]["valorTotal"].sum()

    # FOLHA
    if not df_d.empty:
        vals["f_liq"] = df_d.get("totalLiquido", 0).sum()
        vals["fgts"] = df_d.get("valorFGTS", 0).sum()
        vals["inss"] = df_d.get("INSSSegurado", 0).sum()
        vals["f_tot"] = df_d.get("totalProventos", 0).sum()

    # SIMPLES
    if not df_a.empty:
        vals["sn"] = pd.to_numeric(df_a.iloc[0].get("TOTAL_APURADO", 0), errors="coerce")

    vals["res"] = vals["fat"] - (vals["ent"] + vals["f_liq"] + vals["inss"] + vals["fgts"] + vals["sn"])
    return vals, df_f, df_d

# ---------------- LOGIN ----------------
if "auth" not in st.session_state: st.session_state.auth = False
if not st.session_state.auth:
    st.title("Portal Macro Contábil")
    u = st.text_input("Usuário")
    p = st.text_input("Senha", type="password")
    if st.button("Entrar"):
        if u in usuarios_db and usuarios_db[u]["senha"] == p:
            st.session_state.auth, st.session_state.user = True, usuarios_db[u]
            st.rerun()
        else: st.error("Erro")
    st.stop()

# ---------------- DASHBOARD ----------------
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
st.subheader(f"Dashboard Financeiro - {comp_br(comp)}")

# Métricas Principais
c1,c2,c3,c4 = st.columns(4)
c1.metric("Faturamento Total", format_br(dados["fat"]))
c2.metric("Total Custos/Saídas", format_br(dados["ent"] + dados["f_tot"] + dados["sn"]))
c3.metric("Resultado Estimado", format_br(dados["res"]))
c4.metric("Folha Líquida", format_br(dados["f_liq"]))

st.divider()

col_graf1, col_graf2 = st.columns(2)

with col_graf1:
    st.write("### Faturamento vs Saídas")
    df_comp = pd.DataFrame([
        {"Tipo": "Faturamento", "Valor": dados["fat"]},
        {"Tipo": "Saídas Geral", "Valor": dados["ent"] + dados["f_tot"] + dados["sn"]}
    ])
    fig_bar = px.bar(df_comp, x="Tipo", y="Valor", color="Tipo", text_auto=".2s",
                     color_discrete_map={"Faturamento": colors["faturamento"], "Saídas Geral": colors["saidas"]})
    st.plotly_chart(fig_bar, use_container_width=True)

with col_graf2:
    st.write("### Distribuição de Custos")
    df_pizza = pd.DataFrame([
        {"Cat": "Compras/Entradas", "V": dados["ent"]},
        {"Cat": "Folha (Proventos)", "V": dados["f_tot"]},
        {"Cat": "Impostos (Simples)", "V": dados["sn"]}
    ])
    fig_pie = px.pie(df_pizza, values="V", names="Cat", hole=.4,
                     color_discrete_map={"Compras/Entradas": colors["compras"], "Folha (Proventos)": colors["folha"], "Impostos (Simples)": colors["impostos"]})
    st.plotly_chart(fig_pie, use_container_width=True)

# ---------------- TABELAS DETALHADAS ----------------

st.divider()
tab1, tab2 = st.tabs(["👥 Detalhe da Folha", "📦 Detalhe de Entradas/Fornecedores"])

with tab1:
    if not df_d.empty:
        # Colunas conforme pedido: nomeFuncionario, cargo (ou tipo), totalProventos, totalLiquido
        cols_folha = ["nomeFuncionario", "cargo", "totalProventos", "totalLiquido"]
        # Fallback caso 'cargo' tenha outro nome no JSON (como 'funcao')
        if "cargo" not in df_d.columns and "funcao" in df_d.columns:
            df_d = df_d.rename(columns={"funcao": "cargo"})
        
        df_folha_view = df_d[[c for c in cols_folha if c in df_d.columns]].copy()
        
        for c in ["totalProventos", "totalLiquido"]:
            if c in df_folha_view.columns:
                df_folha_view[c] = df_folha_view[c].apply(format_br)
        
        st.dataframe(df_folha_view, use_container_width=True, hide_index=True)
    else:
        st.warning("Dados de folha não encontrados.")

with tab2:
    df_ent = df_f[df_f.get("tipoMovimento").isin(["Entrada", "Tomado"])] if not df_f.empty else pd.DataFrame()
    if not df_ent.empty:
        # Tabela expansível de fornecedores
        for forn, group in df_ent.groupby("nomeEmitente"):
            with st.expander(f"🏢 {forn} - Total: {format_br(group['valorTotal'].sum())}"):
                detalhe = group[["numero", "valorTotal", "dataEmissao"]].copy()
                detalhe["valorTotal"] = detalhe["valorTotal"].apply(format_br)
                st.table(detalhe)
    else:
        st.warning("Nenhuma nota de entrada detalhada para este mês.")