from colorama import Fore, Style
import requests
import json
from typing import List
import time
from functools import wraps
import os
import json
from tqdm import tqdm
from app.deepseek import obtener_dimensiones_producto

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

#@medir_tiempo
def buscar_id_categoria(nombre_categoria):
    """Busca una categoría por nombre exacto o parcial"""
    categorias = obtener_categorias_tienda()
    nombre_categoria = nombre_categoria.lower().strip()
    
    # Primero intentar búsqueda exacta
    for cat in categorias:
        if cat['nombre'].lower().strip() == nombre_categoria:
            return cat['id']
    
    # Si no se encuentra exacta, intentar búsqueda parcial
    for cat in categorias:
        if nombre_categoria in cat['nombre'].lower().strip():
            return cat['id']
    
    return None

#@medir_tiempo
def obtener_ids_categorias(producto):
    """Obtiene IDs de categorías en formato [id1, id2, id3]"""
    
    # Verificar si el producto ya está en la caché
    if producto['codigo'] in cache_ids_categorias:
        return cache_ids_categorias[producto['codigo']]
    try:
        ids = []
        
        # 1. Obtener categoría principal
        if producto.get('categoria'):
            categoria_id = buscar_id_categoria(producto['categoria'])
            if categoria_id is None:  # Solo crear si realmente no existe
                categoria_id = crear_categoria(producto['categoria'])
            
            if categoria_id:
                ids.append(categoria_id)
                
                # 2. Procesar subcategorías
                if producto.get('subcategoria'):
                    for subcat in producto['subcategoria'].split(','):
                        subcat = subcat.strip()
                        if subcat:
                            subcat_id = buscar_id_categoria(subcat)
                            if subcat_id is None:  # Solo crear si realmente no existe
                                subcat_id = crear_categoria(subcat, categoria_id)
                            if subcat_id:
                                ids.append(subcat_id)
        
        # Almacenar en caché
        cache_ids_categorias[producto['codigo']] = ids if ids else None
        return ids if ids else None
        
    except Exception as e:
        print(Fore.RED + f"Error obteniendo IDs de categorías: {str(e)}" + Style.RESET_ALL)
        return None

#@medir_tiempo
def crear_producto(producto, PATH):
    """Crea un nuevo producto manejando categorías existentes o nuevas"""
    # Formatear precio
    precio_str = producto['precio'].replace('$', '').replace('.', '').replace(',', '.')
    precio = float(precio_str)*2
    
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
            "images": [{"src": producto['imagen_url']}] if producto.get('imagen_url') else [],
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
        if hasattr(e, 'response') and e.response:
            print(Fore.RED + f"Respuesta API: {e.response.text}" + Style.RESET_ALL)
        return None

#@medir_tiempo
def crear_categoria(nombre, parent_id=None):
    """Crea categoría con estructura compatible"""
    global cache_categorias  # Declaramos que usaremos la variable global
    try:
        payload = {
            "name": nombre,
            "parent": parent_id
        }
        
        response = requests.post(
            f"{BASE_URL}/categories",
            headers=headers,
            json=payload
        )
        response.raise_for_status()
        categoria_id = response.json().get('id')
        
        # Actualizar la caché después de crear una nueva categoría
        save_cache()  # Guardar la caché actualizada
        cache_categorias = {}  # Forzar recarga de categorías
        
        return categoria_id
        
    except Exception as e:
        print(Fore.RED + f"Error creando categoría {nombre}: {str(e)}" + Style.RESET_ALL)
        if hasattr(e, 'response') and e.response:
            print(Fore.RED + f"Respuesta: {e.response.text}" + Style.RESET_ALL)
        return None

#@medir_tiempo
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
    
#@medir_tiempo
def actualizar_producto(producto_id, producto):
    """Actualiza un producto con manejo optimizado de categorías e imágenes"""
    try:
        # 1. Actualizar datos básicos (incluyendo categorías)
        payload_base = {
            "name": producto['descripcion'],
            "categories": obtener_ids_categorias(producto)
        }
        
        response = requests.put(
            f"{BASE_URL}/products/{producto_id}",
            headers=headers,
            json=payload_base
        )
        response.raise_for_status()
        
        # 2. Actualizar variante (requiere ID de variante)
        variante_id = obtener_id_variante(producto_id)
        if variante_id:
            payload_variante = {
                "stock_management": False,
                "sku": producto['codigo'],
                "barcode": producto['codigo_de_barras']
            }
            
           
            
            response = requests.put(
                f"{BASE_URL}/products/{producto_id}/variants/{variante_id}",
                headers=headers,
                json=payload_variante
            )
            response.raise_for_status()

         # 3. Actualizar imagen (elimina existentes y agrega nueva)
        if producto.get('imagen_url'):
            # Eliminar imágenes existentes
            imagenes = requests.get(
                f"{BASE_URL}/products/{producto_id}/images",
                headers=headers
            ).json()
            
            for img in imagenes:
                requests.delete(
                    f"{BASE_URL}/products/{producto_id}/images/{img['id']}",
                    headers=headers
                ).raise_for_status()
            
            # Agregar nueva imagen
            response = requests.post(
                f"{BASE_URL}/products/{producto_id}/images",
                headers=headers,
                json={"src": producto['imagen_url']}
            )
            response.raise_for_status()
            
    

        print(Fore.GREEN + f"✔ Producto {producto_id} actualizado correctamente" + Style.RESET_ALL)
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
    


