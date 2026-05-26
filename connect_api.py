import requests
from config import TIENDANUBE_STORE_ID, TIENDANUBE_ACCESS_TOKEN, TIENDANUBE_USER_AGENT

# Configuración básica
STORE_ID = TIENDANUBE_STORE_ID
ACCESS_TOKEN = TIENDANUBE_ACCESS_TOKEN
BASE_URL = f"https://api.tiendanube.com/v1/{STORE_ID}"

# Headers necesarios
headers = {
    "Authentication": f"bearer {ACCESS_TOKEN}",
    "User-Agent": TIENDANUBE_USER_AGENT,
    "Content-Type": "application/json"
}

def test_connection():
    """Prueba básica de conexión con la API"""
    try:
        print("\nProbando conexión con Tienda Nube API...")
        response = requests.get(f"{BASE_URL}/products", headers=headers)
        response.raise_for_status()  # Verifica errores HTTP
        
        data = response.json()
        print(f"\n✅ Conexión exitosa!")
        print(f"Total de productos: {len(data)}")
        if data:
            print(f"\nPrimer producto:")
            print(f"Nombre: {data[0].get('name', {}).get('es', 'Sin nombre')}")
            print(f"ID: {data[0].get('id')}")
            print(f"Precio: {data[0].get('price')}")
        
        return True
        
    except Exception as e:
        print(f"\n❌ Error de conexión: {str(e)}")
        if hasattr(e, 'response'):
            print(f"Código de error: {e.response.status_code}")
            print(f"Respuesta: {e.response.text}")
        return False

# Ejecutar la prueba al correr el script
if __name__ == "__main__":
    test_connection()