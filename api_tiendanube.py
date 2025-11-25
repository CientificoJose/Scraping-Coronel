from colorama import Fore, Style
import requests
import json
import json
from typing import List
import time
from functools import wraps
import os
import json
from tqdm import tqdm
import base64
from app.deepseek import obtener_dimensiones_producto
from config import DOWNLOAD_IMAGES

# Variables necesarias
ACCESS_TOKEN = "cdcad052f53bae4972979dbf6900925d4e9a36dc"  # Tu token de acceso obtenido
STORE_ID = "5950659"  # El ID de tu tienda (por ejemplo, 5950659)
BASE_URL = f"https://api.tiendanube.com/v1/{STORE_ID}"

headers = {
        "Authentication": f"bearer {ACCESS_TOKEN}",
        "Content-Type": "application/json",
        "User-Agent": "API-KEY (jgstore244@gmail.com)"

    }


# Diccionarios para almacenar la caché
cache_categorias = {}
cache_variante = {}
cache_ids_categorias = {}
cache_productos = {}

# Configuración de caché
CACHE_DIR = os.path.join(os.path.dirname(__file__), 'api_cache')
PRODUCTS_CACHE = os.path.join(CACHE_DIR, 'products_cache.json')
os.makedirs(CACHE_DIR, exist_ok=True)

# Cargar caché existente
try:
    with open(PRODUCTS_CACHE, 'r') as f:
        products_cache = json.load(f)
except (FileNotFoundError, json.JSONDecodeError):
    products_cache = {}

def save_cache():
    """Guarda la caché en disco"""
    try:
        with open(PRODUCTS_CACHE, 'w') as f:
            json.dump(products_cache, f, indent=2)
    except Exception as e:
        print(Fore.YELLOW + f"Error guardando caché: {e}" + Style.RESET_ALL)

def manejar_rate_limiting(func):
    """Decorador para manejar rate limiting de la API con sistema de cola y conteo"""
    
    # Variables de control para rate limiting
    last_request_time = 0
    requests_count = 0
    RATE_LIMIT_WINDOW = 60  # 60 segundos
    MAX_REQUESTS = 50  # máximo de peticiones por minuto
    MIN_DELAY = 1.2  # delay mínimo entre peticiones
    
    @wraps(func)
    def wrapper(*args, **kwargs):
        nonlocal last_request_time, requests_count
        
        current_time = time.time()
        
        # Reset contador si ha pasado la ventana de tiempo
        if current_time - last_request_time > RATE_LIMIT_WINDOW:
            requests_count = 0
        
        # Si estamos cerca del límite, forzar espera
        if requests_count >= MAX_REQUESTS:
            wait_time = RATE_LIMIT_WINDOW - (current_time - last_request_time)
            if wait_time > 0:
                print(Fore.YELLOW + f"\n⏳ Esperando {wait_time:.1f}s para respetar límites de API..." + Style.RESET_ALL)
                time.sleep(wait_time)
                requests_count = 0
        
        # Asegurar delay mínimo entre peticiones
        time_since_last = current_time - last_request_time
        if time_since_last < MIN_DELAY:
            time.sleep(MIN_DELAY - time_since_last)
        
        # Intentar petición con reintentos
        max_retries = 3
        retry_delay = 5
        
        for attempt in range(max_retries):
            try:
                result = func(*args, **kwargs)
                last_request_time = time.time()
                requests_count += 1
                return result
                
            except requests.exceptions.RequestException as e:
                if hasattr(e.response, 'status_code') and e.response.status_code == 429:
                    wait_time = retry_delay * (2 ** attempt)
                    print(Fore.YELLOW + f"\n⚠ Rate limit alcanzado (intento {attempt + 1}/{max_retries}). Esperando {wait_time}s..." + Style.RESET_ALL)
                    time.sleep(wait_time)
                    continue
                raise
                
        print(Fore.RED + f"\n✖ Error: Máximo de reintentos alcanzado para {func.__name__}" + Style.RESET_ALL)
        return None
        
    return wrapper


