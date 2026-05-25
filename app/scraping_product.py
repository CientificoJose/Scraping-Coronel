from .deepseek import obtener_dimensiones_producto
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time
import re
import os
import requests
from urllib.parse import urlparse
import openpyxl
import sqlite3
from contextlib import closing
from config import DOWNLOAD_IMAGES, set_download_images
from colorama import Fore, Style
import urllib3

# Desactivar advertencias de solicitud insegura para solicitudes sin verificación SSL
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)    




def formatear_codigo(codigo):
    if not codigo:
        return codigo
    # Separar la variante si ya tiene un guion (ej: COR278305-LLAMA)
    partes = codigo.split('-', 1)
    base = partes[0]
    variante = f"-{partes[1]}" if len(partes) > 1 else ""
    
    # Insertar el guion entre las letras y el número de la base (ej: COR278305 -> COR-278305)
    match = re.match(r"^([a-zA-Z]+)(\d+.*)$", base)
    if match:
        prefijo, numero = match.groups()
        return f"{prefijo}-{numero}{variante}"
    return codigo

def obtener_codigo_barra(code, db_path):
    """Consulta rápida a SQLite"""
    try:
        with closing(sqlite3.connect(db_path)) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT codigo_barra FROM productos WHERE codigo = ?",
                (code.strip(),)
            )
            result = cursor.fetchone()
            return result[0] if result else ""
    except Exception as e:
        print(f"Error consultando SQLite: {str(e)}")
        return ""

