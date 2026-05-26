from config import TIENDANUBE_STORE_ID, TIENDANUBE_ACCESS_TOKEN, TIENDANUBE_USER_AGENT
from app.services.tiendanube import TiendanubeClient

# Instancia centralizada del cliente Tiendanube
client = TiendanubeClient(
    store_id=TIENDANUBE_STORE_ID,
    access_token=TIENDANUBE_ACCESS_TOKEN,
    user_agent=TIENDANUBE_USER_AGENT
)

# Exportamos las funciones de la API delegándolas al cliente (retrocompatibilidad)
def limpiar_cache_productos():
    return client.limpiar_cache_productos()

def buscar_id_categoria(nombre, parent_id=None):
    return client.buscar_id_categoria(nombre, parent_id)

def crear_categoria(nombre, parent_id=None):
    return client.crear_categoria(nombre, parent_id)

def obtener_categorias_tienda():
    return client.obtener_categorias_tienda()

def obtener_ids_categorias(producto):
    return client.obtener_ids_categorias(producto)

def buscar_producto_por_sku(sku):
    return client.buscar_producto_por_sku(sku)

def obtener_id_variante(producto_id):
    return client.obtener_id_variante(producto_id)

def agregar_imagen(producto_id, imagen_url):
    return client.agregar_imagen(producto_id, imagen_url)

def crear_producto(producto, PATH, GANANCIA_PORCENTAJE, DOWNLOAD_IMAGES):
    return client.crear_producto(producto, PATH, GANANCIA_PORCENTAJE, DOWNLOAD_IMAGES)

def actualizar_producto(producto_id, producto, ganancia_porcentaje, DOWNLOAD_IMAGES):
    return client.actualizar_producto(producto_id, producto, ganancia_porcentaje, DOWNLOAD_IMAGES)