def handle_imagenes_producto(producto, DOWNLOAD_IMAGES):
    """Siempre descarga las imágenes desde la URL y las sube como adjuntos Base64.

    Args:
        producto (dict): Diccionario con datos del producto.
        DOWNLOAD_IMAGES (str): Este parámetro ya no se utiliza pero se mantiene por compatibilidad.

    Returns:
        list: Lista de diccionarios con imágenes listas para subir a Tiendanube.
    """
    imagenes_payload = []
    image_url = producto.get('imagen_url')

    if not image_url:
        return []

    try:
        print(Fore.CYAN + f"Descargando imagen desde: {image_url}" + Style.RESET_ALL)
        # Usamos verify=False por si hay certificados autofirmados en los dominios de origen.
        response = requests.get(image_url, timeout=20, verify=False)
        response.raise_for_status()

        image_content = response.content
        encoded_image = base64.b64encode(image_content).decode('utf-8')
        filename = os.path.basename(image_url.split('?')[0])

        imagenes_payload.append({
            "attachment": encoded_image,
            "filename": filename if filename else "image.jpg"
        })
        # print(Fore.GREEN + "✔ Imagen descargada y codificada en Base64." + Style.RESET_ALL)
    except requests.exceptions.RequestException as e:
        print(Fore.RED + f"Error al descargar la imagen {image_url}: {e}" + Style.RESET_ALL)

    return imagenes_payload

def subir_imagen_local(ruta_relativa):
    """Sube imagen local a Tiendanube y prepara estructura para API.
    
    Args:
        ruta_relativa (str): Ruta relativa de la imagen desde el script
        
    Returns:
        dict/None: Diccionario con datos de imagen para API o None si falla
    """
    try:
        # Construir y validar ruta
        base_dir = os.path.dirname(os.path.abspath(__file__))
        ruta_absoluta = os.path.normpath(os.path.join(base_dir, ruta_relativa))
        
        if not os.path.isfile(ruta_absoluta):
            print(Fore.RED + f"✖ Archivo de imagen no encontrado: {ruta_absoluta}" + Style.RESET_ALL)
            return None
            
        # Validar extensión de archivo
        extension = os.path.splitext(ruta_absoluta)[1][1:].lower()
        if extension not in ['jpg', 'jpeg', 'png', 'gif', 'webp']:
            print(Fore.YELLOW + f"⚠ Formato de imagen no soportado: {extension}" + Style.RESET_ALL)
            return None

        # Leer y procesar imagen
        with open(ruta_absoluta, "rb") as img_file:
            encoded_str = base64.b64encode(img_file.read()).decode('utf-8')
            
            return {
                "attachment": encoded_str,
                "filename": os.path.basename(ruta_absoluta),
                "content_type": f"image/{extension}" if extension != 'jpg' else "image/jpeg"
            }
            
    except PermissionError:
        print(Fore.RED + f"✖ Permiso denegado al leer: {ruta_absoluta}" + Style.RESET_ALL)
    except Exception as e:
        print(Fore.RED + f"✖ Error procesando imagen: {type(e).__name__} - {str(e)}" + Style.RESET_ALL)
        
    return None

