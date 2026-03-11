import requests
import json
import os

# --- CONFIGURAÇÕES DE ACESSO ---
TOKEN_USUARIO = "COLE_AQUI_O_TOKEN_NORMAL"
REFRESH_TOKEN = "COLE_AQUI_O_REFRESH_TOKEN"

PERIODOS = ["202601", "202602", "202603"]
PASTA_RAIZ = r"C:\oneflow_bi\dados_powerbi"

ENDPOINTS = {
    "folha_trabalhador_cadastro": "/oneflow/empresa/folha/trabalhador/dadosbasicos",
    "folha_trabalhador_eventos": "/oneflow/empresa/folha/trabalhador/eventos",
    "folha_status_mensal": "/oneflow/empresa/folha/statusfolha",
    "folha_recibos_totais": "/oneflow/empresa/folha/recibos/totais"
}

def renovar_token():
    global TOKEN_USUARIO, REFRESH_TOKEN
    print("🔄 Token vencido! Tentando renovação automática...")
    url = "https://app.omie.com.br/api/portal/users/refresh-token/"
    payload = {"token": TOKEN_USUARIO, "refresh_token": REFRESH_TOKEN}
    res = requests.post(url, json=payload)
    if res.status_code == 200:
        dados = res.json()
        TOKEN_USUARIO = dados['token']
        REFRESH_TOKEN = dados['refresh_token']
        print("✅ Token renovado com sucesso!")
        return True
    return False

def preparar_pastas():
    if not os.path.exists(PASTA_RAIZ): os.makedirs(PASTA_RAIZ)
    for sub in ENDPOINTS.keys():
        caminho = os.path.join(PASTA_RAIZ, sub)
        if not os.path.exists(caminho): os.makedirs(caminho)

def buscar_hash_escritorio():
    url = "https://app.omie.com.br/api/portal/apps/"
    headers = {"Authorization": f"Bearer {TOKEN_USUARIO}"}
    res = requests.get(url, headers=headers)
    if res.status_code == 401:
        if renovar_token():
            headers = {"Authorization": f"Bearer {TOKEN_USUARIO}"}
            res = requests.get(url, headers=headers)
    if res.status_code == 200:
        app = next((a for a in res.json() if a.get('app_type') == 'ONEFLOW'), None)
        return app['app_hash'] if app else None
    return None

def gerar_token_especifico(hash_alvo):
    url = f"https://app.omie.com.br/api/portal/apps/{hash_alvo}/token/"
    headers = {"Authorization": f"Bearer {TOKEN_USUARIO}"}
    res = requests.get(url, headers=headers)
    return res.json().get('token') if res.status_code == 200 else None

def listar_clientes(token_esc, hash_esc):
    url = "https://rest.oneflow.com.br/api/oneflow/escritorio/empresas/listar?pagina=1"
    headers = {"Authorization": f"Bearer {token_esc}", "app-hash": hash_esc}
    res = requests.get(url, headers=headers)
    return res.json().get('result', {}).get('empresas', []) if res.status_code == 200 else []

def extrair_dp(token_empresa, cnpj, nome, competencia):
    for chave, rota in ENDPOINTS.items():
        url = f"https://rest.oneflow.com.br/api{rota}?competencia={competencia}"
        headers = {"Authorization": f"Bearer {token_empresa}", "Accept": "application/json"}
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

if __name__ == "__main__":
    preparar_pastas()
    print("🚀 Iniciando Extração DP...")
    h_esc = buscar_hash_escritorio()
    if h_esc:
        tk_esc = gerar_token_especifico(h_esc)
        empresas = listar_clientes(tk_esc, h_esc)
        for emp in empresas:
            print(f"\n>>> DP: {emp['razao']}")
            cnpj_limpo = emp['cnpj'].replace('.', '').replace('/', '').replace('-', '')
            tk_emp = gerar_token_especifico(emp['apphash'])
            if tk_emp:
                for mes in PERIODOS:
                    extrair_dp(tk_emp, cnpj_limpo, emp['razao'], mes)
    print(f"\nExtração DP concluída!")