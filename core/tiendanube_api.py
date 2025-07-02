import requests
import json
import time
from functools import wraps
import os
import base64
import logging
from typing import List, Dict, Any, Optional

from tqdm import tqdm
from colorama import Fore, Style

# Importaciones de la nueva estructura
from config import settings, credentials
# La importación de app.deepseek se reemplazará por una función o clase de un nuevo módulo, ej: core.ai_services
# Por ahora, vamos a asumir que existe una función placeholder o que se integrará luego.
# from app.deepseek import obtener_dimensiones_producto
def obtener_dimensiones_producto_placeholder(producto_lista, categorias, path):
    # Placeholder - esta función deberá ser implementada o importada correctamente
    logger.warning("Usando placeholder para obtener_dimensiones_producto.")
    return [{'peso_kg': 0.05, 'ancho_cm': 5.0, 'alto_cm': 5.0, 'profundidad_cm': 5.0}]


logger = logging.getLogger(__name__)

# --- Variables Globales y Configuración ---
TIENDANUBE_CREDS = credentials.get_tiendanube_credentials()
ACCESS_TOKEN = TIENDANUBE_CREDS['access_token']
STORE_ID = TIENDANUBE_CREDS['store_id']

if not ACCESS_TOKEN or not STORE_ID:
    logger.critical("Las credenciales de Tiendanube (ACCESS_TOKEN, STORE_ID) no están configuradas. La API no funcionará.")
    # Podríamos lanzar una excepción aquí para detener la ejecución si son críticas.
    # raise ValueError("Credenciales de Tiendanube no configuradas.")

BASE_URL = settings.TIENDANUBE_BASE_URL_TEMPLATE.format(store_id=STORE_ID)

DEFAULT_HEADERS = {
    "Authentication": f"bearer {ACCESS_TOKEN}",
    "Content-Type": "application/json",
    "User-Agent": settings.USER_AGENT_TIENDANUBE
}

# --- Caché ---
# Diccionarios para almacenar la caché en memoria
cache_categorias_mem = {}
cache_variante_mem = {}
cache_ids_categorias_mem = {}
products_cache_mem = {} # Para la caché de productos por página

# Configuración de caché en disco
PRODUCTS_CACHE_FILE = settings.PRODUCTS_CACHE_FILE # Ya incluye API_CACHE_DIR

# Cargar caché de productos desde disco
try:
    if os.path.exists(PRODUCTS_CACHE_FILE):
        with open(PRODUCTS_CACHE_FILE, 'r') as f:
            products_cache_mem = json.load(f)
    else:
        products_cache_mem = {}
except (FileNotFoundError, json.JSONDecodeError) as e:
    logger.warning(f"No se pudo cargar la caché de productos desde {PRODUCTS_CACHE_FILE}: {e}")
    products_cache_mem = {}

def save_products_cache_to_disk():
    """Guarda la caché de productos en disco."""
    try:
        os.makedirs(settings.API_CACHE_DIR, exist_ok=True)
        with open(PRODUCTS_CACHE_FILE, 'w') as f:
            json.dump(products_cache_mem, f, indent=2)
        logger.info(f"Caché de productos guardada en {PRODUCTS_CACHE_FILE}")
    except Exception as e:
        logger.error(f"Error guardando caché de productos en disco: {e}", exc_info=True)

