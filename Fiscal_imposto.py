import requests
import json
import os
import time

# ---------------- CONFIGURAÇÕES ---------------- #
PASTA_RAIZ = r"C:\oneflow_bi\dados_powerbi"
ARQUIVO_TOKEN = r"C:\oneflow_bi\token_usuario.json"
PERIODOS = ["202601", "202602", "202603"]

ENDPOINTS = {
    "notas_detalhe": "/oneflow/empresa/fiscal/documentos/listar",
    "totais_faturamento": "/oneflow/empresa/fiscal/documentos/totais",
    "resumo_apuracao": "/oneflow/empresa/fiscal/apuracao/resumo",
    "simples_aliquotas": "/oneflow/empresa/fiscal/simplesnacional/aliquotas",
    "quantidade_notas": "/oneflow/empresa/fiscal/documentos/quantidade"
}

# ---------------- GESTÃO DE TOKENS ---------------- #
def carregar_tokens():
    if os.path.exists(ARQUIVO_TOKEN):
        with open(ARQUIVO_TOKEN, "r") as f: return json.load(f)
    return None

def salvar_tokens(token, refresh_token):
    with open(ARQUIVO_TOKEN, "w") as f:
        json.dump({"token": token, "refresh_token": refresh_token}, f, indent=4)

def renovar_token_usuario():
    dados = carregar_tokens()
    if not dados: raise Exception("Arquivo 'token_usuario.json' não encontrado.")
    url = "https://app.omie.com.br/api/portal/users/refresh-token/"
    payload = {"token": dados["token"], "refresh_token": dados["refresh_token"]}
    print("🔄 Renovando token de usuário...")
    res = requests.post(url, json=payload, timeout=30)
    if res.status_code == 200:
        novo = res.json()
        salvar_tokens(novo["token"], novo["refresh_token"])
        print("✅ Token renovado e salvo com sucesso.")
        return novo["token"]
    raise Exception(f"❌ Erro na renovação: {res.status_code}")

# ---------------- INFRAESTRUTURA ---------------- #
def preparar_pastas():
    if not os.path.exists(PASTA_RAIZ): os.makedirs(PASTA_RAIZ)
    for sub in ENDPOINTS.keys():
        caminho = os.path.join(PASTA_RAIZ, sub)
        if not os.path.exists(caminho): os.makedirs(caminho)

# ---------------- EXTRAÇÃO COM "CARGA REDUZIDA" ---------------- #

def extrair_fiscal(token_empresa, cnpj, nome, competencia):
    headers = {"Authorization": f"Bearer {token_empresa}", "Accept": "application/json"}

    for chave, rota in ENDPOINTS.items():
        # Para notas_detalhe, vamos forçar um limite pequeno por página para evitar o 504
        if chave == "notas_detalhe":
            todos_dados = []
            pagina = 1
            # Reduzimos para 20 registros por vez (mais chamadas, porém muito mais leves)
            params_base = f"competencia={competencia}&registrosPorPagina=20"
            
            while True:
                url = f"https://rest.oneflow.com.br/api{rota}?{params_base}&pagina={pagina}"
                sucesso_pag = False
                
                for t in range(5): # 5 tentativas por página
                    try:
                        res = requests.get(url, headers=headers, timeout=120)
                        if res.status_code == 200:
                            js = res.json()
                            lista = js.get("result", []) if isinstance(js, dict) else js
                            
                            if not lista: # Fim das notas
                                sucesso_pag = True
                                break
                            
                            todos_dados.extend(lista)
                            print(f"      [OK] {chave} ({competencia}) - Página {pagina} (Acumulado: {len(todos_dados)} notas)")
                            pagina += 1
                            sucesso_pag = True
                            break
                        elif res.status_code == 504:
                            print(f"      [AVISO] Timeout na pág {pagina}. Reduzindo velocidade... (Tenta {t+1}/5)")
                            time.sleep(10) # Espera maior para o servidor "respirar"
                        else:
                            print(f"      [ERRO] Status {res.status_code} na pág {pagina}")
                            break
                    except Exception as e:
                        print(f"      [REDE] Erro na pág {pagina}: {e}. Tentando em 10s...")
                        time.sleep(10)
                
                if not sucesso_pag or not lista: break

            if todos_dados:
                caminho = os.path.join(PASTA_RAIZ, chave, f"{chave}_{cnpj}_{competencia}.json")
                with open(caminho, 'w', encoding='utf-8') as f:
                    json.dump(todos_dados, f, ensure_ascii=False, indent=4)

        else:
            # Demais endpoints (Totais, Apuração, etc) que são leves
            url = f"https://rest.oneflow.com.br/api{rota}?competencia={competencia}"
            if chave == "resumo_apuracao": url += "&imposto=SIMPLES"
            
            for t in range(3):
                try:
                    res = requests.get(url, headers=headers, timeout=60)
                    if res.status_code == 200:
                        caminho = os.path.join(PASTA_RAIZ, chave, f"{chave}_{cnpj}_{competencia}.json")
                        with open(caminho, 'w', encoding='utf-8') as f:
                            json.dump(res.json(), f, ensure_ascii=False, indent=4)
                        print(f"      [OK] {chave} ({competencia})")
                        break
                except: time.sleep(5)

# ---------------- AUXILIARES OMIE/ONEFLOW ---------------- #

def buscar_hash_escritorio(user_token):
    url = "https://app.omie.com.br/api/portal/apps/"
    res = requests.get(url, headers={"Authorization": f"Bearer {user_token}"}, timeout=30)
    if res.status_code == 200:
        app = next((a for a in res.json() if a.get('app_type') == 'ONEFLOW'), None)
        return app['app_hash'] if app else None
    return None

def gerar_token_especifico(user_token, hash_alvo):
    url = f"https://app.omie.com.br/api/portal/apps/{hash_alvo}/token/"
    res = requests.get(url, headers={"Authorization": f"Bearer {user_token}"}, timeout=30)
    return res.json().get('token') if res.status_code == 200 else None

def listar_clientes(token_esc, hash_esc):
    url = "https://rest.oneflow.com.br/api/oneflow/escritorio/empresas/listar?pagina=1"
    res = requests.get(url, headers={"Authorization": f"Bearer {token_esc}", "app-hash": hash_esc}, timeout=30)
    if res.status_code == 200:
        empresas = res.json().get('result', {}).get('empresas', [])
        print(f"🏢 Empresas encontradas: {len(empresas)}")
        return empresas
    return []

# ---------------- EXECUÇÃO ---------------- #

if __name__ == "__main__":
    preparar_pastas()
    try:
        USER_TOKEN = renovar_token_usuario()
        h_esc = buscar_hash_escritorio(USER_TOKEN)
        if h_esc:
            tk_esc = gerar_token_especifico(USER_TOKEN, h_esc)
            empresas = listar_clientes(tk_esc, h_esc)
            for emp in empresas:
                print(f"\n--- Processando: {emp['razao']} ---")
                cnpj_limpo = emp['cnpj'].replace('.', '').replace('/', '').replace('-', '')
                tk_emp = gerar_token_especifico(USER_TOKEN, emp['apphash'])
                if tk_emp:
                    for mes in PERIODOS:
                        extrair_fiscal(tk_emp, cnpj_limpo, emp['razao'], mes)
        print("\n✅ Extração FISCAL concluída!")
    except Exception as e:
        print(f"\n🛑 Erro: {e}")