import requests
import json
import os

# ---------------- CONFIGURAÇÕES ---------------- #

PASTA_RAIZ = r"C:\oneflow_bi\dados_powerbi"
ARQUIVO_TOKEN = r"C:\oneflow_bi\token_usuario.json"

PERIODOS = ["202601", "202602", "202603"]

ENDPOINTS = {

    "folha_trabalhador_cadastro": "/oneflow/empresa/folha/trabalhador/dadosbasicos",
    "folha_trabalhador_eventos": "/oneflow/empresa/folha/trabalhador/eventos",
    "folha_status_mensal": "/oneflow/empresa/folha/statusfolha",
    "folha_recibos_totais": "/oneflow/empresa/folha/recibos/totais"
}

# ---------------- TOKEN USUÁRIO ---------------- #

def carregar_tokens():

    if os.path.exists(ARQUIVO_TOKEN):
        with open(ARQUIVO_TOKEN, "r") as f:
            return json.load(f)

    return None


def salvar_tokens(token, refresh_token):

    dados = {
        "token": token,
        "refresh_token": refresh_token
    }

    with open(ARQUIVO_TOKEN, "w") as f:
        json.dump(dados, f)


def renovar_token_usuario():

    dados = carregar_tokens()

    if not dados:
        raise Exception("Arquivo de token não encontrado.")

    url = "https://app.omie.com.br/api/portal/users/refresh-token/"

    payload = {
        "token": dados["token"],
        "refresh_token": dados["refresh_token"]
    }

    headers = {"Content-Type": "application/json"}

    res = requests.post(url, json=payload, headers=headers)

    if res.status_code == 200:

        novo = res.json()

        salvar_tokens(novo["token"], novo["refresh_token"])

        print("Token de usuário renovado com sucesso")

        return novo["token"]

    else:

        raise Exception(f"Erro ao renovar token: {res.text}")

# ---------------- PREPARAR PASTAS ---------------- #

def preparar_pastas():

    if not os.path.exists(PASTA_RAIZ):
        os.makedirs(PASTA_RAIZ)

    for sub in ENDPOINTS.keys():

        caminho = os.path.join(PASTA_RAIZ, sub)

        if not os.path.exists(caminho):
            os.makedirs(caminho)

# ---------------- ONEFLOW ---------------- #

def buscar_hash_escritorio(user_token):

    url = "https://app.omie.com.br/api/portal/apps/"

    headers = {"Authorization": f"Bearer {user_token}"}

    res = requests.get(url, headers=headers)

    if res.status_code == 200:

        app = next((a for a in res.json() if a.get('app_type') == 'ONEFLOW'), None)

        return app['app_hash'] if app else None

    return None


def gerar_token_especifico(user_token, hash_alvo):

    url = f"https://app.omie.com.br/api/portal/apps/{hash_alvo}/token/"

    headers = {"Authorization": f"Bearer {user_token}"}

    res = requests.get(url, headers=headers)

    if res.status_code == 200:
        return res.json().get('token')

    return None


def listar_clientes(token_esc, hash_esc):

    url = "https://rest.oneflow.com.br/api/oneflow/escritorio/empresas/listar?pagina=1"

    headers = {
        "Authorization": f"Bearer {token_esc}",
        "app-hash": hash_esc
    }

    res = requests.get(url, headers=headers)

    if res.status_code == 200:

        return res.json().get('result', {}).get('empresas', [])

    return []

# ---------------- EXTRAÇÃO ---------------- #

def extrair_dp(token_empresa, cnpj, nome, competencia):

    for chave, rota in ENDPOINTS.items():

        url = f"https://rest.oneflow.com.br/api{rota}?competencia={competencia}"

        headers = {
            "Authorization": f"Bearer {token_empresa}",
            "Accept": "application/json"
        }

        try:

            res = requests.get(url, headers=headers)

            if res.status_code == 200:

                dados = res.json()

                if dados:

                    arquivo = f"{chave}_{cnpj}_{competencia}.json"

                    caminho = os.path.join(PASTA_RAIZ, chave, arquivo)

                    with open(caminho, 'w', encoding='utf-8') as f:

                        json.dump(dados, f, ensure_ascii=False, indent=4)

                    print(f"      [OK] {chave} ({competencia})")

        except Exception as e:

            print(f"      [ERRO] {chave} em {competencia}: {e}")

# ---------------- EXECUÇÃO ---------------- #

if __name__ == "__main__":

    preparar_pastas()

    USER_TOKEN = renovar_token_usuario()

    h_esc = buscar_hash_escritorio(USER_TOKEN)

    if h_esc:

        tk_esc = gerar_token_especifico(USER_TOKEN, h_esc)

        empresas = listar_clientes(tk_esc, h_esc)

        for emp in empresas:

            print(f"\n>>> DP: {emp['razao']}")

            cnpj_limpo = emp['cnpj'].replace('.', '').replace('/', '').replace('-', '')

            tk_emp = gerar_token_especifico(USER_TOKEN, emp['apphash'])

            if tk_emp:

                for mes in PERIODOS:

                    extrair_dp(tk_emp, cnpj_limpo, emp['razao'], mes)

    print("\nExtração DP concluída!")