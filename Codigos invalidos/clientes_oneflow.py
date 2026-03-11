import requests
import pandas as pd

TOKEN_USUARIO = "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJleHAiOjE3NzI5MjQ2MTEsInVpZCI6InF2dm9teTYwIiwidXVpZCI6IkUwMDdBRDc3LTgxRDAtNEI3NS05MDhFLTM1RTg4MDVENENCRSIsImVtYWlsIjoibWFjcm9jb250YWJpbEBvdXRsb29rLmNvbSJ9.zeJ3a9fZc6KNVnO0W6op9Y12Bg6thTWZz3zOzkY91MM"
APP_HASH = "danilo-aqex3x7h"

url = f"https://app.omie.com.br/api/oneflow/{APP_HASH}/companies"

headers = {
    "Authorization": f"Bearer {TOKEN_USUARIO}",
    "Accept": "application/json"
}

response = requests.get(url, headers=headers)

print("Status:", response.status_code)

dados = response.json()

print("Quantidade de registros:", len(dados))

df = pd.DataFrame(dados)

df.to_csv("clientes_oneflow.csv", index=False)

print("Arquivo clientes_oneflow.csv criado com sucesso!")