# --- Decorador para Rate Limiting ---
def manejar_rate_limiting(func):
    """Decorador para manejar rate limiting de la API."""
    last_request_time = 0
    requests_count = 0

    @wraps(func)
    def wrapper(*args, **kwargs):
        nonlocal last_request_time, requests_count

        current_time = time.time()

        if current_time - last_request_time > settings.RATE_LIMIT_WINDOW:
            requests_count = 0

        if requests_count >= settings.MAX_REQUESTS_PER_WINDOW:
            wait_time = settings.RATE_LIMIT_WINDOW - (current_time - last_request_time)
            if wait_time > 0:
                logger.info(f"Esperando {wait_time:.1f}s para respetar límites de API...")
                time.sleep(wait_time)
                requests_count = 0
                last_request_time = time.time() # Actualizar tiempo después de la espera larga

        time_since_last = time.time() - last_request_time # Re-evaluar después de posible espera larga
        if time_since_last < settings.MIN_DELAY_BETWEEN_REQUESTS:
            sleep_duration = settings.MIN_DELAY_BETWEEN_REQUESTS - time_since_last
            # logger.debug(f"Delaying for {sleep_duration:.2f}s") # Puede ser muy verboso
            time.sleep(sleep_duration)

        max_retries = 3
        retry_delay = 5 # segundos

        for attempt in range(max_retries):
            try:
                result = func(*args, **kwargs)
                last_request_time = time.time()
                requests_count += 1
                return result
            except requests.exceptions.RequestException as e:
                if hasattr(e.response, 'status_code') and e.response.status_code == 429: # Too Many Requests
                    current_retry_delay = retry_delay * (2 ** attempt)
                    logger.warning(f"Rate limit alcanzado (intento {attempt + 1}/{max_retries}). Esperando {current_retry_delay}s... ({func.__name__})")
                    time.sleep(current_retry_delay)
                    last_request_time = time.time() # Resetear el tiempo para no encadenar esperas de rate limit con el delay normal
                    requests_count = 0 # Resetear contador también
                    continue
                logger.error(f"Error de red en {func.__name__} (intento {attempt + 1}): {e}", exc_info=True)
                if attempt == max_retries - 1: # Si es el último reintento, relanzar
                    raise
                time.sleep(retry_delay) # Espera antes de reintentar por otros errores de red

        logger.error(f"Máximo de reintentos alcanzado para {func.__name__}")
        return None # O relanzar una excepción específica

    return wrapper

# --- Funciones de Imágenes ---
def _subir_imagen_local_codificada(ruta_imagen_local_abs: str) -> Optional[Dict[str, str]]:
    """
    Lee una imagen local, la codifica en base64 y prepara la estructura para la API.
    """
    try:
        if not os.path.isfile(ruta_imagen_local_abs):
            logger.error(f"Archivo de imagen no encontrado: {ruta_imagen_local_abs}")
            return None

        extension = os.path.splitext(ruta_imagen_local_abs)[1][1:].lower()
        if extension not in ['jpg', 'jpeg', 'png', 'gif', 'webp']:
            logger.warning(f"Formato de imagen no soportado: {extension} para {ruta_imagen_local_abs}")
            return None

        with open(ruta_imagen_local_abs, "rb") as img_file:
            encoded_str = base64.b64encode(img_file.read()).decode('utf-8')

        return {
            "attachment": encoded_str,
            "filename": os.path.basename(ruta_imagen_local_abs),
            "content_type": f"image/{extension}" if extension != 'jpg' else "image/jpeg"
        }
    except PermissionError:
        logger.error(f"Permiso denegado al leer la imagen: {ruta_imagen_local_abs}", exc_info=True)
    except Exception as e:
        logger.error(f"Error procesando imagen local {ruta_imagen_local_abs}: {e}", exc_info=True)
    return None

def _manejar_imagenes_payload(producto_info: Dict[str, Any], descargar_imagenes: bool) -> List[Dict[str, str]]:
    """
    Prepara el payload de imágenes para la API de Tiendanube.
    Utiliza la ruta absoluta para imágenes locales.
    """
    imagenes_payload = []
    if descargar_imagenes:
        if producto_info.get('imagen_local'): # imagen_local debe ser ruta absoluta o relativa a settings.IMG_SCRAPING_DIR
            ruta_abs_imagen = producto_info['imagen_local']
            if not os.path.isabs(ruta_abs_imagen): # Asumir relativa a IMG_SCRAPING_DIR
                # Esto asume que 'imagen_local' es solo el nombre del archivo, ej: "nombre.jpg"
                # y que está en settings.IMG_SCRAPING_DIR
                ruta_abs_imagen = os.path.join(settings.IMG_SCRAPING_DIR, os.path.basename(producto_info['imagen_local']))


            logger.debug(f"Procesando imagen local: {ruta_abs_imagen}")
            imagen_data = _subir_imagen_local_codificada(ruta_abs_imagen)
            if imagen_data:
                imagenes_payload.append(imagen_data)
            else:
                logger.warning(f"No se pudo procesar la imagen local: {producto_info.get('imagen_local')} en ruta {ruta_abs_imagen}")
                # Fallback a URL si la imagen local falla y la URL existe? Podría ser una opción.
                if producto_info.get('imagen_url'):
                    logger.info(f"Usando imagen_url como fallback para {producto_info.get('codigo')}")
                    imagenes_payload.append({"src": producto_info['imagen_url']})

        elif producto_info.get('imagen_url'): # Si no hay local pero sí URL, y se quieren descargar (esto es raro)
            logger.warning(f"Descarga de imágenes habilitada pero solo se encontró imagen_url para {producto_info.get('codigo')}. Usando URL.")
            imagenes_payload.append({"src": producto_info['imagen_url']})
    else: # No descargar, usar URL
        if producto_info.get('imagen_url'):
            imagenes_payload.append({"src": producto_info['imagen_url']})
        elif producto_info.get('imagen_local'): # Si no hay URL pero sí local (y no se quieren descargar)
             logger.warning(f"Descarga de imágenes deshabilitada, pero solo se encontró imagen_local para {producto_info.get('codigo')}. No se subirá imagen.")


    if not imagenes_payload:
        logger.debug(f"No se prepararon imágenes para el producto {producto_info.get('codigo')}")
    return imagenes_payload

