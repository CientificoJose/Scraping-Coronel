from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from app.login import login
from colorama import Fore, Style, init
import pandas as pd
import time
import os
import glob
import sqlite3
import requests
from datetime import datetime

# Configuración de la API de Tiendanube
ACCESS_TOKEN = "cdcad052f53bae4972979dbf6900925d4e9a36dc"
STORE_ID = "5950659"
BASE_URL = f"https://api.tiendanube.com/v1/{STORE_ID}"
headers = {
    "Authentication": f"bearer {ACCESS_TOKEN}",
    "Content-Type": "application/json",
    "User-Agent": "API-KEY (jgstore244@gmail.com)"
}

# Inicializar colorama
init()

# Configurar Chrome
chrome_options = Options()
chrome_options.add_argument('--start-maximized')
chrome_options.add_argument('--disable-extensions')
chrome_options.add_experimental_option('prefs', {
    'download.default_directory': os.path.join(os.path.dirname(__file__), 'productos_coronel'),
    'download.prompt_for_download': False,
    'download.directory_upgrade': True,
    'safebrowsing.enabled': True
})

# Iniciar Chrome
driver = webdriver.Chrome(options=chrome_options)

def scraping_product(driver, max_retries=3, wait_time=10):
    """
    Extrae información de productos y descarga sus imágenes
    """
    # Esperar a que carguen los productos
    WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((By.CLASS_NAME, "itemsBlock"))
    )
    
    products = []
    
    # Obtener la categoría del breadcrumb
    try:
        breadcrumb = driver.find_element(By.CSS_SELECTOR, "#breadcrumb .breadcrumb2")
        categoria = breadcrumb.text.strip()
    except:
        categoria = ""
        print(f"{Fore.RED}⚠️ No se pudo obtener la categoría{Style.RESET_ALL}")
    
    # Obtener todos los productos de una vez
    product_elements = driver.find_elements(By.CSS_SELECTOR, ".col-art .card-product")
    total_products = len(product_elements)
    
    print(f"{Fore.CYAN}📦 Procesando {total_products} productos de la categoría: {categoria}{Style.RESET_ALL}")
    
    for index, product in enumerate(product_elements, 1):
        try:
            # Hacer scroll hasta el elemento
            #driver.execute_script("arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});", product)
            #time.sleep(0.1)
            
            # Obtener el código del producto
            try:
                code_element = product.find_element(By.CSS_SELECTOR, ".span-codigo")
                code = code_element.text.replace("Código: ", "").strip()
            except:
                print(f"{Fore.RED}⚠️ No se pudo obtener el código del producto {index}{Style.RESET_ALL}")
                continue
            
            # Procesar variante (ORO)
            variant = ""
            try:
                adicional_element = product.find_element(By.CSS_SELECTOR, ".adicional span")
                adicional_text = adicional_element.text.strip()
                if adicional_text:
                    # Sanitizar la variante eliminando espacios y caracteres problemáticos
                    variant = adicional_text.upper()
                    variant = variant.replace(' ', '').replace('/', '-').replace('\\', '-')
                    code += f"-{variant}"
            except:
                pass
            
            # Agregar producto a la lista
            product_data = {
                'codigo': code,
                'categoria': categoria,
                'stock': 999999  # Stock "infinito"
            }
            products.append(product_data)
            
            # Mostrar progreso
            print(f"\n{Fore.GREEN}⚡ Producto {index}/{total_products}{Style.RESET_ALL}")
            print(f"{Fore.CYAN}🔍 Código: {Style.RESET_ALL}{code}")
            print(f"{Fore.GREEN} Categoria: {Style.RESET_ALL}{categoria}")
            if variant:
                print(f"{Fore.CYAN}🎨 Variante: {Style.RESET_ALL}{variant}")
            print("-" * 50)
            
        except Exception as e:
            print(f"Error al extraer producto: {e}")
            continue

    
    # Return both products and category
    return products, categoria

