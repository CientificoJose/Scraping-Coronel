from .deepseek import obtener_dimensiones_producto
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time
import os
import requests
from urllib.parse import urlparse
import openpyxl
import sqlite3
from contextlib import closing

# Variables globales
global DB_PATH


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
            return True
            
    except Exception as e:
        print(f"Error consolidando productos en SQLite: {str(e)}")
        return False
    
def scraping_product(driver):
    """
    Extrae información de productos y descarga sus imágenes
    """
    # 1. Configurar rutas
    base_dir = os.path.dirname(os.path.dirname(__file__))
    img_dir = os.path.join(base_dir, 'img-scraping')
    excel_dir = os.path.join(base_dir, 'productos_coronel')
    os.makedirs(img_dir, exist_ok=True)

    # 2. Buscar Excel más reciente
    if not hasattr(scraping_product, 'db_path'):
        scraping_product.db_path = inicializar_bd()



    # Esperar a que carguen los productos
    WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((By.CLASS_NAME, "itemsBlock"))
    )
    
    products = []
    
    # Extracción mejorada de categorías
    breadcrumb = driver.find_element(By.CSS_SELECTOR, ".breadcrumb")
    categorias = [span.text.strip() for span in breadcrumb.find_elements(
            By.CSS_SELECTOR, ".breadcrumb-item.breadcrumb2"
        ) if span.text.strip()]
        
    # Asignación de categorías
    categoria_principal = categorias[0] if len(categorias) > 0 else None

    # Unir todas las subcategorías (si hay más de una) separadas por comas
    subcategoria = ", ".join(categorias[1:]) if len(categorias) > 1 else ""
    
    
    
    product_elements = driver.find_elements(By.CSS_SELECTOR, ".col-art .card-product")
    
    for product in product_elements:
        try:
            # Extraer información base
            code = product.find_element(By.CLASS_NAME, "span-codigo").text.replace("Código: ", "")
            codigo_sin_variante = code
            description = product.find_element(By.CLASS_NAME, "span-3").text
            try:
                price = product.find_element(By.CLASS_NAME, "sintachar").text.strip()
            except:
                price = product.find_element(By.CLASS_NAME, "tachado").text.strip()
            image_url = product.find_element(By.CSS_SELECTOR, ".img-wrap img").get_attribute("src")
            
            # Procesar variante
            variant = ""
            try:
                adicional_element = product.find_element(By.CSS_SELECTOR, ".adicional span")
                adicional_text = adicional_element.text.strip()
                if adicional_text:
                    variant = f"-{adicional_text.upper().replace(' ', '')}"
                    code += variant
            except:
                pass
            
            # Descargar imagen
            try:
                img_name = f"{code}.jpg"
                img_path = os.path.join(img_dir, img_name)
                
                response = requests.get(image_url, stream=True)
                if response.status_code == 200:
                    with open(img_path, 'wb') as f:
                        for chunk in response.iter_content(1024):
                            f.write(chunk)
            except Exception as e:
                print(f"Error descargando imagen {code}: {e}")

            # Obtener código de barras si existe Excel
            codigo_barra = obtener_codigo_barra(codigo_sin_variante, scraping_product.db_path) if scraping_product.db_path else ""
            
            products.append({
                'codigo': code,
                'descripcion': description,
                'precio': price,
                'imagen_url': image_url,
                'imagen_local': f"img-scraping/{img_name}",
                'variante': variant.replace('-', '') if variant else None,
                'codigo_de_barras': codigo_barra,
                "categoria": categoria_principal,
                "subcategoria": subcategoria
            })
            
        except Exception as e:
            print(f"Error al extraer producto: {e}")
            continue
    
    # Crear categorías si no existen
    categoria_grupal = categoria_principal + " > " + subcategoria 
    
    # Return both products and category
    return products, categoria_grupal, scraping_product.db_path