# --- Funciones de Categorías ---
@manejar_rate_limiting
def _obtener_todas_categorias_api() -> List[Dict[str, Any]]:
    """Obtiene todas las categorías de la tienda directamente desde la API."""
    categorias_api = []
    page = 1
    per_page = 200

    while True:
        url = f"{BASE_URL}/categories?page={page}&per_page={per_page}&fields=id,name,parent"
        response = requests.get(url, headers=DEFAULT_HEADERS)
        response.raise_for_status() # Levanta HTTPError para 4xx/5xx

        categorias_pagina = response.json()
        if not categorias_pagina:
            break

        for cat_api in categorias_pagina:
            nombre_es = cat_api.get('name', {}).get('es')
            nombre_pt = cat_api.get('name', {}).get('pt')
            nombre = nombre_es if nombre_es else (nombre_pt if nombre_pt else "Categoría sin nombre")

            parent_data = cat_api.get('parent')
            parent_id = None
            if isinstance(parent_data, dict): # Formato esperado {id: value, name: {es: value}}
                parent_id = parent_data.get('id')
            elif isinstance(parent_data, (int, str)): # A veces la API devuelve solo el ID
                parent_id = int(parent_data)


            categorias_api.append({
                "id": cat_api['id'],
                "nombre": nombre, # Usar el nombre en español o el primero disponible
                "parent_id": parent_id
            })

        if len(categorias_pagina) < per_page:
            break
        page += 1

    return categorias_api

def obtener_categorias_tienda() -> List[Dict[str, Any]]:
    """Obtiene todas las categorías, usando caché en memoria."""
    if 'lista_completa' not in cache_categorias_mem:
        logger.info("Actualizando caché de categorías desde la API...")
        cache_categorias_mem['lista_completa'] = _obtener_todas_categorias_api()
        logger.info(f"Caché de categorías actualizada con {len(cache_categorias_mem['lista_completa'])} categorías.")
    return cache_categorias_mem['lista_completa']

def _buscar_id_categoria_en_cache(nombre_buscado: str, parent_id_buscado: Optional[int] = None) -> Optional[int]:
    """Busca una categoría en la caché por nombre y opcionalmente parent_id."""
    nombre_buscado_lower = nombre_buscado.strip().lower()
    categorias_cached = obtener_categorias_tienda() # Asegura que la caché esté poblada

    for cat in categorias_cached:
        if cat['nombre'].strip().lower() == nombre_buscado_lower:
            # Si parent_id_buscado es None, coincide si la categoría no tiene padre.
            # Si parent_id_buscado tiene valor, coincide si el padre de la categoría es ese valor.
            if parent_id_buscado is None and cat.get('parent_id') is None:
                return cat['id']
            elif parent_id_buscado is not None and cat.get('parent_id') == parent_id_buscado:
                return cat['id']
            elif parent_id_buscado is not None and cat.get('parent_id') is None : # Si busco con padre pero la cat no tiene, no es match
                 pass
            elif parent_id_buscado is None and cat.get('parent_id') is not None: # Si busco sin padre pero la cat sí tiene, no es match
                 pass


    return None