def update_tiendanube_stock(scraped_products, categoria):
    """
    Actualiza el stock de los productos en Tienda Nube basado en los productos scrapeados
    y la categoría especificada
    
    Args:
        scraped_products: Lista de productos obtenidos del scraping
        categoria: Categoría de productos a actualizar
    """
    print(Fore.CYAN + f"\nActualizando stock en Tienda Nube para la categoría '{categoria}'..." + Style.RESET_ALL)
    
    try:
        # Obtener todos los productos de Tienda Nube usando paginación
        tiendanube_products = []
        page = 1
        per_page = 200  # Máximo permitido por la API
        
        total_products = 0
        print("Obteniendo productos de Tienda Nube...")
        
        while True:
            # Crear barra de progreso
            progress = f"[{'=' * (page % 10)}{' ' * (9 - (page % 10))}]" 
            print(f"\r📦 Página {page} {progress} ({total_products} productos)", end='', flush=True)
            
            response = requests.get(
                f"{BASE_URL}/products",
                headers=headers,
                params={'page': page, 'per_page': per_page}
            )
            response.raise_for_status()
            
            page_products = response.json()
            if not page_products:  # Si no hay más productos, salimos del bucle
                break
                
            tiendanube_products.extend(page_products)
            total_products += len(page_products)
            
            if len(page_products) < per_page:  # Si la página no está completa, es la última
                break
                
            page += 1
        
        print()  # Nueva línea para separar del siguiente mensaje
        
        print(f"Total de productos obtenidos de Tienda Nube: {len(tiendanube_products)}")
        
        # Crear diccionario de productos scrapeados para búsqueda rápida
        scraped_codes = {p['codigo']: p for p in scraped_products}
        
        # Contador de actualizaciones
        updates = {'infinito': 0, 'cero': 0, 'error': 0, 'omitidos': 0}
        
        # Actualizar stock de cada producto
        for tn_product in tiendanube_products:
            # Verificar si el producto pertenece a la categoría especificada
            product_categories = [cat.get('name', {}).get('es', '') for cat in tn_product.get('categories', [])]
            if categoria not in product_categories:
                updates['omitidos'] += 1
                continue

            product_id = tn_product['id']
            product_name = tn_product.get('name', {}).get('es', 'Producto sin nombre')
            variants = tn_product.get('variants', [])
            
            # Si el producto pertenece a la categoría, debemos procesarlo
            for variant in variants:
                sku = variant.get('sku', '')
                if not sku:
                    continue
                
                # Determinar el nuevo stock basado en si está en el scraping
                if sku in scraped_codes:
                    new_stock = 999999
                    print(f"{Fore.GREEN}✓ Manteniendo stock del producto {product_name} (SKU: {sku}){Style.RESET_ALL}")
                    updates['infinito'] += 1
                else:
                    new_stock = 0
                    print(f"{Fore.YELLOW}⚠️ Estableciendo stock 0 para {product_name} (SKU: {sku}){Style.RESET_ALL}")
                    updates['cero'] += 1
                
                # Actualizar stock en Tienda Nube
                try:
                    update_url = f"{BASE_URL}/products/{product_id}/variants/{variant['id']}"
                    response = requests.put(update_url, headers=headers, json={'stock': new_stock})
                    if response.status_code != 200:
                        print(f"{Fore.RED}Error al actualizar {product_name} (SKU: {sku}): {response.text}{Style.RESET_ALL}")
                        updates['error'] += 1
                except Exception as e:
                    print(f"{Fore.RED}Error al actualizar {product_name} (SKU: {sku}): {e}{Style.RESET_ALL}")
                    updates['error'] += 1
        
        # Mostrar resumen
        print(f"\n{Fore.GREEN}✅ Actualización de stock completada para la categoría '{categoria}':{Style.RESET_ALL}")
        print(f"  • {Fore.GREEN}{updates['infinito']} productos con stock infinito{Style.RESET_ALL}")
        print(f"  • {Fore.YELLOW}{updates['cero']} productos con stock 0{Style.RESET_ALL}")
        print(f"  • {Fore.BLUE}{updates['omitidos']} productos omitidos (otra categoría){Style.RESET_ALL}")
        if updates['error'] > 0:
            print(f"  • {Fore.RED}{updates['error']} errores de actualización{Style.RESET_ALL}")
            
    except Exception as e:
        print(Fore.RED + f"Error al obtener productos de Tienda Nube: {e}" + Style.RESET_ALL)

def scraping_all_product(driver):
    """
    Extrae información de productos de TODAS las páginas disponibles
    
    Args:
        driver: Instancia de Selenium WebDriver
        
    Returns:
        Lista de productos encontrados
    """
    all_products = []
    page_number = 1
    
    while True:
        print(Fore.YELLOW + f"\nProcesando página {page_number}..." + Fore.RESET)
        current_products, categoria = scraping_product(driver)
        
        if not current_products:
            print(Fore.GREEN + "No se encontraron productos - fin del scraping" + Fore.RESET)
            break
            
        all_products.extend(current_products)
        
        try:
            # Preparación y scroll
            current_url = driver.current_url
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            
            # Localizar botón siguiente
            next_button = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.ID, "siguiente"))
            )
            
            if next_button.get_attribute("disabled") is not None:
                print(Fore.GREEN + "✅ Última página alcanzada" + Fore.RESET)
                break
                
            # Intentar cambio de página
            driver.execute_script("arguments[0].click();", next_button)
            time.sleep(2)
            page_number += 1
                
        except Exception as e:
            print(Fore.RED + f"🚨 Error: {str(e)}" + Fore.RESET)
            break
    
    print(Fore.GREEN + f"\nSCRAPING COMPLETADO - {len(all_products)} productos encontrados" + Fore.RESET)
    return all_products, categoria




# Loguearnos
login_result = login(driver, True)
if not login_result:
    print(Fore.RED + "✖ Scraping cancelado por fallo en el login" + Fore.RESET)
    driver.quit()
    exit(1)

# Ejecutar scraping y actualización de stock
products, categoria = scraping_all_product(driver)
if products:
    update_tiendanube_stock(products, categoria)

# Cerrar el navegador
driver.quit()
