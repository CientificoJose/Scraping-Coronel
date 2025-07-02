import os
from dotenv import load_dotenv

# Cargar variables de entorno desde un archivo .env si existe
# El archivo .env NO debe ser versionado y debe estar en .gitignore
env_path = os.path.join(os.path.dirname(__file__), '..', '.env') # .env en la raíz del proyecto
load_dotenv(dotenv_path=env_path)

# --- Credenciales Coronel Mayorista ---
CORONEL_CUIT = os.getenv('CORONEL_CUIT', '27958596508') # Valor por defecto si no está en .env
CORONEL_PASSWORD = os.getenv('CORONEL_PASSWORD', '95859650') # Valor por defecto si no está en .env

# --- Credenciales Tiendanube ---
# Estos valores DEBEN estar en el archivo .env o como variables de entorno del sistema
TIENDANUBE_ACCESS_TOKEN = os.getenv('TIENDANUBE_ACCESS_TOKEN', 'cdcad052f53bae4972979dbf6900925d4e9a36dc') # Mantengo el valor hardcodeado como fallback si no hay .env
TIENDANUBE_STORE_ID = os.getenv('TIENDANUBE_STORE_ID', '5950659') # Mantengo el valor hardcodeado como fallback

# --- Credenciales DeepSeek (si se usa) ---
# DEEPSEEK_API_KEY = os.getenv('DEEPSEEK_API_KEY')

# --- Verificaciones ---
if not TIENDANUBE_ACCESS_TOKEN:
    print("ADVERTENCIA: TIENDANUBE_ACCESS_TOKEN no está configurado. La interacción con Tiendanube fallará.")
if not TIENDANUBE_STORE_ID:
    print("ADVERTENCIA: TIENDANUBE_STORE_ID no está configurado. La interacción con Tiendanube fallará.")

# Es buena práctica validar que las credenciales esenciales están presentes al inicio.
# Podríamos lanzar una excepción si faltan credenciales críticas.
# For example:
# if not TIENDANUBE_ACCESS_TOKEN or not TIENDANUBE_STORE_ID:
#     raise ValueError("Credenciales de Tiendanube (ACCESS_TOKEN, STORE_ID) no encontradas. "
#                      "Por favor, configúrelas en un archivo .env en la raíz del proyecto.")

def get_coronel_credentials():
    return {
        "cuit": CORONEL_CUIT,
        "password": CORONEL_PASSWORD
    }

def get_tiendanube_credentials():
    if not TIENDANUBE_ACCESS_TOKEN or not TIENDANUBE_STORE_ID:
        # Esto podría ser manejado de forma más robusta, quizás pidiéndolo en la GUI la primera vez
        # o mostrando un error claro que indique cómo configurar.
        print("Error: Faltan credenciales de Tiendanube. Usando valores por defecto o vacíos.")
        # Decide si retornar valores por defecto que fallarán o None, o lanzar excepción.
        # Por ahora, para mantener la ejecución similar al original, retorno los valores
        # que podrían estar hardcodeados o ser None si no hay .env ni fallback.
    return {
        "access_token": TIENDANUBE_ACCESS_TOKEN,
        "store_id": TIENDANUBE_STORE_ID
    }

# def get_deepseek_api_key():
#    return DEEPSEEK_API_KEY

# Ejemplo de cómo crear un archivo .env (NO LO EJECUTES AQUÍ, es solo un ejemplo para el usuario)
# Contenido del archivo .env en la raíz del proyecto:
# CORONEL_CUIT=tu_cuit
# CORONEL_PASSWORD=tu_password
# TIENDANUBE_ACCESS_TOKEN=tu_access_token_tiendanube
# TIENDANUBE_STORE_ID=tu_store_id_tiendanube
# DEEPSEEK_API_KEY=tu_deepseek_api_key
