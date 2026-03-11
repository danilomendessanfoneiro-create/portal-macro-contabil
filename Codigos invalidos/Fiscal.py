import requests
import json
import os

# --- CONFIGURAÇÕES DE ACESSO ---
# 1. Pegue o TOKEN NORMAL aqui: https://app.omie.com.br/api/portal/users/me/token/
TOKEN_USUARIO = "COLE_AQUI_O_TOKEN_NORMAL"
# 2. Seu HASH fixo que já funcionou antes:
HASH_ESCRITORIO = "danilo-aqex3x7h"

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

def gerar_token_especifico(hash_alvo):
    url = f"https://app.omie.com.br/api/portal/apps/{hash_alvo}/token/"
    headers = {"Authorization": f"Bearer {TOKEN_USUARIO}"}
    res = requests.get(url, headers=headers)
    if res.status_code == 200:
        return res.json().get('token')
    else:
        print(f"❌ Erro ao gerar token para o Hash {hash_alvo}: {res.status_code} - {res.text}")
        return None

def listar_clientes(token_esc, hash_esc):
    url = "https://rest.oneflow.com.br/api/oneflow/escritorio/empresas/listar?pagina=1"
    headers = {"Authorization": f"Bearer {token_esc}", "app-hash": hash_esc}
    res = requests.get(url, headers=headers)
    if res.status_code == 200:
        # Algumas vezes o OneFlow encapsula o resultado em 'result'
        dados = res.json()
        if isinstance(dados, dict) and "result" in dados:
            return dados["result"].get("empresas", [])
        return dados
    print(f"❌ Erro ao listar clientes: {res.status_code} - {res.text}")
    return []

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
    print(f"🚀 Iniciando Extração FISCAL direta para Escritório: {HASH_ESCRITORIO}")
    
    # Passo 1: Gera o token do escritório usando o HASH fixo
    tk_esc = gerar_token_especifico(HASH_ESCRITORIO)
    
    if tk_esc:
        # Passo 2: Lista as empresas
        empresas = listar_clientes(tk_esc, HASH_ESCRITORIO)
        print(f"👥 Total de empresas encontradas: {len(empresas)}")
        
        # Passo 3: Loop de extração
        for emp in empresas:
            print(f"\n--- Processando: {emp['razao']} ---")
            cnpj_limpo = emp['cnpj'].replace('.', '').replace('/', '').replace('-', '')
            tk_emp = gerar_token_especifico(emp['apphash'])
            
            if tk_emp:
                for mes in PERIODOS:
                    extrair_fiscal(tk_emp, cnpj_limpo, emp['razao'], mes)
            else:
                print(f"⚠️ Pulei a empresa {emp['razao']} por erro no token.")
    
    print(f"\nExtração FISCAL concluída!")