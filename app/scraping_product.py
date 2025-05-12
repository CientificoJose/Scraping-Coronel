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
from config import DOWNLOAD_IMAGES, set_download_images




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
    
    product_elements = driver.find_elements(By.CSS_SELECTOR, ".col-art .card-product")
    
    for index in range(len(product_elements)):
        try:
            # Re-obtener los elementos de producto después de regresar
            product_elements = driver.find_elements(By.CSS_SELECTOR, ".col-art .card-product")
            product = product_elements[index]
            
            # Hacer scroll hasta el elemento
            driver.execute_script("arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});", product)
            time.sleep(0.5)  # Pequeña pausa para que termine el scroll
            
            # Esperar a que el elemento sea clickeable
            WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, ".col-art .card-product"))
            )
            
            # Intentar hacer click con JavaScript si el click normal falla
            try:
                product.click()
            except:
                driver.execute_script("arguments[0].click();", product)
            
            # Esperar a que la página de detalle cargue completamente
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.CLASS_NAME, "precios"))
            )
            
            # Extraer información de la página de detalle
            try:
                # Primero intentamos encontrar el precio sin tachar
                sintachar_element = driver.find_element(By.CLASS_NAME, "sintachar")
                if sintachar_element and sintachar_element.text.strip():
                    price = sintachar_element.text.strip()
                else:
                    # Si no hay precio sin tachar o está vacío, buscamos el tachado
                    price = driver.find_element(By.CLASS_NAME, "tachado").text.strip()
            except Exception as e:
                # Si no se encuentra ninguno de los dos precios, intentamos otras alternativas
                try:
                    price = driver.find_element(By.CLASS_NAME, "precios").text.strip()
                except:
                    print("No se pudo encontrar el precio para el producto")
                    price = "0"  # Valor por defecto si no se encuentra ningún precio
            
            try:
                code = driver.find_element(By.CLASS_NAME, "codigo").text.replace("Código: ", "")
            except Exception as e:
                print(f"Error al extraer código: {e}")
                code = ""
            
            description = driver.find_element(By.CLASS_NAME, "description").text
            
            # Extraer categorías
            breadcrumb = driver.find_element(By.CSS_SELECTOR, ".breadcrumb")
            categorias = [span.text.strip() for span in breadcrumb.find_elements(
                    By.CSS_SELECTOR, ".breadcrumb-item.breadcrumb2"
                ) if span.text.strip()]
            
            categoria_principal = categorias[0] if len(categorias) > 0 else None
            subcategoria = ", ".join(categorias[1:]) if len(categorias) > 1 else ""
            
            # Procesar variante
            variant = ""
            try:
                adicional_element = driver.find_element(By.CLASS_NAME, "adicional")
                adicional_text = adicional_element.text.strip()
                if adicional_text:
                    variant = adicional_text.upper().replace(' ', '')
                    code += f"-{variant}"
            except:
                pass
            
            # Extraer imagen
            image_url = driver.find_element(By.CLASS_NAME, "ngxImageZoomThumbnail").get_attribute("src")
            
            # Preparar nombre de imagen
            img_name = f"{code}.jpg"
            img_path = os.path.join(img_dir, img_name)
            
            # Descargar imagen solo si DOWNLOAD_IMAGES es True
            if DOWNLOAD_IMAGES:
                response = requests.get(image_url, stream=True)
                if response.status_code == 200:
                    with open(img_path, 'wb') as f:
                        for chunk in response.iter_content(1024):
                            f.write(chunk)

            # Obtener código de barras si existe Excel
            codigo_barra = obtener_codigo_barra(code, scraping_product.db_path) if scraping_product.db_path else ""
            
            products.append({
                'codigo': code,
                'descripcion': description,
                'precio': price,
                'imagen_url': image_url,
                'imagen_local': f"img-scraping/{img_name}",
                'variante': variant,
                'codigo_de_barras': codigo_barra,
                "categoria": categoria_principal,
                "subcategoria": subcategoria
            })
            
            # Regresar a la página de listado
            driver.back()
            
            # Esperar a que los productos vuelvan a cargar
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.CLASS_NAME, "itemsBlock"))
            )
            
        except Exception as e:
            print(f"Error al extraer producto: {e}")
            continue
    
    # Crear categorías si no existen
    categoria_grupal = categoria_principal + " > " + subcategoria 
    
    # Return both products and category
    return products, categoria_grupal, scraping_product.db_path