@manejar_rate_limiting
def crear_categoria_api(nombre: str, parent_id: Optional[int] = None) -> Optional[int]:
    """Crea una nueva categoría en Tiendanube."""
    nombre_limpio = nombre.strip()
    if not nombre_limpio:
        logger.error("El nombre de la categoría no puede estar vacío.")
        return None

    # Verificar si ya existe con ese nombre y padre (para evitar duplicados innecesarios)
    id_existente = _buscar_id_categoria_en_cache(nombre_limpio, parent_id)
    if id_existente:
        logger.info(f"La categoría '{nombre_limpio}' con parent_id '{parent_id}' ya existe (ID: {id_existente}). No se creará una nueva.")
        return id_existente

    payload = {"name": {"es": nombre_limpio}}
    if parent_id:
        payload["parent"] = parent_id

    logger.info(f"Creando categoría: '{nombre_limpio}' (Parent ID: {parent_id})")
    response = requests.post(f"{BASE_URL}/categories", headers=DEFAULT_HEADERS, json=payload)

    if response.status_code in [200, 201]: # 200 OK (si ya existía y la API la devuelve), 201 Created
        response_data = response.json()
        categoria_id = response_data.get('id')
        if categoria_id:
            logger.info(f"Categoría '{nombre_limpio}' creada/confirmada con ID: {categoria_id}")
            # Invalidar y recargar caché de categorías después de una creación exitosa
            if 'lista_completa' in cache_categorias_mem:
                del cache_categorias_mem['lista_completa']
            obtener_categorias_tienda() # Recargar
            return categoria_id
        else:
            logger.error(f"Respuesta API inesperada al crear categoría '{nombre_limpio}': {response_data}")
            return None
    else:
        logger.error(f"Error al crear categoría '{nombre_limpio}' (HTTP {response.status_code}): {response.text}")
        return None

def _obtener_ids_categorias_para_producto(producto_data: Dict[str, Any]) -> List[int]:
    """
    Obtiene o crea los IDs de las categorías para un producto.
    Maneja categoría principal y subcategoría.
    """
    ids_cat = []
    cat_principal_nombre = producto_data.get('categoria', '').strip()
    sub_cat_nombre = producto_data.get('subcategoria', '').strip()

    current_parent_id = None

    if cat_principal_nombre:
        cat_id = _buscar_id_categoria_en_cache(cat_principal_nombre, None)
        if not cat_id:
            cat_id = crear_categoria_api(cat_principal_nombre, None)

        if cat_id:
            ids_cat.append(cat_id)
            current_parent_id = cat_id
        else:
            logger.warning(f"No se pudo obtener/crear ID para la categoría principal: {cat_principal_nombre}")
            return [] # Si la principal falla, no continuar

    if sub_cat_nombre and current_parent_id: # Solo procesar subcategoría si hay una principal válida
        sub_cat_id = _buscar_id_categoria_en_cache(sub_cat_nombre, current_parent_id)
        if not sub_cat_id:
            sub_cat_id = crear_categoria_api(sub_cat_nombre, current_parent_id)

        if sub_cat_id:
            ids_cat.append(sub_cat_id)
        else:
            logger.warning(f"No se pudo obtener/crear ID para la subcategoría: {sub_cat_nombre} (parent: {current_parent_id})")
            # No necesariamente fallar todo si la subcategoría falla, al menos la principal está.

    return ids_cat

# --- Funciones de Producto ---
@manejar_rate_limiting
def buscar_producto_por_sku(sku: str) -> Optional[int]:
    """Busca un producto por SKU, usando caché en disco y memoria."""
    logger.debug(f"Buscando producto por SKU: {sku}")
    page = 1
    per_page = 200

    for _, product_list_cached in products_cache_mem.items():
        for prod_cached in product_list_cached:
            for variant_cached in prod_cached.get('variants', []):
                if variant_cached.get('sku') == sku:
                    logger.info(f"SKU {sku} encontrado en caché en memoria (Producto ID: {prod_cached['id']})")
                    return prod_cached["id"]

    logger.info(f"SKU {sku} no encontrado en caché inicial, consultando API y construyendo caché...")

    try:
        response_count = requests.get(f"{BASE_URL}/products", headers=DEFAULT_HEADERS, params={'page': 1, 'per_page': 1, 'fields': 'id'})
        response_count.raise_for_status()
        total_products_api = int(response_count.headers.get('X-Total-Count', 0))
        total_pages = (total_products_api + per_page - 1) // per_page if total_products_api > 0 else 0
    except requests.RequestException as e:
        logger.error(f"Error obteniendo el total de productos para la barra de progreso: {e}")
        total_pages = 5

    if total_pages == 0 and total_products_api > 0 : total_pages = 1

    pbar = None
    if total_pages > 0:
         pbar = tqdm(total=total_pages, desc="Consultando API Productos", unit="página", leave=False)

    newly_fetched_pages = 0
    try:
        while True:
            cache_page_key = f"products_page_{page}"
            if cache_page_key in products_cache_mem:
                productos_pagina = products_cache_mem[cache_page_key]
                logger.debug(f"Página {page} de productos cargada desde caché en memoria.")
            else:
                params = {'page': page, 'per_page': per_page, 'fields': 'id,name,variants'}
                response = requests.get(f"{BASE_URL}/products", headers=DEFAULT_HEADERS, params=params)
                response.raise_for_status()
                productos_pagina = response.json()

                products_cache_mem[cache_page_key] = productos_pagina
                newly_fetched_pages +=1
                logger.debug(f"Página {page} de productos obtenida de API y guardada en caché.")

            if pbar: pbar.update(1)

            for producto_api in productos_pagina:
                for variante_api in producto_api.get('variants', []):
                    if variante_api.get('sku') == sku:
                        logger.info(f"SKU {sku} encontrado en API (Producto ID: {producto_api['id']}) en página {page}")
                        if pbar: pbar.close()
                        if newly_fetched_pages > 0 : save_products_cache_to_disk()
                        return producto_api["id"]

            if not productos_pagina or len(productos_pagina) < per_page:
                logger.debug(f"Fin de la paginación de productos en la página {page}.")
                break
            page += 1
            if page > total_pages and total_pages > 0 :
                logger.warning(f"Se alcanzó el número estimado de páginas ({total_pages}), deteniendo búsqueda de SKU {sku}.")
                break

    except requests.RequestException as e:
        logger.error(f"Error durante la búsqueda de producto por SKU ({sku}): {e}", exc_info=True)
    finally:
        if pbar: pbar.close()
        if newly_fetched_pages > 0 : save_products_cache_to_disk()

    logger.info(f"SKU {sku} no encontrado en Tiendanube.")
    return None

