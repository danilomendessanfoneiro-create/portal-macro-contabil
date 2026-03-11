import requests
import json

TOKEN_USUARIO = "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJleHAiOjE3NzI5MjQ2MTEsInVpZCI6InF2dm9teTYwIiwidXVpZCI6IkUwMDdBRDc3LTgxRDAtNEI3NS05MDhFLTM1RTg4MDVENENCRSIsImVtYWlsIjoibWFjcm9jb250YWJpbEBvdXRsb29rLmNvbSJ9.zeJ3a9fZc6KNVnO0W6op9Y12Bg6thTWZz3zOzkY91MM"
APP_HASH = "danilo-aqex3x7h"

url = f"https://app.omie.com.br/api/oneflow/{APP_HASH}/"

headers = {
    "Authorization": f"Bearer {TOKEN_USUARIO}",
    "Accept": "application/json"
}

response = requests.get(url, headers=headers)

print("Status:", response.status_code)
print("\nRetorno da API:\n")

print(response.text)