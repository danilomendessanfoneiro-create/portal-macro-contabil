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

# ---------------- TOKEN ---------------- #

def carregar_tokens():

    if os.path.exists(ARQUIVO_TOKEN):

        with open(ARQUIVO_TOKEN,"r") as f:
            return json.load(f)

    return None


def salvar_tokens(token, refresh_token):

    with open(ARQUIVO_TOKEN,"w") as f:

        json.dump({
            "token":token,
            "refresh_token":refresh_token
        },f,indent=4)


def renovar_token_usuario():

    dados=carregar_tokens()

    if not dados:
        raise Exception("Arquivo token_usuario.json não encontrado")

    url="https://app.omie.com.br/api/portal/users/refresh-token/"

    payload={
        "token":dados["token"],
        "refresh_token":dados["refresh_token"]
    }

    print("🔄 Renovando token de usuário...")

    res=requests.post(url,json=payload,timeout=30)

    if res.status_code==200:

        novo=res.json()

        salvar_tokens(novo["token"],novo["refresh_token"])

        print("✅ Token renovado")

        return novo["token"]

    raise Exception(f"Erro renovando token {res.status_code}")

# ---------------- INFRA ---------------- #

def preparar_pastas():

    if not os.path.exists(PASTA_RAIZ):
        os.makedirs(PASTA_RAIZ)

    for sub in ENDPOINTS:

        pasta=os.path.join(PASTA_RAIZ,sub)

        if not os.path.exists(pasta):
            os.makedirs(pasta)

# ---------------- EXTRAÇÃO ---------------- #

def extrair_fiscal(token_empresa,cnpj,nome,competencia):

    headers={
        "Authorization":f"Bearer {token_empresa}",
        "Accept":"application/json"
    }

    for chave,rota in ENDPOINTS.items():

        print(f"\n   → {chave} ({competencia})")

        if chave=="notas_detalhe":

            todos_dados=[]

            # separar para evitar timeout
            for tipo in ["Saida","Entrada"]:

                print(f"      Buscando {tipo}")

                pagina=1
                registros=10

                while True:

                    url=f"https://rest.oneflow.com.br/api{rota}?competencia={competencia}&tipoMovimento={tipo}&pagina={pagina}&registrosPorPagina={registros}"

                    lista=[]

                    for tentativa in range(5):

                        try:

                            res=requests.get(url,headers=headers,timeout=120)

                            if res.status_code==200:

                                js=res.json()

                                if isinstance(js,dict):
                                    lista=js.get("result",[])
                                elif isinstance(js,list):
                                    lista=js

                                if not lista:
                                    break

                                todos_dados.extend(lista)

                                print(f"      {tipo} página {pagina} → {len(lista)}")

                                pagina+=1

                                time.sleep(2)

                                break

                            elif res.status_code==504:

                                print(f"      timeout {tipo} página {pagina} tentativa {tentativa+1}")

                                time.sleep(15)

                            else:

                                print(f"      erro HTTP {res.status_code}")

                                break

                        except Exception as e:

                            print(f"      erro rede {e}")

                            time.sleep(10)

                    if not lista:
                        break

            if todos_dados:

                caminho=os.path.join(
                    PASTA_RAIZ,
                    chave,
                    f"{chave}_{cnpj}_{competencia}.json"
                )

                with open(caminho,"w",encoding="utf-8") as f:

                    json.dump(todos_dados,f,ensure_ascii=False,indent=4)

                print(f"      💾 salvo {len(todos_dados)} notas")

        else:

            url=f"https://rest.oneflow.com.br/api{rota}?competencia={competencia}"

            if chave=="resumo_apuracao":
                url+="&imposto=SIMPLES"

            for tentativa in range(3):

                try:

                    res=requests.get(url,headers=headers,timeout=60)

                    if res.status_code==200:

                        caminho=os.path.join(
                            PASTA_RAIZ,
                            chave,
                            f"{chave}_{cnpj}_{competencia}.json"
                        )

                        with open(caminho,"w",encoding="utf-8") as f:

                            json.dump(res.json(),f,ensure_ascii=False,indent=4)

                        print("      OK")

                        break

                except:

                    time.sleep(5)

# ---------------- OMIE / ONEFLOW ---------------- #

def buscar_hash_escritorio(user_token):

    url="https://app.omie.com.br/api/portal/apps/"

    res=requests.get(url,headers={"Authorization":f"Bearer {user_token}"},timeout=30)

    if res.status_code==200:

        apps=res.json()

        app=next((a for a in apps if a.get("app_type")=="ONEFLOW"),None)

        if app:
            return app["app_hash"]

    return None


def gerar_token_especifico(user_token,hash_alvo):

    url=f"https://app.omie.com.br/api/portal/apps/{hash_alvo}/token/"

    res=requests.get(url,headers={"Authorization":f"Bearer {user_token}"},timeout=30)

    if res.status_code==200:

        return res.json().get("token")

    return None


def listar_clientes(token_esc,hash_esc):

    url="https://rest.oneflow.com.br/api/oneflow/escritorio/empresas/listar?pagina=1"

    headers={
        "Authorization":f"Bearer {token_esc}",
        "app-hash":hash_esc
    }

    res=requests.get(url,headers=headers,timeout=30)

    if res.status_code==200:

        empresas=res.json().get("result",{}).get("empresas",[])

        print(f"\n🏢 Empresas encontradas: {len(empresas)}")

        return empresas

    return []

# ---------------- EXECUÇÃO ---------------- #

if __name__=="__main__":

    preparar_pastas()

    try:

        USER_TOKEN=renovar_token_usuario()

        hash_escritorio=buscar_hash_escritorio(USER_TOKEN)

        if hash_escritorio:

            token_escritorio=gerar_token_especifico(USER_TOKEN,hash_escritorio)

            empresas=listar_clientes(token_escritorio,hash_escritorio)

            for emp in empresas:

                print(f"\n--- {emp['razao']} ---")

                cnpj_limpo=emp["cnpj"].replace(".","").replace("/","").replace("-","")

                token_empresa=gerar_token_especifico(USER_TOKEN,emp["apphash"])

                if token_empresa:

                    for mes in PERIODOS:

                        extrair_fiscal(token_empresa,cnpj_limpo,emp["razao"],mes)

        print("\n✅ EXTRAÇÃO FISCAL FINALIZADA")

    except Exception as e:

        print(f"\n🛑 ERRO: {e}")