@manejar_rate_limiting
def _obtener_id_variante_api(producto_id_tiendanube: int) -> Optional[int]:
    """Obtiene el ID de la primera variante de un producto desde la API."""
    if producto_id_tiendanube in cache_variante_mem:
        return cache_variante_mem[producto_id_tiendanube]

    try:
        logger.debug(f"Consultando API para ID de variante del producto {producto_id_tiendanube}")
        response = requests.get(f"{BASE_URL}/products/{producto_id_tiendanube}/variants?fields=id,sku", headers=DEFAULT_HEADERS)
        response.raise_for_status()
        variants_api = response.json()
        if variants_api:
            variante_id = variants_api[0]['id']
            cache_variante_mem[producto_id_tiendanube] = variante_id
            return variante_id
        else:
            logger.warning(f"El producto {producto_id_tiendanube} no tiene variantes según la API.")
            return None
    except requests.RequestException as e:
        logger.error(f"Error obteniendo ID de variante para producto {producto_id_tiendanube}: {e}", exc_info=True)
        return None


@manejar_rate_limiting
def crear_producto_tiendanube(producto_data: Dict[str, Any], ganancia_porcentaje: float, descargar_imagenes: bool) -> Optional[int]:
    """
    Crea un nuevo producto en Tiendanube.
    """
    logger.info(f"Intentando crear producto con SKU: {producto_data.get('codigo')}")
    try:
        precio_str = str(producto_data.get('precio', '0')).replace('$', '').replace('.', '').replace(',', '.')
        precio_base = float(precio_str)
        precio_final = round(precio_base * (1 + ganancia_porcentaje / 100), 2)

        categorias_str = f"{producto_data.get('categoria', '')}, {producto_data.get('subcategoria', '')}"
        dimensiones_info = obtener_dimensiones_producto_placeholder(
            [{'descripcion': producto_data.get('descripcion'), 'codigo': producto_data.get('codigo')}],
            categorias_str,
            settings.DB_PATH
        )

        dim = dimensiones_info[0] if dimensiones_info else \
              {'peso_kg': 0.05, 'ancho_cm': 5.0, 'alto_cm': 5.0, 'profundidad_cm': 5.0}

        payload = {
            "name": producto_data.get('descripcion', 'Producto sin descripción'),
            "variants": [{
                "price": str(precio_final),
                "stock_management": True,
                "stock": producto_data.get('stock', 0),
                "sku": producto_data.get('codigo'),
                "barcode": producto_data.get('codigo_de_barras'),
                "weight": str(dim.get('peso_kg', 0.05)),
                "width": str(dim.get('ancho_cm', 5.0)),
                "height": str(dim.get('alto_cm', 5.0)),
                "depth": str(dim.get('profundidad_cm', 5.0))
            }],
            "published": True,
            "images": _manejar_imagenes_payload(producto_data, descargar_imagenes),
            "categories": _obtener_ids_categorias_para_producto(producto_data)
        }

        payload['variants'][0] = {k: v for k, v in payload['variants'][0].items() if v is not None}

        logger.debug(f"Payload para crear producto ({producto_data.get('codigo')}): {json.dumps(payload, indent=2)}")
        response = requests.post(f"{BASE_URL}/products", headers=DEFAULT_HEADERS, json=payload)

        if response.status_code == 201:
            producto_creado_id = response.json().get('id')
            logger.info(f"Producto {producto_data.get('codigo')} creado exitosamente con ID: {producto_creado_id}")
            products_cache_mem.clear()
            save_products_cache_to_disk()
            return producto_creado_id
        else:
            logger.error(f"Error al crear producto {producto_data.get('codigo')} (HTTP {response.status_code}): {response.text}")
            return None

    except Exception as e:
        logger.error(f"Excepción al crear producto {producto_data.get('codigo')}: {e}", exc_info=True)
        return None

