import streamlit as st
import pandas as pd
import json
import os
import glob
import plotly.express as px

# Configuração da página
st.set_page_config(layout="wide", page_title="Portal BI - Macro Contábil")

# Estilização e Cores
colors = {"accent": "#38bdf8"}

# Banco de dados de usuários (Simulado)
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

# --- FUNÇÕES DE FORMATAÇÃO ---
def format_br(valor):
    if valor is None: return "R$ 0,00"
    return f"R$ {valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

def format_pct(valor):
    return f"{valor*100:.2f}%".replace(".", ",")

def comp_br(c):
    return f"{c[4:6]}/{c[:4]}"

# --- CARREGAMENTO DE DADOS ---
def carregar_dados(cnpj, comp):
    pasta = "dados_powerbi"

    def ler(sub):
        path = os.path.join(pasta, sub, f"*{cnpj}_{comp}.json")
        files = glob.glob(path)
        data = []
        for f in files:
            with open(f, "r", encoding="utf-8") as file:
                js = json.load(file)
                res = js.get("result", js)
                if isinstance(res, list): data.extend(res)
                elif isinstance(res, dict):
                    if "documentos" in res: data.extend(res["documentos"])
                    elif "recibos" in res: data.extend(res["recibos"])
                    else: data.append(res)
        df = pd.DataFrame(data)
        if not df.empty:
            df.columns = [c.split(".")[-1] for c in df.columns]
        return df

    df_f = ler("notas_detalhe")
    df_d = ler("folha_recibos_totais")
    df_a = ler("resumo_apuracao")

    vals = {"fat": 0, "ent": 0, "fgts": 0, "inss": 0, "sn": 0, "f_liq": 0, "f_tot": 0}

    if not df_f.empty:
        vals["fat"] = df_f[df_f["tipoMovimento"] == "Prestado"]["valorTotal"].sum()
        vals["ent"] = df_f[df_f["tipoMovimento"] == "Entrada"]["valorTotal"].sum()

    if not df_d.empty:
        vals["f_liq"] = df_d.get("totalLiquido", 0).sum()
        vals["fgts"] = df_d.get("valorFGTS", 0).sum()
        vals["inss"] = df_d.get("INSSSegurado", 0).sum()
        vals["f_tot"] = df_d.get("totalProventos", 0).sum()

    if not df_a.empty:
        if isinstance(df_a.iloc[0], pd.Series):
            vals["sn"] = df_a.iloc[0].get("TOTAL_APURADO", 0)

    vals["res"] = vals["fat"] - (vals["ent"] + vals["f_liq"] + vals["inss"] + vals["fgts"])
    vals["al_fgts"] = vals["fgts"] / vals["f_tot"] if vals["f_tot"] > 0 else 0
    vals["al_inss"] = vals["inss"] / vals["f_tot"] if vals["f_tot"] > 0 else 0
    vals["al_sn"] = vals["sn"] / vals["fat"] if vals["fat"] > 0 else 0

    return vals, df_f, df_d

# --- LOGIN ---
if "auth" not in st.session_state:
    st.session_state.auth = False

if not st.session_state.auth:
    st.title("Portal Macro Contábil")
    user = st.text_input("Usuário")
    senha = st.text_input("Senha", type="password")
    if st.button("Entrar"):
        if user in usuarios_db and usuarios_db[user]["senha"] == senha:
            st.session_state.auth = True
            st.session_state.user = usuarios_db[user]
            st.rerun()
        else:
            st.error("Usuário ou senha inválidos")
    st.stop()

# --- DASHBOARD ---
user = st.session_state.user

with st.sidebar:
    st.title("Macro Contábil")
    st.write(f"Bem-vindo **{user['nome']}**")
    comps = ["202601", "202602", "202603"]
    comp = st.selectbox("Competência", comps, format_func=lambda x: comp_br(x))
    if st.button("Sair"):
        st.session_state.auth = False
        st.rerun()

dados, df_f, df_d = carregar_dados(user["cnpj"], comp)

st.title(user["nome"])
st.subheader("Análise Contábil Preliminar")

# Métricas Principais
m1, m2, m3, m4 = st.columns(4)
m1.metric("Faturamento", format_br(dados["fat"]))
m2.metric("Entradas (Compras)", format_br(dados["ent"]))
m3.metric("Folha Líquida", format_br(dados["f_liq"]))
m4.metric("Resultado Est.", format_br(dados["res"]))

m5, m6, m7, m8 = st.columns(4)
m5.metric("FGTS", format_br(dados["fgts"]), format_pct(dados["al_fgts"]), delta_color="inverse")
m6.metric("INSS", format_br(dados["inss"]), format_pct(dados["al_inss"]), delta_color="inverse")
m7.metric("Simples Nacional", format_br(dados["sn"]), format_pct(dados["al_sn"]), delta_color="inverse")
m8.metric("Folha Total (Proventos)", format_br(dados["f_tot"]))

