from colorama import Fore, Style
import threading
import os
from pathlib import Path
from dotenv import load_dotenv

# Cargar variables de entorno (busca API_KEY.ENV, .env, o api_key.env)
project_root = Path(__file__).parent.resolve()
env_files = ["API_KEY.ENV", ".env", "api_key.env", "API_KEY.ENV.txt", "api_key.env.txt"]
env_loaded = False

for file_name in env_files:
    env_path = project_root / file_name
    if env_path.exists():
        load_dotenv(env_path)
        env_loaded = True
        break

# Si no se cargó ninguna en la raíz, intentar subir un nivel (por si se ejecuta desde subcarpetas)
if not env_loaded:
    for file_name in env_files:
        env_path = project_root.parent / file_name
        if env_path.exists():
            load_dotenv(env_path)
            break

# Variables del Mayorista (Coronel)
CORONEL_CUIT = os.getenv("CORONEL_CUIT", "27958596508")
CORONEL_PASSWORD = os.getenv("CORONEL_PASSWORD", "95859650")

# Variables de Tiendanube
TIENDANUBE_STORE_ID = os.getenv("TIENDANUBE_STORE_ID", "5950659")
TIENDANUBE_ACCESS_TOKEN = os.getenv("TIENDANUBE_ACCESS_TOKEN", "cdcad052f53bae4972979dbf6900925d4e9a36dc")
TIENDANUBE_USER_AGENT = os.getenv("TIENDANUBE_USER_AGENT", "API-KEY (jgstore244@gmail.com)")

# OpenAI / Deepseek API Keys
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")

# Variables globales de configuración
DOWNLOAD_IMAGES = True

def set_download_images(value):
    """Función para cambiar el estado de descarga de imágenes"""
    global DOWNLOAD_IMAGES
    DOWNLOAD_IMAGES = value
    
def preguntar_download():
    return 't'

def preguntar_porcentaje():
    # Preguntar al usuario el porcentaje de ganancia
    print(Fore.CYAN + "\n" + "="*50)
    print(" CONFIGURACIÓN DE PORCENTAJE DE GANANCIA ")
    print("="*50 + Style.RESET_ALL)
    
    while True:
        try:
            respuesta = input(Fore.CYAN + "Ingrese el porcentaje de ganancia (ej: 40 para 40%): " + Style.RESET_ALL)
            porcentaje = int(float(respuesta))  # Convertir a float primero y luego a int
            print(Fore.GREEN + f"✔ Porcentaje de ganancia configurado a: {porcentaje}%" + Style.RESET_ALL)
            print(Fore.CYAN + "="*50 + "\n" + Style.RESET_ALL)
            return porcentaje
        except ValueError:
            print(Fore.RED + "⚠ Error: Debe ingresar un número válido. Intente nuevamente." + Style.RESET_ALL)