@manejar_rate_limiting
def actualizar_producto_tiendanube(id_tiendanube: int, producto_data: Dict[str, Any], ganancia_porcentaje: float, descargar_imagenes: bool) -> bool:
    """
    Actualiza un producto existente en Tiendanube.
    """
    logger.info(f"Intentando actualizar producto ID: {id_tiendanube} con SKU: {producto_data.get('codigo')}")
    try:
        precio_str = str(producto_data.get('precio', '0')).replace('$', '').replace('.', '').replace(',', '.')
        precio_base = float(precio_str)
        precio_final = round(precio_base * (1 + ganancia_porcentaje / 100), 2)

        payload_producto = {
            "name": producto_data.get('descripcion', 'Producto sin descripción'),
            "categories": _obtener_ids_categorias_para_producto(producto_data),
        }
        payload_producto = {k:v for k,v in payload_producto.items() if v is not None and (isinstance(v, list) and len(v) > 0 or not isinstance(v, list))}

        if payload_producto:
            logger.debug(f"Payload para actualizar producto base ({id_tiendanube}): {json.dumps(payload_producto, indent=2)}")
            response_prod = requests.put(f"{BASE_URL}/products/{id_tiendanube}", headers=DEFAULT_HEADERS, json=payload_producto)
            if response_prod.status_code != 200:
                logger.error(f"Error al actualizar datos base del producto {id_tiendanube} (HTTP {response_prod.status_code}): {response_prod.text}")
                return False
        else:
            logger.info(f"No hay datos base para actualizar en el producto {id_tiendanube}.")

        nuevas_imagenes = _manejar_imagenes_payload(producto_data, descargar_imagenes)
        if nuevas_imagenes:
            logger.info(f"Intentando actualizar/añadir imágenes para el producto {id_tiendanube}.")
            # Primero obtener imágenes existentes para no duplicar por URL si es la misma
            try:
                resp_get_images = requests.get(f"{BASE_URL}/products/{id_tiendanube}/images?fields=id,src", headers=DEFAULT_HEADERS)
                existing_images_api = resp_get_images.json() if resp_get_images.status_code == 200 else []
            except Exception:
                existing_images_api = []

            existing_srcs = {img.get('src') for img in existing_images_api if img.get('src')}

            for img_payload in nuevas_imagenes:
                # Si la imagen es por URL y ya existe una imagen con esa URL, no la subimos de nuevo.
                if "src" in img_payload and img_payload["src"] in existing_srcs:
                    logger.info(f"Imagen {img_payload['src']} ya existe para producto {id_tiendanube}, no se vuelve a añadir.")
                    continue

                img_post_url = f"{BASE_URL}/products/{id_tiendanube}/images"
                response_img = requests.post(img_post_url, headers=DEFAULT_HEADERS, json=img_payload)
                if response_img.status_code not in [200, 201]:
                    logger.warning(f"No se pudo añadir/actualizar imagen para producto {id_tiendanube} (HTTP {response_img.status_code}): {response_img.text}. Payload: {img_payload.get('filename', img_payload.get('src'))}")
                else:
                    logger.info(f"Imagen {img_payload.get('filename', img_payload.get('src'))} añadida/actualizada para producto {id_tiendanube}.")


        variante_id_tiendanube = _obtener_id_variante_api(id_tiendanube)
        if variante_id_tiendanube:
            categorias_str = f"{producto_data.get('categoria', '')}, {producto_data.get('subcategoria', '')}"
            dimensiones_info = obtener_dimensiones_producto_placeholder(
                 [{'descripcion': producto_data.get('descripcion'), 'codigo': producto_data.get('codigo')}],
                 categorias_str, settings.DB_PATH
            )
            dim = dimensiones_info[0] if dimensiones_info else \
                  {'peso_kg': 0.05, 'ancho_cm': 5.0, 'alto_cm': 5.0, 'profundidad_cm': 5.0}

            payload_variante = {
                "price": str(precio_final),
                "stock_management": True,
                "stock": producto_data.get('stock', 0),
                "sku": producto_data.get('codigo'),
                "barcode": producto_data.get('codigo_de_barras'),
                "weight": str(dim.get('peso_kg', 0.05)),
                "width": str(dim.get('ancho_cm', 5.0)),
                "height": str(dim.get('alto_cm', 5.0)),
                "depth": str(dim.get('profundidad_cm', 5.0))
            }
            payload_variante = {k: v for k, v in payload_variante.items() if v is not None}

            logger.debug(f"Payload para actualizar variante ({variante_id_tiendanube}) del producto {id_tiendanube}: {json.dumps(payload_variante, indent=2)}")
            response_var = requests.put(f"{BASE_URL}/products/{id_tiendanube}/variants/{variante_id_tiendanube}", headers=DEFAULT_HEADERS, json=payload_variante)
            if response_var.status_code != 200:
                logger.error(f"Error al actualizar variante {variante_id_tiendanube} del producto {id_tiendanube} (HTTP {response_var.status_code}): {response_var.text}")
                return False
        else:
            logger.warning(f"No se encontró ID de variante para el producto {id_tiendanube}. No se actualizó la variante.")

        logger.info(f"Producto ID {id_tiendanube} (SKU: {producto_data.get('codigo')}) actualizado correctamente.")
        products_cache_mem.clear()
        save_products_cache_to_disk()
        return True

    except Exception as e:
        logger.error(f"Excepción al actualizar producto {id_tiendanube}: {e}", exc_info=True)
        return False

