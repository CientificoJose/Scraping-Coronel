import os
import time
import json
import base64
import requests
from typing import List, Dict, Optional
from functools import wraps
from colorama import Fore, Style
from tqdm import tqdm

class TiendanubeClient:
    def __init__(self, store_id: str, access_token: str, user_agent: str):
        self.store_id = store_id
        self.access_token = access_token
        self.user_agent = user_agent
        self.base_url = f"https://api.tiendanube.com/v1/{self.store_id}"
        self.headers = {
            "Authentication": f"bearer {self.access_token}",
            "Content-Type": "application/json",
            "User-Agent": self.user_agent
        }
        
        # Caché de productos en disco
        self.cache_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'api_cache')
        self.products_cache_path = os.path.join(self.cache_dir, 'products_cache.json')
        os.makedirs(self.cache_dir, exist_ok=True)
        self.products_cache = self._load_cache()
        
        # Cachés en memoria
        self.cache_categorias = {}
        self.cache_variante = {}
        self.cache_ids_categorias = {}

    def _load_cache(self) -> Dict:
        try:
            if os.path.exists(self.products_cache_path):
                with open(self.products_cache_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
        except Exception as e:
            print(Fore.YELLOW + f"Advertencia cargando caché: {e}" + Style.RESET_ALL)
        return {}

    def save_cache(self):
        try:
            with open(self.products_cache_path, 'w', encoding='utf-8') as f:
                json.dump(self.products_cache, f, indent=2)
        except Exception as e:
            print(Fore.YELLOW + f"Error guardando caché: {e}" + Style.RESET_ALL)

    def limpiar_cache_productos(self):
        try:
            if os.path.exists(self.products_cache_path):
                os.remove(self.products_cache_path)
                print(Fore.YELLOW + "✓ Caché de productos eliminada" + Style.RESET_ALL)
            self.products_cache = {}
        except Exception as e:
            print(Fore.RED + f"Error limpiando caché: {str(e)}" + Style.RESET_ALL)

    def buscar_id_categoria(self, nombre: str, parent_id: Optional[int] = None) -> Optional[int]:
        categorias = self.obtener_categorias_tienda()
        nombre = nombre.strip().lower()
        for cat in categorias:
            cat_nombre = cat['nombre'].lower().strip()
            cat_parent_id = cat.get('parent_id')
            if cat_nombre == nombre:
                if parent_id is None and cat_parent_id is None:
                    return cat['id']
                elif parent_id is not None and cat_parent_id == parent_id:
                    return cat['id']
        return None

    def crear_categoria(self, nombre: str, parent_id: Optional[int] = None) -> Optional[int]:
        try:
            nombre = nombre.strip()
            if not nombre:
                return None
            categoria_id = self.buscar_id_categoria(nombre, parent_id)
            if categoria_id:
                return categoria_id

            payload = {"name": {"es": nombre}}
            if parent_id is not None:
                payload["parent"] = parent_id

            response = requests.post(f"{self.base_url}/categories", headers=self.headers, json=payload, timeout=10)
            response.raise_for_status()
            
            if 'categorias' in self.cache_categorias:
                del self.cache_categorias['categorias']
            
            return response.json().get('id')
        except Exception as e:
            print(Fore.RED + f"Error creando categoría: {e}" + Style.RESET_ALL)
        return None

    def obtener_categorias_tienda(self) -> List[Dict]:
        if 'categorias' in self.cache_categorias and self.cache_categorias['categorias']:
            return self.cache_categorias['categorias']
        try:
            categorias = []
            page = 1
            per_page = 200
            while True:
                url = f"{self.base_url}/categories?page={page}&per_page={per_page}"
                response = requests.get(url, headers=self.headers, timeout=15)
                response.raise_for_status()
                categorias_pagina = response.json()
                if not categorias_pagina:
                    break
                for cat in categorias_pagina:
                    categoria = {
                        "id": cat['id'],
                        "nombre": cat['name']['es'] if 'es' in cat['name'] else cat['name'].get('pt', ''),
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
            self.cache_categorias['categorias'] = categorias
            return categorias
        except Exception as e:
            print(Fore.RED + f"Error obteniendo categorías: {str(e)}" + Style.RESET_ALL)
            return []

    def obtener_ids_categorias(self, producto: Dict) -> List[int]:
        if producto['codigo'] in self.cache_ids_categorias:
            return self.cache_ids_categorias[producto['codigo']]
        
        ids = []
        try:
            categoria_principal = producto['categoria'].strip()
            if categoria_principal:
                categoria_id = self.buscar_id_categoria(categoria_principal)
                if not categoria_id:
                    categoria_id = self.crear_categoria(categoria_principal)
                if categoria_id:
                    ids.append(categoria_id)
                    parent_id = categoria_id
                    
                    if producto.get('subcategoria'):
                        subcategorias = [s.strip() for s in producto['subcategoria'].split(',') if s.strip()]
                        for subcat in subcategorias:
                            subcat_id = self.buscar_id_categoria(subcat, parent_id)
                            if not subcat_id:
                                subcat_id = self.crear_categoria(subcat, parent_id)
                            if subcat_id:
                                ids.append(subcat_id)
                                parent_id = subcat_id
                            else:
                                break
            self.cache_ids_categorias[producto['codigo']] = ids
            return ids
        except Exception as e:
            print(Fore.RED + f"Error obteniendo IDs de categorías: {str(e)}" + Style.RESET_ALL)
            return []

    def handle_imagenes_producto(self, producto: Dict, download_images_flag: str) -> List[Dict]:
        imagenes_payload = []
        image_url = producto.get('imagen_url')
        if not image_url:
            return []
        try:
            print(Fore.CYAN + f"Descargando imagen desde: {image_url}" + Style.RESET_ALL)
            response = requests.get(image_url, timeout=20, verify=False)
            response.raise_for_status()
            encoded_image = base64.b64encode(response.content).decode('utf-8')
            filename = os.path.basename(image_url.split('?')[0])
            imagenes_payload.append({
                "attachment": encoded_image,
                "filename": filename if filename else "image.jpg"
            })
        except Exception as e:
            print(Fore.RED + f"Error al descargar la imagen {image_url}: {e}" + Style.RESET_ALL)
        return imagenes_payload

    def subir_imagen_local(self, ruta_relativa: str) -> Optional[Dict]:
        try:
            base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            ruta_absoluta = os.path.normpath(os.path.join(base_dir, ruta_relativa))
            if not os.path.isfile(ruta_absoluta):
                return None
            extension = os.path.splitext(ruta_absoluta)[1][1:].lower()
            with open(ruta_absoluta, "rb") as img_file:
                encoded_str = base64.b64encode(img_file.read()).decode('utf-8')
                return {
                    "attachment": encoded_str,
                    "filename": os.path.basename(ruta_absoluta),
                    "content_type": f"image/{extension}" if extension != 'jpg' else "image/jpeg"
                }
        except Exception:
            return None

    def buscar_producto_por_sku(self, sku: str) -> Optional[int]:
        page = 1
        per_page = 200
        pbar = None
        try:
            while True:
                cache_key = f"products_page_{page}"
                if cache_key in self.products_cache:
                    productos = self.products_cache[cache_key]
                else:
                    if pbar is None:
                        response_count = requests.get(f"{self.base_url}/products?page=1&per_page=1", headers=self.headers, timeout=10)
                        total_products = int(response_count.headers.get('X-Total-Count', 1000)) if response_count.ok else 1000
                        total_pages = (total_products + per_page - 1) // per_page
                        pbar = tqdm(total=total_pages, desc="Guardando API de Productos en Cache", unit="página",
                                  bar_format="{l_bar}{bar}| {n_fmt}/{total_fmt} [{elapsed}<{remaining}]")
                    
                    url = f"{self.base_url}/products?page={page}&per_page={per_page}"
                    response = requests.get(url, headers=self.headers, timeout=15)
                    response.raise_for_status()
                    productos = response.json()
                    self.products_cache[cache_key] = productos
                    self.save_cache()
                    if pbar:
                        pbar.update(1)
                
                for producto in productos:
                    for variante in producto.get('variants', []):
                        if variante.get('sku') == sku:
                            if pbar:
                                pbar.close()
                            return producto["id"]
                if len(productos) < per_page:
                    break
                page += 1
            return None
        finally:
            if pbar:
                pbar.close()

    def obtener_id_variante(self, producto_id: int) -> Optional[int]:
        if producto_id in self.cache_variante:
            return self.cache_variante[producto_id]
        try:
            response = requests.get(f"{self.base_url}/products/{producto_id}/variants", headers=self.headers, timeout=10)
            response.raise_for_status()
            variante_id = response.json()[0]['id']
            self.cache_variante[producto_id] = variante_id
            return variante_id
        except Exception:
            pass
        return None

    def agregar_imagen(self, producto_id: int, imagen_url: str) -> bool:
        try:
            response = requests.post(f"{self.base_url}/products/{producto_id}/images", headers=self.headers, json={"src": imagen_url}, timeout=10)
            return response.ok
        except Exception as e:
            print(Fore.RED + f"Error agregando imagen: {str(e)}" + Style.RESET_ALL)
            return False

    def crear_producto(self, producto: Dict, db_path: str, ganancia_porcentaje: int, download_images_flag: str) -> Optional[int]:
        from app.services.ai_estimator import obtener_dimensiones_producto
        
        precio_str = producto['precio'].replace('$', '').replace('.', '').replace(',', '.')
        precio = float(precio_str) * (1 + ganancia_porcentaje/100)
        categorias = producto['categoria'] + ', ' + producto['subcategoria']
        
        producto_lista = [{
            'descripcion': producto['descripcion'],
            'codigo': producto['codigo']
        }]
        
        dimensiones = obtener_dimensiones_producto(producto_lista, categorias, db_path)
        if dimensiones and 'peso_kg' in dimensiones[0]:
            peso_kg = dimensiones[0]['peso_kg']
            ancho_cm = dimensiones[0]['ancho_cm']
            alto_cm = dimensiones[0]['alto_cm']
            profundidad_cm = dimensiones[0]['profundidad_cm']
        else:
            peso_kg = 0.05
            ancho_cm = 0.05
            alto_cm = 0.05
            profundidad_cm = 0.05
            
        try:
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
                "images": self.handle_imagenes_producto(producto, download_images_flag),
                "categories": self.obtener_ids_categorias(producto)
            }
            
            response = requests.post(f"{self.base_url}/products", headers=self.headers, json=payload, timeout=20)
            response.raise_for_status()
            return response.json()['id']
        except Exception as e:
            print(Fore.RED + f"Error creando producto: {type(e).__name__} - {str(e)}" + Style.RESET_ALL)
            if 'payload' in locals():
                print(Fore.YELLOW + "--- Payload Enviado ---" + Style.RESET_ALL)
                print(json.dumps(payload, indent=2, ensure_ascii=False))
                print(Fore.YELLOW + "-----------------------" + Style.RESET_ALL)
            if hasattr(e, 'response') and e.response:
                print(Fore.RED + f"Respuesta de la API: {e.response.text}" + Style.RESET_ALL)
        return None

    def actualizar_producto(self, producto_id: int, producto: Dict, ganancia_porcentaje: int, download_images_flag: str) -> bool:
        try:
            precio_str = producto['precio'].replace('$', '').replace('.', '').replace(',', '.')
            precio = float(precio_str) * (1 + ganancia_porcentaje/100)
            print(Fore.GREEN + f"Precio formateado: {precio}" + Style.RESET_ALL)
            
            payload_base = {
                "name": producto['descripcion'],
                "categories": self.obtener_ids_categorias(producto),
                "price": precio,      
            }
            
            response = requests.put(f"{self.base_url}/products/{producto_id}", headers=self.headers, json=payload_base, timeout=15)
            response.raise_for_status()
                
            variante_id = self.obtener_id_variante(producto_id)
            if variante_id:
                payload_variante = {
                    "stock_management": False,
                    "sku": producto['codigo'],
                    "barcode": producto['codigo_de_barras'],
                    "price": precio,
                }
                
                response_var = requests.put(f"{self.base_url}/products/{producto_id}/variants/{variante_id}", headers=self.headers, json=payload_variante, timeout=15)
                response_var.raise_for_status()
                    
            print(Fore.GREEN + f"✔ Producto {producto_id} actualizado correctamente - Precio: {precio} | Codigo: {producto['codigo']}" + Style.RESET_ALL)
            return True
        except Exception as e:
            print(Fore.RED + f"Error inesperado actualizando producto: {type(e).__name__} - {str(e)}" + Style.RESET_ALL)
            return False

    def update_variant_stock(self, product_id: int, variant_id: int, stock: int) -> bool:
        try:
            response = requests.put(f"{self.base_url}/products/{product_id}/variants/{variant_id}", headers=self.headers, json={'stock': stock}, timeout=10)
            return response.ok
        except Exception as e:
            print(Fore.RED + f"Error actualizando stock para variante {variant_id}: {e}" + Style.RESET_ALL)
            return False

    def update_product_visibility(self, product_id: int, published: bool) -> bool:
        try:
            response = requests.put(f"{self.base_url}/products/{product_id}", headers=self.headers, json={'published': published}, timeout=10)
            return response.ok
        except Exception as e:
            print(Fore.RED + f"Error actualizando visibilidad de producto {product_id}: {e}" + Style.RESET_ALL)
            return False
            
    def get_all_products(self) -> List[Dict]:
        tiendanube_products = []
        page = 1
        per_page = 200
        while True:
            url = f"{self.base_url}/products?page={page}&per_page={per_page}"
            response = requests.get(url, headers=self.headers, timeout=15)
            response.raise_for_status()
            page_products = response.json()
            if not page_products:
                break
            tiendanube_products.extend(page_products)
            if len(page_products) < per_page:
                break
            page += 1
        return tiendanube_products
