import requests
import json
from colorama import Fore, Style
from typing import List

# Variables necesarias
ACCESS_TOKEN = "cdcad052f53bae4972979dbf6900925d4e9a36dc"  # Tu token de acceso obtenido
STORE_ID = "5950659"  # El ID de tu tienda (por ejemplo, 5950659)
BASE_URL = f"https://api.tiendanube.com/v1/{STORE_ID}"

headers = {
        "Authentication": f"bearer {ACCESS_TOKEN}",
        "Content-Type": "application/json",
        "User-Agent": "API-KEY (jgstore244@gmail.com)"

    }


def buscar_id_categoria(nombre_categoria):
    categorias = obtener_categorias_tienda()
    for cat in categorias:
        if nombre_categoria.lower() in cat['nombre'].lower():
            return cat['id']
    return None

def obtener_ids_categorias(producto):
    """Obtiene IDs de categorías en formato [id1, id2, id3]"""
    try:
        ids = []
        
        # 1. Obtener categoría principal
        if producto.get('categoria'):
            categoria_id = buscar_id_categoria(producto['categoria']) or crear_categoria(producto['categoria'])
            if categoria_id:
                ids.append(categoria_id)
                
                # 2. Procesar subcategorías
                if producto.get('subcategoria'):
                    for subcat in producto['subcategoria'].split(','):
                        subcat = subcat.strip()
                        if subcat:
                            subcat_id = buscar_id_categoria(subcat) or crear_categoria(subcat, categoria_id)
                            if subcat_id:
                                ids.append(subcat_id)
        
        return ids if ids else None
        
    except Exception as e:
        print(Fore.RED + f"Error obteniendo IDs de categorías: {str(e)}" + Style.RESET_ALL)
        return None
    
def crear_producto(producto):
    """Crea un nuevo producto manejando categorías existentes o nuevas"""
    # Convertir precio
    precio_str = producto['precio'].replace('$', '').replace('.', '').replace(',', '.')
    precio = float(precio_str)*2
        
    # Convertir medidas
    peso_kg = float(producto.get('peso_kg', 0))
    ancho_cm = float(producto.get('ancho_cm', 0))
    alto_cm = float(producto.get('alto_cm', 0))
    profundidad_cm = float(producto.get('profundidad_cm', 0))
        
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
        
         # DEBUG: Mostrar payload completo
        """ print("\n" + Fore.CYAN + "=== PAYLOAD A ENVIAR ===" + Style.RESET_ALL)
        print(json.dumps(payload, indent=2, ensure_ascii=False))
        print(Fore.CYAN + "=========================" + Style.RESET_ALL + "\n")"""
        
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

def crear_categoria(nombre, parent_id=None):
    """Crea categoría con estructura compatible"""
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
        return response.json().get('id')
        
    except Exception as e:
        print(Fore.RED + f"Error creando categoría {nombre}: {str(e)}" + Style.RESET_ALL)
        if hasattr(e, 'response') and e.response:
            print(Fore.RED + f"Respuesta: {e.response.text}" + Style.RESET_ALL)
        return None

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
    
def buscar_producto_por_sku(sku):
    """Busca un producto por su SKU (código) con paginación incluida"""
    try:
        headers = {
            "Authentication": f"bearer {ACCESS_TOKEN}",
            "User-Agent": "JG-STORE (josegarcia@gmail.com)"
        }
        
        page = 1
        per_page = 200  # Máximo permitido por la API
        
        while True:
            url = f"https://api.tiendanube.com/v1/{STORE_ID}/products?page={page}&per_page={per_page}"
            response = requests.get(url, headers=headers)
            response.raise_for_status()
            
            productos = response.json()
            if not productos:
                return None  # Fin de paginación
            
            # Buscar SKU en los productos de esta página
            for producto in productos:
                for variante in producto.get('variants', []):
                    if variante.get('sku') == sku:
                        return producto["id"]
            
            # Verificar si hay más páginas
            if len(productos) < per_page:
                return None  # No hay más productos
                
            page += 1
            
    except Exception as e:
        print(Fore.RED + f"Error buscando producto por SKU: {str(e)}" + Fore.RESET)
        return None

def obtener_categorias_tienda():
    """Obtiene todas las categorías de la tienda con sus IDs"""
    try:
        headers = {
            "Authentication": f"bearer {ACCESS_TOKEN}",
            "User-Agent": "JG-STORE (josegarcia@gmail.com)"
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
            
        return categorias
        
    except Exception as e:
        print(Fore.RED + f"Error obteniendo categorías: {str(e)}" + Fore.RESET)
        return []

def obtener_id_variante(producto_id):
    """Obtiene el ID de la primera variante del producto"""
    try:
        response = requests.get(
            f"{BASE_URL}/products/{producto_id}/variants",
            headers=headers
        )
        response.raise_for_status()
        return response.json()[0]['id']
    except Exception:
        return None


""" def eliminar_todos_productos_tiendanube(access_token: str, store_id: str) -> bool:
    
    # Elimina todos los productos de una tienda Tiendanube (maneja paginación)
    
    base_url = f"https://api.tiendanube.com/v1/{store_id}/products"
    headers = {
        "Authentication": f"bearer {access_token}",
        "User-Agent": "JG-STORE Scraping (josegarcia@gmail.com)"
    }
    
    try:
        page = 1
        total_eliminados = 0
        
        while True:
            # 1. Obtener productos paginados
            params = {'page': page, 'per_page': 200}  # Máximo permitido
            response = requests.get(base_url, headers=headers, params=params)
            response.raise_for_status()
            productos = response.json()
            
            if not productos:
                break  # No hay más productos
                
            # 2. Eliminar cada producto de la página actual
            for producto in productos:
                product_id = producto['id']
                delete_url = f"{base_url}/{product_id}"
                
                delete_response = requests.delete(delete_url, headers=headers)
                delete_response.raise_for_status()
                print(f"Producto eliminado: {product_id}")
                total_eliminados += 1
                
            page += 1  # Ir a la siguiente página
            
        print(f"Se eliminaron {total_eliminados} productos correctamente")
        return True
        
    except requests.exceptions.RequestException as e:
        print(f"Error al eliminar productos: {str(e)}")
        return False

if eliminar_todos_productos_tiendanube(ACCESS_TOKEN, STORE_ID):
    print("Eliminación completada con éxito")
else:
    print("Hubo errores durante la eliminación") """