def limpiar_cache_productos_tiendanube():
    """Limpia la caché de productos de Tiendanube (memoria y disco)."""
    global products_cache_mem
    products_cache_mem.clear()
    try:
        if os.path.exists(PRODUCTS_CACHE_FILE):
            os.remove(PRODUCTS_CACHE_FILE)
        logger.info("Caché de productos de Tiendanube eliminada (memoria y disco).")
    except Exception as e:
        logger.error(f"Error eliminando archivo de caché de productos ({PRODUCTS_CACHE_FILE}): {e}", exc_info=True)

@manejar_rate_limiting
def actualizar_stock_variante(id_producto_tiendanube: int, id_variante_tiendanube: int, nuevo_stock: Optional[int]) -> bool:
    """
    Actualiza el stock de una variante específica.
    """
    payload = {}
    if nuevo_stock is None: # Stock ilimitado
        payload["stock_management"] = False
        payload["stock"] = None
    else: # Stock gestionado
        payload["stock_management"] = True
        payload["stock"] = int(nuevo_stock)

    logger.info(f"Actualizando stock para producto {id_producto_tiendanube}, variante {id_variante_tiendanube}: Nuevo stock {'Ilimitado' if nuevo_stock is None else nuevo_stock}")

    url = f"{BASE_URL}/products/{id_producto_tiendanube}/variants/{id_variante_tiendanube}"
    try:
        response = requests.put(url, headers=DEFAULT_HEADERS, json=payload)
        response.raise_for_status()
        logger.info(f"Stock actualizado correctamente para variante {id_variante_tiendanube}.")
        # Actualizar caché de producto si es necesario, aunque el stock no suele estar en la caché de búsqueda general.
        # Podríamos invalidar la página específica del producto si la tuviéramos.
        return True
    except requests.exceptions.HTTPError as e:
        logger.error(f"Error API (HTTP {e.response.status_code}) al actualizar stock de variante {id_variante_tiendanube}: {e.response.text}")
        return False
    except requests.exceptions.RequestException as e:
        logger.error(f"Error de red al actualizar stock de variante {id_variante_tiendanube}: {e}")
        return False


