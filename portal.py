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


def carregar_dados(cnpj, comp):

    pasta = "dados_powerbi"

    def ler(sub):

        path = os.path.join(pasta, sub, f"*{cnpj}_{comp}.json")
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

    df_f = ler("notas_detalhe")
    df_d = ler("folha_recibos_totais")
    df_a = ler("resumo_apuracao")
    df_t = ler("totais_faturamento")

    vals = {
        "fat": 0,
        "ent": 0,
        "fgts": 0,
        "inss": 0,
        "sn": 0,
        "f_liq": 0,
        "f_tot": 0
    }

    # ---------------- FATURAMENTO E ENTRADAS ----------------

    if not df_f.empty:

        df_f["tipoMovimento"] = df_f["tipoMovimento"].astype(str).str.strip()

        vals["fat"] = df_f[
            df_f["tipoMovimento"].isin(["Prestado", "Saída"])
        ]["valorTotal"].sum()

        vals["ent"] = df_f[
            df_f["tipoMovimento"] == "Entrada"
        ]["valorTotal"].sum()

    # Fallback

    if (vals["fat"] == 0 and vals["ent"] == 0) and not df_t.empty:

        if "situacao" in df_t.columns:
            df_t["situacao"] = df_t["situacao"].astype(str).str.strip()

        df_emitido = df_t[df_t.get("situacao") == "Emitido"].copy()

        if not df_emitido.empty:

            def check_mov(row, tipos):
                return any(str(val).strip() in tipos for val in row.values)

            mask_fat = df_emitido.apply(
                lambda r: check_mov(r, ["Saída", "Prestado"]),
                axis=1
            )

            vals["fat"] = df_emitido[mask_fat]["valorTotal"].sum()

            mask_ent = df_emitido.apply(
                lambda r: check_mov(r, ["Entrada", "Tomado"]),
                axis=1
            )

            vals["ent"] = df_emitido[mask_ent]["valorTotal"].sum()

    # ---------------- FOLHA ----------------

    if not df_d.empty:

        vals["f_liq"] = df_d.get("totalLiquido", 0).sum()
        vals["fgts"] = df_d.get("valorFGTS", 0).sum()
        vals["inss"] = df_d.get("INSSSegurado", 0).sum()
        vals["f_tot"] = df_d.get("totalProventos", 0).sum()

    # ---------------- SIMPLES ----------------

    if not df_a.empty:

        if isinstance(df_a.iloc[0], pd.Series):
            vals["sn"] = df_a.iloc[0].get("TOTAL_APURADO", 0)

    # ---------------- CÁLCULOS ----------------

    vals["res"] = vals["fat"] - (
        vals["ent"] +
        vals["f_liq"] +
        vals["inss"] +
        vals["fgts"]
    )

    vals["al_fgts"] = vals["fgts"] / vals["f_tot"] if vals["f_tot"] > 0 else 0
    vals["al_inss"] = vals["inss"] / vals["f_tot"] if vals["f_tot"] > 0 else 0
    vals["al_sn"] = vals["sn"] / vals["fat"] if vals["fat"] > 0 else 0

    return vals, df_f, df_d


def carregar_historico(cnpj, lista_comps):

    hist = []

    for c in lista_comps:

        v, _, _ = carregar_dados(cnpj, c)

        hist.append({
            "Competência": comp_br(c),
            "Faturamento": v["fat"],
            "Custos": v["ent"] + v["f_tot"] + v["sn"]
        })

    return pd.DataFrame(hist)


# -------- LOGIN --------

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


# -------- DASHBOARD --------

user = st.session_state.user

comps = ["202601", "202602", "202603"]

with st.sidebar:

    st.title("Macro Contábil")

    st.write(f"Bem-vindo **{user['nome']}**")

    comp = st.selectbox(
        "Competência",
        comps,
        format_func=lambda x: comp_br(x)
    )

    if st.button("Sair"):

        st.session_state.auth = False
        st.rerun()


dados, df_f, df_d = carregar_dados(user["cnpj"], comp)

st.title(user["nome"])
st.subheader("Análise Contábil Preliminar")

c1, c2, c3, c4 = st.columns(4)

c1.metric("Faturamento Total", format_br(dados["fat"]))
c2.metric("Entradas/Compras", format_br(dados["ent"]))
c3.metric("Folha Líquida", format_br(dados["f_liq"]))
c4.metric("Resultado Estimado", format_br(dados["res"]))

c1, c2, c3, c4 = st.columns(4)

c1.metric("FGTS", format_br(dados["fgts"]), format_pct(dados["al_fgts"]))
c2.metric("INSS", format_br(dados["inss"]), format_pct(dados["al_inss"]))
c3.metric("Simples Nacional", format_br(dados["sn"]), format_pct(dados["al_sn"]))
c4.metric("Custo Total Folha", format_br(dados["f_tot"]))

st.divider()

st.subheader("📊 Evolução Mensal (Faturamento vs Custos)")

df_hist = carregar_historico(user["cnpj"], comps)

fig_evolucao = px.bar(
    df_hist,
    x="Competência",
    y=["Faturamento", "Custos"],
    barmode="group",
    color_discrete_map={
        "Faturamento": colors["faturamento"],
        "Custos": colors["custos"]
    },
    text_auto=".2s"
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

st.plotly_chart(fig_evolucao, use_container_width=True)