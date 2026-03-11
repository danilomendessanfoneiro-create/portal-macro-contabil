import requests
import json

# --- CONFIGURAÇÕES ---
TOKEN = "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJleHAiOjE3NzI5MjQ2MTEsInVpZCI6InF2dm9teTYwIiwidXVpZCI6IkUwMDdBRDc3LTgxRDAtNEI3NS05MDhFLTM1RTg4MDVENENCRSIsImVtYWlsIjoibWFjcm9jb250YWJpbEBvdXRsb29rLmNvbSJ9.zeJ3a9fZc6KNVnO0W6op9Y12Bg6thTWZz3zOzkY91MM"
BASE_URL = "https://rest.oneflow.com.br/api"

headers = {
    "Authorization": f"Bearer {TOKEN}",
    "accept": "application/json",
    "Content-Type": "application/json"
}

def testar_listagem():
    print("--- Tentativa 1: Lista de Escritório (Parceiro) ---")
    url_escritorio = f"{BASE_URL}/oneflow/escritorio/empresas/listar"
    
    try:
        res = requests.get(url_escritorio, headers=headers)
        if res.status_code == 200:
            empresas = res.json()
            # Se retornar erro interno do servidor no JSON
            if isinstance(empresas, dict) and "errorType" in empresas:
                print("   [X] O servidor deu erro interno (Provável falta de perfil Partner).")
            else:
                print(f"   [OK] Sucesso! Encontrei {len(empresas)} empresas.")
                print(json.dumps(empresas, indent=2))
                return
        else:
            print(f"   [X] Erro {res.status_code}: {res.text}")
    except Exception as e:
        print(f"   [X] Erro na chamada: {e}")

    print("\n--- Tentativa 2: Dados da Empresa do Usuário ---")
    # Se você não for parceiro, você deve ao menos ver a sua própria empresa
    url_basico = f"{BASE_URL}/oneflow/empresa/geral/dadosbasicos"
    res_b = requests.get(url_basico, headers=headers)
    
    if res_b.status_code == 200:
        print("   [OK] Você não é um parceiro global, mas tem acesso a esta empresa:")
        print(json.dumps(res_b.json(), indent=2))
    else:
        print(f"   [X] Erro ao buscar dados básicos: {res_b.status_code}")

if __name__ == "__main__":
    testar_listagem()