if __name__ == '__main__':
    # Este bloque es para pruebas si ejecutas: python -m core.tiendanube_api
    # Asegúrate que config/logging_config.py y config/settings.py estén correctos.
    # Y que .env exista en la raíz con las credenciales si no usas los fallbacks.

    # Para que el logger funcione correctamente desde aquí:
    if not logging.getLogger().hasHandlers(): # Evitar múltiples handlers si se importa en otro lado
        from config.logging_config import setup_logging
        setup_logging() # Configura el logging como se definió

    logger.info("Probando módulo Tiendanube API...")

    if not ACCESS_TOKEN or not STORE_ID or ACCESS_TOKEN == 'cdcad052f53bae4972979dbf6900925d4e9a36dc': # Chequea el fallback
        logger.error("Por favor, configura TIENDANUBE_ACCESS_TOKEN y TIENDANUBE_STORE_ID en .env para probar.")
    else:
        logger.info(f"Usando STORE_ID: {STORE_ID} y ACCESS_TOKEN: ...{ACCESS_TOKEN[-4:]}")

        # Test 1: Limpiar y obtener categorías
        # limpiar_cache_productos_tiendanube() # Opcional, para forzar recarga de productos
        # if 'lista_completa' in cache_categorias_mem: del cache_categorias_mem['lista_completa'] # Limpiar caché de categorías

        # all_cats = obtener_categorias_tienda()
        # logger.info(f"Total de categorías obtenidas: {len(all_cats)}")
        # if all_cats: logger.info(f"Ejemplo de categoría: {all_cats[0]['nombre']} (ID: {all_cats[0]['id']})")

        # Test 2: Crear/Obtener categoría de prueba
        # cat_name_test = "Super Test Jules"
        # subcat_name_test = "Sub Super Test Jules"
        # id_cat_test = crear_categoria_api(cat_name_test)
        # id_subcat_test = None
        # if id_cat_test:
        #    id_subcat_test = crear_categoria_api(subcat_name_test, id_cat_test)
        #    logger.info(f"Categoría '{cat_name_test}' ID: {id_cat_test}, Subcategoría '{subcat_name_test}' ID: {id_subcat_test}")
        # else:
        #    logger.error(f"No se pudo crear/obtener la categoría de prueba '{cat_name_test}'")

        # Test 3: Buscar un producto por SKU (reemplaza con un SKU real o uno para crear)
        # sku_test = "JULES-TEST-PRODUCT-005"
        # product_id = buscar_producto_por_sku(sku_test)

        # if product_id:
        #     logger.info(f"Producto SKU '{sku_test}' encontrado. ID Tiendanube: {product_id}")
            # Test 3.1: Actualizar producto encontrado
            # product_update_data = {
            #     'codigo': sku_test,
            #     'descripcion': f"Producto Test Jules Actualizado ({time.strftime('%H:%M')})",
            #     'precio': "150.75", # Precio base
            #     'categoria': cat_name_test,
            #     'subcategoria': subcat_name_test,
            #     'codigo_de_barras': "0001112223339",
            #     'imagen_url': "https://picsum.photos/id/237/200/300", # Nueva imagen URL
            #     # 'imagen_local': "nombre_de_tu_imagen.jpg", # Si tienes una en data/img-scraping/
            #     'stock': 22
            # }
            # success_update = actualizar_producto_tiendanube(product_id, product_update_data, 30, False) # 30% ganancia, no descargar
            # logger.info(f"Resultado de actualización para SKU '{sku_test}': {success_update}")

            # Test 3.2: Actualizar stock del producto encontrado
            # variant_id = _obtener_id_variante_api(product_id)
            # if variant_id:
            #     logger.info(f"Actualizando stock para producto {product_id}, variante {variant_id}")
            #     actualizar_stock_variante(product_id, variant_id, 30) # Stock = 30
            #     time.sleep(settings.MIN_DELAY_BETWEEN_REQUESTS + 0.5) # Pausa
            #     actualizar_stock_variante(product_id, variant_id, None) # Stock ilimitado
            # else:
            #     logger.warning(f"No se pudo obtener ID de variante para {product_id} para probar stock.")

        # else:
        #     logger.info(f"Producto SKU '{sku_test}' NO encontrado. Intentando crear...")
            # Test 3.3: Crear el producto si no existe
            # product_create_data = {
            #     'codigo': sku_test,
            #     'descripcion': "Producto Test Jules Creado",
            #     'precio': "120.00", # Precio base
            #     'categoria': cat_name_test,
            #     'subcategoria': subcat_name_test,
            #     'codigo_de_barras': "9998887776661",
            #     'imagen_url': "https://picsum.photos/200",
            #     # 'imagen_local': "nombre_de_tu_imagen.jpg", # Si la tienes en data/img-scraping/
            #     'stock': 5
            # }
            # new_product_id = crear_producto_tiendanube(product_create_data, 40, False) # 40% ganancia, no descargar
            # if new_product_id:
            #     logger.info(f"Producto SKU '{sku_test}' creado con ID Tiendanube: {new_product_id}")
            # else:
            #     logger.error(f"Fallo al crear producto SKU '{sku_test}'")

        logger.info("Pruebas de Tiendanube API finalizadas.")