def inicializar_bd(excel_path='productos_coronel'):
    """Convierte el Excel más reciente a SQLite para consultas rápidas"""
    try:
        # 1. Configurar rutas
        base_dir = os.path.dirname(os.path.dirname(__file__))
        excel_dir = os.path.join(base_dir, excel_path)
        db_path = os.path.join(base_dir, 'productos.db')
        
        # 2. Buscar Excel más reciente
        archivos = [f for f in os.listdir(excel_dir) if f.lower().endswith('.xlsx')]
        if not archivos:
            return None
            
        archivo_reciente = max(archivos, key=lambda f: os.path.getmtime(os.path.join(excel_dir, f)))
        ruta_excel = os.path.join(excel_dir, archivo_reciente)
        
        # 3. Crear/actualizar SQLite
        with closing(sqlite3.connect(db_path)) as conn:
            cursor = conn.cursor()
            
            # Crear tabla con todas las columnas necesarias
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS productos (
                    codigo TEXT PRIMARY KEY,
                    codigo_barra TEXT,
                    descripcion TEXT,
                    precio TEXT,
                    imagen_url TEXT,
                    imagen_local TEXT,
                    variante TEXT,
                    categoria TEXT,
                    subcategoria TEXT,
                    peso_kg TEXT,
                    ancho_cm TEXT,
                    alto_cm TEXT,
                    profundidad_cm TEXT
                )
            ''')
            
            # Cargar datos desde Excel
            wb = openpyxl.load_workbook(ruta_excel)
            ws = wb.active
            
            # Limpiar datos existentes
            cursor.execute("DELETE FROM productos")
            #print(f"Se borro todo de la base de datos")
            
            
            # Insertar nuevos datos (solo código y código de barras del Excel)
            for row in range(2, ws.max_row + 1):
                codigo = str(ws.cell(row=row, column=1).value).strip().replace(" ", "")  # Columna A: Código
                codigo_barra = str(ws.cell(row=row, column=3).value).strip()  # Columna C: C.Barra
                
                if codigo:
                    cursor.execute(
                        "INSERT OR REPLACE INTO productos (codigo, codigo_barra) VALUES (?, ?)",
                        (codigo, codigo_barra)
                    )
            
            conn.commit()
            
            # Hacer la variable db_path accesible globalmente
            DB_PATH = db_path
            
            return db_path
        
    except Exception as e:
        print(f"Error inicializando SQLite: {str(e)}")
        return None

def consolidar_todo_en_base_de_datos(todos_los_productos):
    """
    Guarda todos los datos de productos en la base de datos SQLite
    
    Args:
        todos_los_productos: Lista de diccionarios con los datos de los productos
    """
    try:
        if not hasattr(scraping_product, 'db_path') or not scraping_product.db_path:
            scraping_product.db_path = inicializar_bd()
            
        if not scraping_product.db_path:
            print("Error: No se pudo inicializar la base de datos")
            return False
            
        with closing(sqlite3.connect(scraping_product.db_path)) as conn:
            cursor = conn.cursor()
            
            # 1. Insertar/actualizar productos
            for producto in todos_los_productos:
                codigo = producto.get('codigo', '')
                
                # Si el código contiene guion, siempre INSERT (nuevo producto)
                if '-' in codigo:
                    cursor.execute("""
                        INSERT INTO productos (
                            codigo, codigo_barra, descripcion, precio, 
                            imagen_url, imagen_local, variante, categoria, subcategoria,
                            peso_kg, ancho_cm, alto_cm, profundidad_cm
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        codigo,
                        producto.get('codigo_de_barras', ''),
                        producto.get('descripcion', ''),
                        producto.get('precio', ''),
                        producto.get('imagen_url', ''),
                        producto.get('imagen_local', ''),
                        producto.get('variante', ''),
                        producto.get('categoria', ''),
                        producto.get('subcategoria', ''),
                        producto.get('peso_kg', ''),
                        producto.get('ancho_cm', ''),
                        producto.get('alto_cm', ''),
                        producto.get('profundidad_cm', '')
                    ))
                else:
                    # Para códigos sin guion, mantener lógica de INSERT OR REPLACE
                    cursor.execute("""
                        INSERT OR REPLACE INTO productos (
                            codigo, codigo_barra, descripcion, precio, 
                            imagen_url, imagen_local, variante, categoria, subcategoria,
                            peso_kg, ancho_cm, alto_cm, profundidad_cm
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        codigo,
                        producto.get('codigo_de_barras', ''),
                        producto.get('descripcion', ''),
                        producto.get('precio', ''),
                        producto.get('imagen_url', ''),
                        producto.get('imagen_local', ''),
                        producto.get('variante', ''),
                        producto.get('categoria', ''),
                        producto.get('subcategoria', ''),
                        producto.get('peso_kg', ''),
                        producto.get('ancho_cm', ''),
                        producto.get('alto_cm', ''),
                        producto.get('profundidad_cm', '')
                    ))
            
            # 2. Eliminar productos con descripción vacía
            cursor.execute("DELETE FROM productos WHERE descripcion = '' OR descripcion IS NULL")
            deleted_count = cursor.rowcount
            
            conn.commit()
            print(f"Se consolidaron {len(todos_los_productos)} productos en la base de datos")
            # print(f"Se eliminaron {deleted_count} productos con descripción vacía")
            return todos_los_productos
            
    except Exception as e:
        print(f"Error consolidando productos en SQLite: {str(e)}")
        return False
    
def scraping_product(driver, max_retries=3, wait_time=10):
    """
    Extrae información de productos directamente desde el listado sin navegar al detalle,
    haciendo el scraping muchísimo más rápido y evitando fallos por cambios de DOM o navegación.
    """
    # 1. Configurar rutas
    base_dir = os.path.dirname(os.path.dirname(__file__))
    img_dir = os.path.join(base_dir, 'img-scraping')
    os.makedirs(img_dir, exist_ok=True)

    # 2. Buscar Excel más reciente e inicializar la base de datos local
    if not hasattr(scraping_product, 'db_path'):
        scraping_product.db_path = inicializar_bd()

    # Esperar a que carguen los productos en el listado
    WebDriverWait(driver, wait_time).until(
        EC.presence_of_element_located((By.CLASS_NAME, "itemsBlock"))
    )
    
    # Extraer categorías (una sola vez por página del listado)
    try:
        breadcrumb = driver.find_element(By.CSS_SELECTOR, ".breadcrumb")
        categorias = [span.text.strip() for span in breadcrumb.find_elements(
            By.CSS_SELECTOR, ".breadcrumb-item.breadcrumb2"
        ) if span.text.strip()]
        categoria_principal = categorias[0] if len(categorias) > 0 else "Sin Categoría"
        subcategoria = categorias[1] if len(categorias) > 1 else ""
    except Exception as e:
        print(f"Advertencia al extraer categorías del breadcrumb: {e}")
        categoria_principal = "Sin Categoría"
        subcategoria = ""
        
    products = []
    
    # Obtener todas las tarjetas de producto en el listado
    product_elements = driver.find_elements(By.CSS_SELECTOR, ".col-art .card-product")
    total_products = len(product_elements)
    
    print(f"{Fore.CYAN}📦 Encontrados {total_products} productos en el listado. Procesando...{Style.RESET_ALL}")
    
    for index, product in enumerate(product_elements):
        try:
            # Hacer scroll hasta el elemento para asegurar carga de imágenes perezosas (lazy load)
            driver.execute_script("arguments[0].scrollIntoView({behavior: 'auto', block: 'center'});", product)
            
            # 1. Extraer código (SKU)
            try:
                code = product.find_element(By.CSS_SELECTOR, ".span-codigo").text.replace("Código: ", "").strip()
            except Exception:
                try:
                    code = product.find_element(By.CSS_SELECTOR, ".codigo").text.replace("Código: ", "").strip()
                except Exception:
                    print(f"{Fore.RED}⚠️ No se pudo obtener el código del producto {index + 1}{Style.RESET_ALL}")
                    continue

            code = formatear_codigo(code)

            # 2. Extraer descripción
            try:
                description = product.find_element(By.CSS_SELECTOR, ".descripcion").text.strip()
            except Exception:
                description = ""

            # 3. Extraer precio (tachado/oferta primero, si no existe el normal)
            try:
                price = product.find_element(By.CSS_SELECTOR, "span.tachado").text.strip()
            except Exception:
                try:
                    price = product.find_element(By.CSS_SELECTOR, "span.sintachar").text.strip()
                except Exception:
                    price = "0"

            # 4. Extraer variante si existe
            variant = ""
            try:
                adicional_element = product.find_element(By.CSS_SELECTOR, ".adicional span")
                adicional_text = adicional_element.text.strip()
                if adicional_text:
                    variant = adicional_text.upper()
                    variant = variant.replace(' ', '').replace('/', '-').replace('\\', '-')
                    # Solo añadir si no está ya en el código
                    if not code.endswith(f"-{variant}"):
                        code = f"{code}-{variant}"
            except Exception:
                pass

            # 5. Extraer URL de la imagen
            try:
                image_element = product.find_element(By.CSS_SELECTOR, ".card-img-top")
                image_url = image_element.get_attribute("src")
            except Exception:
                image_url = ""

            # 6. Descargar imagen localmente si está activado
            img_name = f"{code}.jpg"
            img_path = os.path.join(img_dir, img_name)
            
            if DOWNLOAD_IMAGES and image_url:
                try:
                    # Evitar errores si la imagen es una URL base64/data
                    if not image_url.startswith("data:"):
                        response = requests.get(image_url, stream=True, verify=False, timeout=10)
                        if response.status_code == 200:
                            with open(img_path, 'wb') as f:
                                for chunk in response.iter_content(1024):
                                    f.write(chunk)
                except Exception as img_err:
                    print(f"Advertencia al descargar imagen para {code}: {img_err}")

            # 7. Obtener código de barras del Excel/SQLite si existe
            codigo_barra = obtener_codigo_barra(code, scraping_product.db_path) if scraping_product.db_path else ""

            # Guardar datos estructurados
            product_data = {
                'codigo': code,
                'descripcion': description,
                'precio': price,
                'imagen_url': image_url,
                'imagen_local': f"img-scraping/{img_name}",
                'variante': variant,
                'codigo_de_barras': codigo_barra,
                "categoria": categoria_principal,
                "subcategoria": subcategoria
            }
            products.append(product_data)
            
            # Mostrar progreso con formato
            print(f"{Fore.GREEN}⚡ Procesado {index + 1}/{total_products} {Style.RESET_ALL} | {Fore.CYAN}Código: {code}{Style.RESET_ALL} | Price: {price}")

        except Exception as e:
            print(f"Error al extraer producto individual en índice {index}: {e}")
            continue

    # Categoría completa formateada
    categoria_grupal = categoria_principal
    if subcategoria:
        categoria_grupal += " > " + subcategoria

    return products, categoria_grupal, scraping_product.db_path
