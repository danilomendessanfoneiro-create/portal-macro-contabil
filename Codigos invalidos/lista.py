import requests
import json

# Use o Token do Usuário que você pegou na URL /me/token/
USER_TOKEN = "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJleHAiOjE3NzI5MjQ2MTEsInVpZCI6InF2dm9teTYwIiwidXVpZCI6IkUwMDdBRDc3LTgxRDAtNEI3NS05MDhFLTM1RTg4MDVENENCRSIsImVtYWlsIjoibWFjcm9jb250YWJpbEBvdXRsb29rLmNvbSJ9.zeJ3a9fZc6KNVnO0W6op9Y12Bg6thTWZz3zOzkY91MM"

def buscar_hash_escritorio():
    print("--- 1. Buscando Aplicativos Disponíveis ---")
    url = "https://app.omie.com.br/api/portal/apps/"
    headers = {"Authorization": f"Bearer {USER_TOKEN}", "Accept": "application/json"}
    
    res = requests.get(url, headers=headers)
    if res.status_code == 200:
        apps = res.json()
        # Procuramos o app que é do tipo ONEFLOW
        oneflow_app = next((a for a in apps if a.get('app_type') == 'ONEFLOW'), None)
        
        if oneflow_app:
            app_hash = oneflow_app['app_hash']
            print(f"[OK] Escritório encontrado! Hash: {app_hash}")
            return app_hash
        else:
            print("[!] Nenhum app do tipo ONEFLOW encontrado. Verifique se você é admin do escritório.")
            return None
    else:
        print(f"[ERRO] Falha ao listar apps: {res.status_code}")
        return None

def gerar_token_escritorio(app_hash):
    print(f"--- 2. Gerando Token do Escritório ({app_hash}) ---")
    url = f"https://app.omie.com.br/api/portal/apps/{app_hash}/token/"
    headers = {"Authorization": f"Bearer {USER_TOKEN}"}
    
    res = requests.get(url, headers=headers)
    if res.status_code == 200:
        dados = res.json()
        token_escritorio = dados.get('token')
        print("[OK] Token do Escritório gerado com sucesso!")
        return token_escritorio
    else:
        print(f"[ERRO] Falha ao gerar token do app: {res.status_code} - {res.text}")
        return None

def listar_clientes(token_escritorio, app_hash_escritorio):
    print(f"--- 3. Listando Clientes (Hash: {app_hash_escritorio}) ---")
    
    # Tentaremos a página 1, que é o padrão de algumas rotas do OneFlow
    url = "https://rest.oneflow.com.br/api/oneflow/escritorio/empresas/listar?pagina=1"
    
    headers = {
        "Authorization": f"Bearer {token_escritorio}", 
        "Accept": "application/json",
        "app-hash": app_hash_escritorio  # Reafirmando o contexto do escritório
    }
    
    res = requests.get(url, headers=headers)
    
    if res.status_code == 200:
        dados = res.json()
        # Se vier o BYEBYE de novo, tentaremos sem o parâmetro de página
        if isinstance(dados, dict) and dados.get("proto") == "PROTO_BYEBYE":
            print("[!] Recebi BYEBYE. Tentando sem o parâmetro de página...")
            url_simples = "https://rest.oneflow.com.br/api/oneflow/escritorio/empresas/listar"
            res = requests.get(url_simples, headers=headers)
            dados = res.json()

        if isinstance(dados, list):
            print(f"[SUCESSO] Encontrei {len(dados)} empresas!")
            print(json.dumps(dados, indent=2))
            return dados
        else:
            print("[AVISO] O servidor respondeu, mas não veio uma lista.")
            print(json.dumps(dados, indent=2))
    else:
        print(f"[ERRO] Status: {res.status_code} - {res.text}")

# Ajuste também a chamada no final do script:
if __name__ == "__main__":
    hash_esc = buscar_hash_escritorio()
    if hash_esc:
        tk_esc = gerar_token_escritorio(hash_esc)
        if tk_esc:
            # Passamos o hash_esc para a função agora
            listar_clientes(tk_esc, hash_esc)

if __name__ == "__main__":
    hash_esc = buscar_hash_escritorio()
    if hash_esc:
        tk_esc = gerar_token_escritorio(hash_esc)
        if tk_esc:
            listar_clientes(tk_esc)