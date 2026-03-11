import requests
import json

TOKEN = "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJleHAiOjE3NzI5MjQ2MTEsInVpZCI6InF2dm9teTYwIiwidXVpZCI6IkUwMDdBRDc3LTgxRDAtNEI3NS05MDhFLTM1RTg4MDVENENCRSIsImVtYWlsIjoibWFjcm9jb250YWJpbEBvdXRsb29rLmNvbSJ9.zeJ3a9fZc6KNVnO0W6op9Y12Bg6thTWZz3zOzkY91MM"
APP_HASH = "danilo-aqex3x7h"

url = f"https://app.omie.com.br/api/oneflow/v1/{APP_HASH}/companies"

headers = {
    "Authorization": f"Bearer {TOKEN}",
    "Content-Type": "application/json"
}

response = requests.get(url, headers=headers)

print("Status:", response.status_code)

print("\nResposta da API:\n")
print(response.text)