# Decorador para medir el tiempo de ejecución de las funciones
def medir_tiempo(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        inicio = time.time()
        resultado = func(*args, **kwargs)
        fin = time.time()
        print(Fore.YELLOW + f"Tiempo de ejecución de {func.__name__}: {fin - inicio:.4f} segundos" + Style.RESET_ALL)
        return resultado
    return wrapper

@manejar_rate_limiting
def buscar_id_categoria(nombre, parent_id=None):
    """Busca categoría por nombre y parent_id específico"""
    categorias = obtener_categorias_tienda()
    nombre = nombre.strip().lower()
    #print( "NOMBRE - buscar_id_categoria: "+nombre)
    
    # Primero buscar coincidencia exacta con parent_id
    for cat in categorias:
        cat_nombre = cat['nombre'].lower().strip()
        cat_parent_id = cat.get('parent_id')

        
        
        if cat_nombre == nombre:
            if parent_id is None and cat_parent_id is None:
                return cat['id']
            elif parent_id is not None and cat_parent_id == parent_id:
                return cat['id']
    
    return None

@manejar_rate_limiting
def obtener_ids_categorias(producto):
    """Obtiene IDs de categorías en formato [id1, id2, id3] con soporte para subcategorías anidadas"""
    
    if producto['codigo'] in cache_ids_categorias:
        return cache_ids_categorias[producto['codigo']]
    
    ids = []
    try:
        
        categoria_principal = producto['categoria'].strip()
        if categoria_principal:
            categoria_id = buscar_id_categoria(categoria_principal)
            if not categoria_id:
                categoria_id = crear_categoria(categoria_principal)
            
            if categoria_id:
                ids.append(categoria_id)
                parent_id = categoria_id  # Padre inicial
                
                # Procesar subcategorías anidadas
                if producto.get('subcategoria'):
                    subcategorias = [s.strip() for s in producto['subcategoria'].split(',') if s.strip()]
                    
                    for subcat in subcategorias:
                        # Buscar bajo el padre actual
                        subcat_id = buscar_id_categoria(subcat, parent_id)
                        if not subcat_id:
                            subcat_id = crear_categoria(subcat, parent_id)
                        
                        if subcat_id:
                            ids.append(subcat_id)
                            parent_id = subcat_id  # Actualizar padre para la próxima subcategoría
                        else:
                            break  # Si falla una, detener la cadena
    
        cache_ids_categorias[producto['codigo']] = ids if ids else None
        return ids
    
    except Exception as e:
        print(Fore.RED + f"Error obteniendo IDs de categorías: {str(e)}" + Style.RESET_ALL)
        return None


def crear_producto(producto, PATH, GANANCIA_PORCENTAJE, DOWNLOAD_IMAGES):
    """Crea un nuevo producto manejando categorías existentes o nuevas"""
    # Formatear precio
    precio_str = producto['precio'].replace('$', '').replace('.', '').replace(',', '.')
    precio = float(precio_str) * (1 + GANANCIA_PORCENTAJE/100)
    
    categorias = producto['categoria'] + ', ' + producto['subcategoria']
        
    # Obtener dimensiones usando DeepSeek
    #print(Fore.YELLOW + "Obteniendo dimensiones con DeepSeek..." + Style.RESET_ALL)
    producto_lista = [{
        'descripcion': producto['descripcion'],
        'codigo': producto['codigo']
    }]
    dimensiones = obtener_dimensiones_producto(producto_lista, categorias, PATH)
    if dimensiones:
        peso_kg = dimensiones[0]['peso_kg']
        ancho_cm = dimensiones[0]['ancho_cm']
        alto_cm = dimensiones[0]['alto_cm']
        profundidad_cm = dimensiones[0]['profundidad_cm']
        #print(Fore.GREEN + f"✔ Dimensiones obtenidas: {peso_kg}kg, {ancho_cm}x{alto_cm}x{profundidad_cm}cm" + Style.RESET_ALL)
    else:
        #print(Fore.YELLOW + "⚠ No se pudieron obtener dimensiones, usando valores por defecto" + Style.RESET_ALL)
        peso_kg = 0.05
        ancho_cm = 0.05
        alto_cm = 0.05
        profundidad_cm = 0.05
        
    try:
        # 1. Construir payload completo
        payload = {
            "name": producto['descripcion'],
            "variants": [{
                "price": precio,
                "stock_management": False,
                "sku": producto['codigo'],
                "barcode": producto['codigo_de_barras'],
                "weight": peso_kg,
                "width": ancho_cm,
                "height": alto_cm,
                "depth": profundidad_cm
            }],
            "published": True,
            "images": handle_imagenes_producto(producto, DOWNLOAD_IMAGES),
            "categories": obtener_ids_categorias(producto)
        }
        
        # 3. Enviar request consolidado
        response = requests.post(
            f"{BASE_URL}/products",
            headers=headers,
            json=payload
        )
        response.raise_for_status()
        
        return response.json()['id']
        
    except Exception as e:
        print(Fore.RED + f"Error creando producto: {type(e).__name__} - {str(e)}" + Style.RESET_ALL)
        # Imprimir el payload para depuración
        if 'payload' in locals():
            print(Fore.YELLOW + "--- Payload Enviado ---" + Style.RESET_ALL)
            print(json.dumps(payload, indent=2, ensure_ascii=False))
            print(Fore.YELLOW + "-----------------------" + Style.RESET_ALL)

        if hasattr(e, 'response') and e.response:
            print(Fore.RED + f"Respuesta de la API: {e.response.text}" + Style.RESET_ALL)
        return None


def crear_categoria(nombre, parent_id=None):
    """Crea categoría con estructura compatible"""
    try:
        # Validación básica del nombre
        if not nombre or not isinstance(nombre, str):
            print(Fore.RED + "Error: Nombre de categoría inválido" + Style.RESET_ALL)
            return None
            
        nombre = nombre.strip()
        if not nombre:
            print(Fore.RED + "Error: El nombre no puede estar vacío" + Style.RESET_ALL)
            return None

        # Verificar si la categoría ya existe
        categoria_id = buscar_id_categoria(nombre, parent_id)
        if categoria_id:
            print(Fore.YELLOW + f"Categoría '{nombre}' ya existe con ID: {categoria_id}" + Style.RESET_ALL)
            return categoria_id

        # Construir payload
        payload = {
            "name": {
                "es": nombre
            }
        }
        
        # Solo agregar parent si existe
        if parent_id is not None:
            if not isinstance(parent_id, int):
                print(Fore.RED + f"Error: parent_id debe ser entero (recibido {type(parent_id)})" + Style.RESET_ALL)
                return None
            payload["parent"] = parent_id

        #print(Fore.CYAN + f"Creando categoría: {nombre} (parent_id: {parent_id})" + Style.RESET_ALL)
        
        response = requests.post(
            f"{BASE_URL}/categories",
            headers=headers,
            json=payload,
            timeout=10
        )
        
        response_data = response.json()
        
        if response.status_code not in [200, 201]:
            print(Fore.RED + f"Error HTTP {response.status_code}: {response_data}" + Style.RESET_ALL)
            return None
            
        if 'id' not in response_data:
            print(Fore.RED + f"Respuesta API inesperada: {response_data}" + Style.RESET_ALL)
            return None

        # Limpiar caché
        if 'categorias' in cache_categorias:
            del cache_categorias['categorias']
        
        categoria_id = response_data['id']
        #print(Fore.GREEN + f"Categoría '{nombre}' creada con ID: {categoria_id}" + Style.RESET_ALL)
        return categoria_id
        
    except Exception as e:
        print(Fore.RED + f"Error crítico: {type(e).__name__} - {str(e)}" + Style.RESET_ALL)
        return None

@manejar_rate_limiting
def obtener_categorias_tienda():
    """Obtiene todas las categorías de la tienda con sus IDs"""
    # Verificar si hay datos en caché
    if 'categorias' in cache_categorias and cache_categorias['categorias']:
        return cache_categorias['categorias']
        
    try:
        headers = {
            "Authentication": f"bearer {ACCESS_TOKEN}",
            "User-Agent": "JG-STORE (jgstore244@gmail.com)"
        }
        
        categorias = []
        page = 1
        per_page = 200  # Máximo permitido por la API
        
        while True:
            url = f"https://api.tiendanube.com/v1/{STORE_ID}/categories?page={page}&per_page={per_page}"
            response = requests.get(url, headers=headers)
            response.raise_for_status()
            
            categorias_pagina = response.json()
            if not categorias_pagina:
                break
                
            for cat in categorias_pagina:
                categoria = {
                    "id": cat['id'],
                    "nombre": cat['name']['es'] if 'es' in cat['name'] else cat['name']['pt'],
                    "parent_id": None
                }
                
                if 'parent' in cat and cat['parent']:
                    if isinstance(cat['parent'], dict):
                        categoria['parent_id'] = cat['parent'].get('id')
                    else:
                        categoria['parent_id'] = cat['parent']
                
                categorias.append(categoria)
            
            if len(categorias_pagina) < per_page:
                break
                
            page += 1
        
        # Almacenar en caché
        cache_categorias['categorias'] = categorias  
        return categorias
        
    except Exception as e:
        print(Fore.RED + f"Error obteniendo categorías: {str(e)}" + Fore.RESET)
        return []

@manejar_rate_limiting
def agregar_imagen(producto_id, imagen_url):
    """Agrega imagen a un producto existente"""
    try:
        response = requests.post(
            f"{BASE_URL}/products/{producto_id}/images",
            headers=headers,
            json={"src": imagen_url}
        )
        response.raise_for_status()
        return True
    except Exception as e:
        print(Fore.RED + f"Error agregando imagen: {str(e)}" + Style.RESET_ALL)
        return False
    
@manejar_rate_limiting
def actualizar_producto(producto_id, producto, ganancia_porcentaje, DOWNLOAD_IMAGES):
    """Actualiza un producto con manejo optimizado de categorías e imágenes"""
    try:
        # 1. Actualizar datos básicos (incluyendo categorías)
        # Formatear precio
        precio_str = producto['precio'].replace('$', '').replace('.', '').replace(',', '.')
        precio = float(precio_str) * (1 + (ganancia_porcentaje)/100)
        print(Fore.GREEN + f"Precio formateado: {precio}" + Style.RESET_ALL)
        
        payload_base = {
            "name": producto['descripcion'],
            "categories": obtener_ids_categorias(producto),
            "price": precio,      
        }
        
        response = requests.put(
            f"{BASE_URL}/products/{producto_id}",
            headers=headers,
            json=payload_base
        )
        response.raise_for_status()
        

        
        
        # 3. Actualiza variante (requiere ID de variante)
        variante_id = obtener_id_variante(producto_id)
        if variante_id:
            payload_variante = {
                "stock_management": False,
                "sku": producto['codigo'],
                "barcode": producto['codigo_de_barras'],
                "price": precio,
            }
            
           
            
            response = requests.put(
                f"{BASE_URL}/products/{producto_id}/variants/{variante_id}",
                headers=headers,
                json=payload_variante
            )
            response.raise_for_status()

         

            
    

        print(Fore.GREEN + f"✔ Producto {producto_id} actualizado correctamente - Precio: {precio} | Codigo: {producto['codigo']} | Codigo de Barras: {producto['codigo_de_barras']}" + Style.RESET_ALL)
        return True

    except requests.exceptions.HTTPError as e:
        error_msg = f"Error API ({e.response.status_code}): "
        if e.response.text:
            error_msg += e.response.json().get('message', e.response.text)
        print(Fore.RED + error_msg + Style.RESET_ALL)
        return False
        
    except Exception as e:
        print(Fore.RED + f"Error inesperado actualizando producto: {type(e).__name__} - {str(e)}" + Style.RESET_ALL)
        return False

@manejar_rate_limiting
def buscar_producto_por_sku(sku):
    """Busca un producto por SKU usando caché de páginas completas"""
    headers = {
        "Authentication": f"bearer {ACCESS_TOKEN}",
        "User-Agent": "JG-STORE (jgstore244@gmail.com)"
    }
    
    page = 1
    per_page = 200
    pbar = None
    
    try:
        while True:
            # Primero verificar caché
            cache_key = f"products_page_{page}"
            if cache_key in products_cache:
                productos = products_cache[cache_key]
            else:
                # Si es la primera vez que necesitamos usar la API, inicializar la barra
                if pbar is None:
                    # Obtener total de productos para la barra de progreso
                    params = {'page': 1, 'per_page': 1}
                    response = requests.get(f"{BASE_URL}/products", headers=headers, params=params)
                    response.raise_for_status()
                    total_products = int(response.headers.get('X-Total-Count', 1000))
                    total_pages = (total_products + per_page - 1) // per_page
                    pbar = tqdm(total=total_pages, desc="Guardando API de Productos en Cache", unit="página",
                              bar_format="{l_bar}{bar}| {n_fmt}/{total_fmt} [{elapsed}<{remaining}]")
                
                # Obtener de API si no está en caché
                params = {'page': page, 'per_page': per_page}
                response = requests.get(f"{BASE_URL}/products", headers=headers, params=params)
                response.raise_for_status()
                productos = response.json()
                products_cache[cache_key] = productos
                save_cache()
                
                # Actualizar la barra solo si existe
                if pbar:
                    pbar.update(1)
            
            # Buscar SKU en los productos
            for producto in productos:
                for variante in producto.get('variants', []):
                    if variante.get('sku') == sku:
                        if pbar:  # Cerrar la barra si existe
                            pbar.close()
                        return producto["id"]
            
            if len(productos) < per_page:
                break
                
            page += 1
        
        return None
    finally:
        if pbar:  # Cerrar la barra si existe
            pbar.close()

@manejar_rate_limiting
def obtener_id_variante(producto_id):
    """Obtiene el ID de la primera variante del producto"""
    # Verificar si el ID de variante ya está en la caché
    if producto_id in cache_variante:
        return cache_variante[producto_id]
    try:
        response = requests.get(
            f"{BASE_URL}/products/{producto_id}/variants",
            headers=headers
        )
        response.raise_for_status()
        variante_id = response.json()[0]['id']
        # Almacenar en caché
        cache_variante[producto_id] = variante_id
        return variante_id
    except Exception:
        return None

@manejar_rate_limiting
def limpiar_cache_productos():
    """Elimina todos los archivos de caché de productos"""
    try:
        if os.path.exists(PRODUCTS_CACHE):
            os.remove(PRODUCTS_CACHE)
            print(Fore.YELLOW + "✓ Caché de productos eliminada" + Style.RESET_ALL)
        # Reiniciar caché en memoria
        global products_cache
        products_cache = {}
    except Exception as e:
        print(Fore.RED + f"Error limpiando caché: {str(e)}" + Style.RESET_ALL)
