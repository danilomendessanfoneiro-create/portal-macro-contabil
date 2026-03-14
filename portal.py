import streamlit as st
import pandas as pd
import json
import os
import glob
import plotly.express as px
import re

st.set_page_config(layout="wide", page_title="Portal BI - Macro Contábil")

# ---------------- CORES ----------------
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

def comp_br(c):
    return f"{c[4:6]}/{c[:4]}"

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
                    for k in ["documentos", "recibos", "totais"]:
                        if k in res: data.extend(res[k]); break
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

    # Faturamento e Entradas
    if not df_f.empty:
        df_f["tipoMovimento"] = df_f["tipoMovimento"].astype(str).str.strip()
        vals["fat"] = df_f[df_f["tipoMovimento"].isin(["Prestado","Saída"])]["valorTotal"].sum()
        vals["ent"] = df_f[df_f["tipoMovimento"].isin(["Entrada","Tomado"])]["valorTotal"].sum()
    elif not df_t.empty:
        df_t["tipoMovimento"] = df_t["tipoMovimento"].astype(str).str.strip()
        vals["fat"] = df_t[df_t["tipoMovimento"].isin(["Saída","Prestado"])]["valorTotal"].sum()
        vals["ent"] = df_t[df_t["tipoMovimento"].isin(["Entrada","Tomado"])]["valorTotal"].sum()

    if not df_d.empty:
        vals["f_liq"] = df_d.get("totalLiquido", 0).sum()
        vals["f_tot"] = df_d.get("totalProventos", 0).sum()
        vals["fgts"] = df_d.get("valorFGTS", 0).sum()
        vals["inss"] = df_d.get("INSSSegurado", 0).sum()

    if not df_a.empty:
        vals["sn"] = pd.to_numeric(df_a.iloc[0].get("TOTAL_APURADO", 0), errors="coerce")

    vals["res"] = vals["fat"] - (vals["ent"] + vals["f_tot"] + vals["sn"])
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

c1,c2,c3,c4 = st.columns(4)
c1.metric("Faturamento Total", format_br(dados["fat"]))
c2.metric("Total Saídas", format_br(dados["ent"] + dados["f_tot"] + dados["sn"]))
c3.metric("Resultado Estimado", format_br(dados["res"]))
c4.metric("Folha Líquida", format_br(dados["f_liq"]))

st.divider()

col_graf1, col_graf2 = st.columns(2)

with col_graf1:
    st.write("### Comparativo: Faturamento x Saídas")
    df_bar = pd.DataFrame([
        {"Legenda": "Faturamento", "Valor": dados["fat"]},
        {"Legenda": "Saídas Geral", "Valor": dados["ent"] + dados["f_tot"] + dados["sn"]}
    ])
    fig1 = px.bar(df_bar, x="Legenda", y="Valor", color="Legenda", text_auto=".2s",
                  color_discrete_map={"Faturamento": colors["faturamento"], "Saídas Geral": colors["saidas"]})
    st.plotly_chart(fig1, use_container_width=True)

with col_graf2:
    st.write("### Composição dos Custos (Proporção)")
    df_pie = pd.DataFrame([
        {"Categoria": "Compras", "V": dados["ent"]},
        {"Categoria": "Folha", "V": dados["f_tot"]},
        {"Categoria": "Impostos", "V": dados["sn"]}
    ])
    fig2 = px.pie(df_pie, values="V", names="Categoria", hole=.4,
                  color_discrete_map={"Compras": colors["compras"], "Folha": colors["folha"], "Impostos": colors["impostos"]})
    st.plotly_chart(fig2, use_container_width=True)

st.divider()
t1, t2 = st.tabs(["👥 Funcionários", "📦 Fornecedores"])

with t1:
    if not df_d.empty:
        # Padronização de nomes de colunas para evitar erros
        mapa_folha = {
            "nomeFuncionario": "Nome do Funcionário",
            "cargo": "Função/Cargo",
            "funcao": "Função/Cargo",
            "totalProventos": "Salário Bruto",
            "totalLiquido": "Salário Líquido"
        }
        df_folha_view = df_d.rename(columns=mapa_folha)
        colunas_finais = ["Nome do Funcionário", "Função/Cargo", "Salário Bruto", "Salário Líquido"]
        
        # Só exibe o que existir no arquivo
        existentes = [c for c in colunas_finais if c in df_folha_view.columns]
        df_final = df_folha_view[existentes].copy()
        
        for c in ["Salário Bruto", "Salário Líquido"]:
            if c in df_final.columns:
                df_final[c] = df_final[c].apply(format_br)
        
        st.dataframe(df_final, use_container_width=True, hide_index=True)
    else:
        st.info("Sem dados de folha.")

with t2:
    if not df_f.empty:
        df_ent = df_f[df_f["tipoMovimento"].isin(["Entrada", "Tomado"])].copy()
        
        # Ajuste para o erro de KeyError: Tenta encontrar a coluna do fornecedor
        col_forn = "nomeEmitente" if "nomeEmitente" in df_ent.columns else ("nome" if "nome" in df_ent.columns else None)
        
        if col_forn and not df_ent.empty:
            for forn, group in df_ent.groupby(col_forn):
                with st.expander(f"🏢 {forn} - Total: {format_br(group['valorTotal'].sum())}"):
                    # Tabela interna simplificada
                    det = group[["numero", "valorTotal", "dataEmissao"]].copy()
                    det.columns = ["NF", "Valor", "Data"]
                    det["Valor"] = det["Valor"].apply(format_br)
                    st.table(det)
        else:
            st.info("Nenhum detalhe de fornecedor disponível.")
    else:
        st.info("Sem notas de entrada.")