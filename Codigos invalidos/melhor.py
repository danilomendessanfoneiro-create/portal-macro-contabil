import requests
import json
import os

# --- CONFIGURAÇÕES ---
USER_TOKEN = "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJleHAiOjE3NzI5MjQ2MTEsInVpZCI6InF2dm9teTYwIiwidXVpZCI6IkUwMDdBRDc3LTgxRDAtNEI3NS05MDhFLTM1RTg4MDVENENCRSIsImVtYWlsIjoibWFjcm9jb250YWJpbEBvdXRsb29rLmNvbSJ9.zeJ3a9fZc6KNVnO0W6op9Y12Bg6thTWZz3zOzkY91MM"
COMPETENCIA = "202601"
# FORÇANDO O CAMINHO ABSOLUTO PARA NÃO TER ERRO
PASTA_DESTINO = r"C:\oneflow_bi\dados_powerbi"

def criar_pasta():
    if not os.path.exists(PASTA_DESTINO):
        os.makedirs(PASTA_DESTINO)
        print(f"Pasta criada em: {PASTA_DESTINO}")

def buscar_hash_escritorio():
    url = "https://app.omie.com.br/api/portal/apps/"
    headers = {"Authorization": f"Bearer {USER_TOKEN}", "Accept": "application/json"}
    res = requests.get(url, headers=headers)
    if res.status_code == 200:
        apps = res.json()
        app = next((a for a in apps if a.get('app_type') == 'ONEFLOW'), None)
        return app['app_hash'] if app else None
    return None

def gerar_token_especifico(hash_alvo):
    url = f"https://app.omie.com.br/api/portal/apps/{hash_alvo}/token/"
    headers = {"Authorization": f"Bearer {USER_TOKEN}"}
    res = requests.get(url, headers=headers)
    if res.status_code == 200:
        return res.json().get('token')
    return None

def listar_clientes(token_esc, hash_esc):
    url = "https://rest.oneflow.com.br/api/oneflow/escritorio/empresas/listar?pagina=1"
    headers = {"Authorization": f"Bearer {token_esc}", "app-hash": hash_esc}
    res = requests.get(url, headers=headers)
    if res.status_code == 200:
        return res.json().get('result', {}).get('empresas', [])
    return []

def baixar_detalhe_notas(token_empresa, cnpj, nome):
    print(f"   -> Solicitando notas de: {nome}")
    
    url = f"https://rest.oneflow.com.br/api/oneflow/empresa/fiscal/documentos/listar?competencia={COMPETENCIA}"
    headers = {"Authorization": f"Bearer {token_empresa}", "Accept": "application/json"}
    
    res = requests.get(url, headers=headers)
    
    if res.status_code == 200:
        dados = res.json()
        
        # Se a lista vier vazia [], o OneFlow não tem notas nessa competência
        if not dados:
            print(f"      [AVISO] Sem notas para {nome} em {COMPETENCIA}.")
            return

        nome_arquivo = f"notas_{cnpj}_{COMPETENCIA}.json"
        caminho_completo = os.path.join(PASTA_DESTINO, nome_arquivo)
        
        with open(caminho_completo, 'w', encoding='utf-8') as f:
            json.dump(dados, f, ensure_ascii=False, indent=4)
        print(f"      [SUCESSO] Salvo: {nome_arquivo} ({len(dados)} registros)")
    else:
        print(f"      [ERRO {res.status_code}] Resposta: {res.text[:100]}")

if __name__ == "__main__":
    criar_pasta()
    print("Iniciando extração...")
    
    h_esc = buscar_hash_escritorio()
    if h_esc:
        tk_esc = gerar_token_especifico(h_esc)
        empresas = listar_clientes(tk_esc, h_esc)
        
        print(f"Escritório OK. Processando {len(empresas)} clientes...\n")
        
        for emp in empresas:
            h_emp = emp['apphash']
            razao = emp['razao']
            cnpj_id = emp['cnpj'].replace('.', '').replace('/', '').replace('-', '')
            
            tk_emp = gerar_token_especifico(h_emp)
            
            if tk_emp:
                baixar_detalhe_notas(tk_emp, cnpj_id, razao)
            else:
                print(f"   [!] Erro ao gerar token para {razao}")
    else:
        print("[ERRO] Escritório não encontrado.")

    print(f"\nVerifique agora a pasta: {PASTA_DESTINO}")