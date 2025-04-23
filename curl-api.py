import requests

# URL del endpoint
TOKEN_URL = "https://www.tiendanube.com/apps/authorize/token"

# Datos necesarios para obtener el access token
payload = {
    "client_id": "17068",
    "client_secret": "2c9172f6dd4f6c96cff3fd891dcd1756e7d737f3179b6c86",
    "grant_type": "authorization_code",
    "code": "b67000215f3a53cb03039cfb0922dcbc9aa24330"
}

# Encabezados de la solicitud
headers = {
    "Content-Type": "application/json"
}

# Hacer la solicitud POST
response = requests.post(TOKEN_URL, json=payload, headers=headers)

# Manejo de la respuesta
if response.status_code == 200:
    token_data = response.json()
    print("Access Token obtenido:", token_data["access_token"])
else:
    print("Error al obtener el access token:", response.status_code, response.text)
