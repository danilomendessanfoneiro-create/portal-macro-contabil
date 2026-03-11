
import requests

import json

import os



# --- CONFIGURAÇÕES ---

USER_TOKEN = "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJleHAiOjE3NzI5MjQ2MTEsInVpZCI6InF2dm9teTYwIiwidXVpZCI6IkUwMDdBRDc3LTgxRDAtNEI3NS05MDhFLTM1RTg4MDVENENCRSIsImVtYWlsIjoibWFjcm9jb250YWJpbEBvdXRsb29rLmNvbSJ9.zeJ3a9fZc6KNVnO0W6op9Y12Bg6thTWZz3zOzkY91MM"

PERIODOS = ["202601", "202602", "202603"] 

PASTA_RAIZ = r"C:\oneflow_bi\dados_powerbi"



ENDPOINTS = {

    "notas_detalhe": "/oneflow/empresa/fiscal/documentos/listar",

    "totais_faturamento": "/oneflow/empresa/fiscal/documentos/totais",

    "resumo_apuracao": "/oneflow/empresa/fiscal/apuracao/resumo",

    "simples_aliquotas": "/oneflow/empresa/fiscal/simplesnacional/aliquotas",

    "quantidade_notas": "/oneflow/empresa/fiscal/documentos/quantidade"

}



def preparar_pastas():

    if not os.path.exists(PASTA_RAIZ): os.makedirs(PASTA_RAIZ)

    for sub in ENDPOINTS.keys():

        caminho = os.path.join(PASTA_RAIZ, sub)

        if not os.path.exists(caminho): os.makedirs(caminho)



def buscar_hash_escritorio():

    url = "https://app.omie.com.br/api/portal/apps/"

    headers = {"Authorization": f"Bearer {USER_TOKEN}"}

    res = requests.get(url, headers=headers)

    if res.status_code == 200:

        app = next((a for a in res.json() if a.get('app_type') == 'ONEFLOW'), None)

        return app['app_hash'] if app else None

    return None



def gerar_token_especifico(hash_alvo):

    url = f"https://app.omie.com.br/api/portal/apps/{hash_alvo}/token/"

    headers = {"Authorization": f"Bearer {USER_TOKEN}"}

    res = requests.get(url, headers=headers)

    return res.json().get('token') if res.status_code == 200 else None



def listar_clientes(token_esc, hash_esc):

    url = "https://rest.oneflow.com.br/api/oneflow/escritorio/empresas/listar?pagina=1"

    headers = {"Authorization": f"Bearer {token_esc}", "app-hash": hash_esc}

    res = requests.get(url, headers=headers)

    return res.json().get('result', {}).get('empresas', []) if res.status_code == 200 else []



def extrair_fiscal(token_empresa, cnpj, nome, competencia):

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

    h_esc = buscar_hash_escritorio()

    if h_esc:

        tk_esc = gerar_token_especifico(h_esc)

        empresas = listar_clientes(tk_esc, h_esc)

        for emp in empresas:

            print(f"\n--- Fiscal: {emp['razao']} ---")

            cnpj_limpo = emp['cnpj'].replace('.', '').replace('/', '').replace('-', '')

            tk_emp = gerar_token_especifico(emp['apphash'])

            if tk_emp:

                for mes in PERIODOS:

                    extrair_fiscal(tk_emp, cnpj_limpo, emp['razao'], mes)

    print(f"\nExtração FISCAL concluída!")