#@medir_tiempo
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
#@medir_tiempo
def obtener_categorias_tienda():
    """Obtiene todas las categorías de la tienda con sus IDs"""
    # Verificar si las categorías ya están en la caché
    if 'categorias' in cache_categorias:
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
                
            categorias.extend([
                {
                    "id": cat['id'],
                    "nombre": cat['name']['es'] if 'es' in cat['name'] else cat['name']['pt'],
                    "handle": cat['handle']['es'] if 'es' in cat['handle'] else cat['handle']['pt']
                }
                for cat in categorias_pagina
            ])
            
            if len(categorias_pagina) < per_page:
                break
                
            page += 1
        
        # Almacenar en caché
        cache_categorias['categorias'] = categorias
        return categorias
        
    except Exception as e:
        print(Fore.RED + f"Error obteniendo categorías: {str(e)}" + Fore.RESET)
        return []

#@medir_tiempo
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

# Función para manejar rate limiting con backoff exponencial
def manejar_rate_limiting(func, max_retries=5, initial_delay=1):
    """
    Decorador para manejar errores 429 con reintentos exponenciales
    
    Args:
        func: Función a decorar
        max_retries: Máximo número de reintentos
        initial_delay: Delay inicial en segundos
    """
    def wrapper(*args, **kwargs):
        retries = 0
        delay = initial_delay
        
        while retries < max_retries:
            try:
                return func(*args, **kwargs)
            except requests.exceptions.HTTPError as e:
                if e.response.status_code == 429:  # Too Many Requests
                    print(Fore.YELLOW + f"Rate limit alcanzado. Reintentando en {delay} segundos..." + Style.RESET_ALL)
                    time.sleep(delay)
                    delay *= 2  # Backoff exponencial
                    retries += 1
                else:
                    raise
        
        raise Exception(f"Máximo de reintentos ({max_retries}) alcanzado")
    
    return wrapper

@manejar_rate_limiting
#@medir_tiempo
def actualizar_producto(producto_id, producto):
    """Actualiza un producto con manejo optimizado de categorías e imágenes"""
    try:
        # 1. Actualizar datos básicos (incluyendo categorías)
        payload_base = {
            "name": producto['descripcion'],
            "categories": obtener_ids_categorias(producto)
        }
        
        response = requests.put(
            f"{BASE_URL}/products/{producto_id}",
            headers=headers,
            json=payload_base
        )
        response.raise_for_status()
        
        # 2. Actualizar variante (requiere ID de variante)
        variante_id = obtener_id_variante(producto_id)
        if variante_id:
            payload_variante = {
                "stock_management": False,
                "sku": producto['codigo'],
                "barcode": producto['codigo_de_barras']
            }
            
           
            
            response = requests.put(
                f"{BASE_URL}/products/{producto_id}/variants/{variante_id}",
                headers=headers,
                json=payload_variante
            )
            response.raise_for_status()

         # 3. Actualizar imagen (elimina existentes y agrega nueva)
        if producto.get('imagen_url'):
            # Eliminar imágenes existentes
            imagenes = requests.get(
                f"{BASE_URL}/products/{producto_id}/images",
                headers=headers
            ).json()
            
            for img in imagenes:
                requests.delete(
                    f"{BASE_URL}/products/{producto_id}/images/{img['id']}",
                    headers=headers
                ).raise_for_status()
            
            # Agregar nueva imagen
            response = requests.post(
                f"{BASE_URL}/products/{producto_id}/images",
                headers=headers,
                json={"src": producto['imagen_url']}
            )
            response.raise_for_status()
            
    

        print(Fore.GREEN + f"✔ Producto {producto_id} actualizado correctamente" + Style.RESET_ALL)
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