# Configuraciones generales, rutas, umbrales, etc.
import os

# --- Rutas Base ---
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__))) # proyecto_scraping_grafico/
DATA_DIR = os.path.join(BASE_DIR, 'data')
CONFIG_DIR = os.path.join(BASE_DIR, 'config')
CORE_DIR = os.path.join(BASE_DIR, 'core')
GUI_DIR = os.path.join(BASE_DIR, 'gui')
UTILS_DIR = os.path.join(BASE_DIR, 'utils')

# --- Directorios de Datos ---
PRODUCTOS_CORONEL_DIR = os.path.join(DATA_DIR, 'productos_coronel')
IMG_SCRAPING_DIR = os.path.join(DATA_DIR, 'img-scraping')
DB_PATH = os.path.join(DATA_DIR, 'productos.db')
API_CACHE_DIR = os.path.join(DATA_DIR, 'api_cache')
PRODUCTS_CACHE_FILE = os.path.join(API_CACHE_DIR, 'products_cache.json')

# --- Configuraciones de Scraping ---
CORONEL_BASE_URL = "https://www.coronelmayorista.com/"
LOGIN_URL = f"{CORONEL_BASE_URL}#/sign-in"
HOME_URL = f"{CORONEL_BASE_URL}#/home"
LISTA_PRECIOS_URL = f"{CORONEL_BASE_URL}#/usuario/listaPrecios"
ARTICULOS_URL = f"{CORONEL_BASE_URL}#/articulos?page=1&ORDER=ORD%3DASC&VIEW_TYPE=GRID_VI"

DEFAULT_TIMEOUT = 10 # Segundos para esperas de Selenium
MAX_RETRIES_SCRAPING = 3

# --- Configuraciones de Tiendanube API ---
# Las credenciales se moverán a credentials.py
TIENDANUBE_BASE_URL_TEMPLATE = "https://api.tiendanube.com/v1/{store_id}"
# STORE_ID y ACCESS_TOKEN se cargarán desde credentials.py
USER_AGENT_TIENDANUBE = "ProyectoScrapingGrafico/1.0 (contacto@dominio.com)" # Actualizar con datos reales

RATE_LIMIT_WINDOW = 60  # Segundos
MAX_REQUESTS_PER_WINDOW = 50
MIN_DELAY_BETWEEN_REQUESTS = 1.2 # Segundos

# --- Configuraciones de la Aplicación ---
DEFAULT_DOWNLOAD_IMAGES = False # True para descargar, False para usar URL
DEFAULT_GANANCIA_PORCENTAJE = 40 # Porcentaje

# --- Logging ---
LOGGING_CONFIG = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'standard': {
            'format': '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            'datefmt': '%Y-%m-%d %H:%M:%S',
        },
    },
    'handlers': {
        'console': {
            'level': 'INFO',
            'formatter': 'standard',
            'class': 'logging.StreamHandler',
            'stream': 'ext://sys.stdout',  # Default is stderr
        },
        'file': {
            'level': 'DEBUG',
            'formatter': 'standard',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': os.path.join(BASE_DIR, 'app.log'),
            'maxBytes': 1024*1024*5, # 5 MB
            'backupCount': 5,
            'encoding': 'utf-8',
        }
    },
    'loggers': {
        '': {  # root logger
            'handlers': ['console', 'file'],
            'level': 'DEBUG',
            'propagate': False
        },
        'selenium': { # Silenciar logs de selenium a menos que sean WARNING
            'handlers': ['console', 'file'],
            'level': 'WARNING',
            'propagate': False
        },
         'urllib3': { # Silenciar logs de urllib3 a menos que sean WARNING
            'handlers': ['console', 'file'],
            'level': 'WARNING',
            'propagate': False
        }
    }
}

# --- DeepSeek (si se usa) ---
# DEEPSEEK_API_KEY = "tu_api_key" # Mover a credentials.py
# DEEPSEEK_API_URL = "https://api.deepseek.com/..."

# Crear directorios de datos si no existen
os.makedirs(PRODUCTOS_CORONEL_DIR, exist_ok=True)
os.makedirs(IMG_SCRAPING_DIR, exist_ok=True)
os.makedirs(API_CACHE_DIR, exist_ok=True)

# --- Funciones del antiguo config.py ---
# Estas funciones (preguntar_download, preguntar_porcentaje) se integrarán en la GUI.
# Por ahora, podemos mantener las configuraciones por defecto aquí.

# Variable global para el estado de descarga de imágenes (será manejada por la GUI)
# DOWNLOAD_IMAGES = DEFAULT_DOWNLOAD_IMAGES

# def set_download_images(value: bool):
#     global DOWNLOAD_IMAGES
#     DOWNLOAD_IMAGES = value

# GANANCIA_PORCENTAJE = DEFAULT_GANANCIA_PORCENTAJE # Será manejada por la GUI

# def set_ganancia_porcentaje(value: int):
#     global GANANCIA_PORCENTAJE
#     GANANCIA_PORCENTAJE = value

print(f"Base directory: {BASE_DIR}")
print(f"Data directory: {DATA_DIR}")
print(f"Database path: {DB_PATH}")

# Inicializar las variables que antes se preguntaban, ahora se tomarán de los defaults
# o serán configurables a través de la GUI.
CURRENT_DOWNLOAD_IMAGES_STATE = DEFAULT_DOWNLOAD_IMAGES
CURRENT_GANANCIA_PORCENTAJE = DEFAULT_GANANCIA_PORCENTAJE

def get_current_download_images_state():
    return CURRENT_DOWNLOAD_IMAGES_STATE

def set_current_download_images_state(value: bool):
    global CURRENT_DOWNLOAD_IMAGES_STATE
    CURRENT_DOWNLOAD_IMAGES_STATE = value

def get_current_ganancia_porcentaje():
    return CURRENT_GANANCIA_PORCENTAJE

def set_current_ganancia_porcentaje(value: int):
    global CURRENT_GANANCIA_PORCENTAJE
    CURRENT_GANANCIA_PORCENTAJE = value

# La lógica de preguntar al usuario se moverá a la GUI.
# Las funciones originales de `config.py` (preguntar_download, preguntar_porcentaje)
# no se replicarán aquí directamente, ya que la GUI se encargará de obtener estos valores.
# Los valores se almacenarán y recuperarán a través de los setters y getters anteriores
# o un objeto de estado de la aplicación.