st.divider()

# --- GRÁFICO: COMPOSIÇÃO DE CUSTOS ---
st.subheader("📊 Composição de Custos")
custos_df = pd.DataFrame({
    "Categoria": ["Compras", "Folha (Proventos)", "Impostos (Simples)"],
    "Valor": [dados["ent"], dados["f_tot"], dados["sn"]]
})

fig_pizza = px.pie(custos_df, values="Valor", names="Categoria", hole=0.45, 
                   color_discrete_sequence=px.colors.qualitative.Pastel)
fig_pizza.update_layout(height=400, margin=dict(t=0, b=0, l=0, r=0))
st.plotly_chart(fig_pizza, use_container_width=True)

st.divider()

# --- FORNECEDORES E CLIENTES ---
col_forn, col_cli = st.columns([1.3, 1])

with col_forn:
    st.subheader("🚛 Maiores Fornecedores (Detalhado)")
    if not df_f.empty:
        df_forn = df_f[df_f["tipoMovimento"] == "Entrada"].sort_values("valorTotal", ascending=False)
        
        for _, row in df_forn.iterrows():
            fornecedor = row.get("razaoSocialClienteFornecedor", "Fornecedor")
            valor = row.get("valorTotal", 0)
            nf = row.get("numero", "N/A")
            
            with st.expander(f"{fornecedor} | NF: {nf} | {format_br(valor)}"):
                if "itens" in row and isinstance(row["itens"], list):
                    itens_df = pd.DataFrame(row["itens"])
                    if not itens_df.empty:
                        # Ajuste de colunas conforme estrutura do JSON
                        cols_show = ["descricaoProduto", "quantidade", "valorUnitario", "valorTotal"]
                        existentes = [c for c in cols_show if c in itens_df.columns]
                        st.dataframe(itens_df[existentes].style.format({
                            "valorUnitario": format_br, "valorTotal": format_br
                        }), use_container_width=True)
    else:
        st.info("Sem dados de fornecedores para esta competência.")

with col_cli:
    st.subheader("🎯 Maiores Clientes")
    if not df_f.empty:
        df_cli = df_f[df_f["tipoMovimento"] == "Prestado"]
        if not df_cli.empty:
            top_cli = df_cli.groupby("razaoSocialClienteFornecedor")["valorTotal"].sum().reset_index()
            top_cli = top_cli.sort_values("valorTotal").tail(8)
            
            fig_cli = px.bar(top_cli, x="valorTotal", y="razaoSocialClienteFornecedor", orientation="h",
                             text=top_cli["valorTotal"].apply(format_br),
                             color_discrete_sequence=[colors["accent"]])
            fig_cli.update_layout(xaxis_title=None, yaxis_title=None, height=400)
            st.plotly_chart(fig_cli, use_container_width=True)

st.divider()

# --- TOP FONTES DE FATURAMENTO ---
st.subheader("💰 Top Fontes de Faturamento (Produtos/Serviços)")
if not df_f.empty:
    fontes = []
    for _, row in df_f.iterrows():
        if row["tipoMovimento"] == "Prestado" and "itens" in row and isinstance(row["itens"], list):
            for i in row["itens"]:
                nome = i.get("nomeServico") or i.get("descricaoProduto") or "Receita"
                fontes.append({"fonte": nome, "valor": i.get("valorItem") or i.get("valorTotal") or 0})
    
    if fontes:
        df_fontes = pd.DataFrame(fontes).groupby("fonte")["valor"].sum().reset_index()
        df_fontes = df_fontes.sort_values("valor").tail(8)
        
        fig_fontes = px.bar(df_fontes, x="valor", y="fonte", orientation="h",
                            text=df_fontes["valor"].apply(format_br),
                            color_discrete_sequence=["#10b981"])
        fig_fontes.update_layout(height=400)
        st.plotly_chart(fig_fontes, use_container_width=True)

st.divider()

# --- FOLHA DE PAGAMENTO ---
st.subheader("👥 Detalhamento de Folha de Pagamento")
if not df_d.empty:
    nome_col = "nome" if "nome" in df_d.columns else "nomeTrabalhador"
    
    # Selecionando colunas: Nome, Função (tipoRecibo), Salário Bruto (totalProventos), Líquido (totalLiquido)
    df_folha_view = df_d[[nome_col, "tipoRecibo", "totalProventos", "totalLiquido"]].copy()
    df_folha_view.columns = ["Nome", "Função/Tipo", "Salário Bruto", "Salário Líquido"]

    st.dataframe(
        df_folha_view.style.format({
            "Salário Bruto": format_br,
            "Salário Líquido": format_br
        }),
        use_container_width=True,
        hide_index=True
    )
else:
    st.info("Nenhum dado de folha disponível para este período.")