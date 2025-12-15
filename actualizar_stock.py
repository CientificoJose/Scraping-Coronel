from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from selenium.common.exceptions import TimeoutException
from app.login import login
from colorama import Fore, Style, init
import pandas as pd
import time
import os
import glob
import sqlite3
import requests
import re
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

LISTING_SELECTOR = (By.CLASS_NAME, "itemsBlock")
NEXT_BUTTON_SELECTOR = (By.ID, "siguiente")

# Configuración de tiempos y reintentos (ajustable para conexiones lentas)
MAX_RETRIES = 5
WAIT_TIME = 20
MIN_EXPECTED_PAGES = 100  # Mínimo de páginas esperadas en el catálogo


def get_current_page_from_url(driver):
    """Extrae el número de página actual de la URL."""
    try:
        url = driver.current_url
        match = re.search(r'page=(\d+)', url)
        if match:
            return int(match.group(1))
    except Exception:
        pass
    return 1


def is_last_page(driver, be_conservative=False):
    """
    Intenta determinar si no quedan más páginas o productos visibles.
    Si be_conservative=True, solo retorna True si estamos SEGUROS de que es la última.
    """
    current_page = get_current_page_from_url(driver)
    
    try:
        next_button = driver.find_element(*NEXT_BUTTON_SELECTOR)
        classes = (next_button.get_attribute("class") or "")
        is_disabled = next_button.get_attribute("disabled") is not None
        is_inactive = "btn-shadow" not in classes
        
        # Si el botón está claramente deshabilitado, es última página
        if is_disabled:
            return True
            
        # Si estamos siendo conservadores y la página es baja, no declarar fin
        if be_conservative and current_page < MIN_EXPECTED_PAGES:
            if is_inactive:
                print(Fore.YELLOW + f"⚠️ Botón inactivo en página {current_page}, pero siendo conservador..." + Style.RESET_ALL)
                return False
                
        if is_inactive:
            return True
            
    except Exception:
        # Si no existe el botón y estamos siendo conservadores, no asumir fin
        if be_conservative and current_page < MIN_EXPECTED_PAGES:
            return False
        return True

    try:
        if not driver.find_elements(By.CSS_SELECTOR, ".col-art .card-product"):
            # Si no hay productos pero estamos en página baja, puede ser carga lenta
            if be_conservative and current_page < MIN_EXPECTED_PAGES:
                return False
            return True
    except Exception:
        pass
    return False


def wait_for_listing(driver, wait_time=WAIT_TIME, max_retries=MAX_RETRIES):
    """Asegura que el listado de productos esté presente con reintentos."""
    last_exception = None
    current_page = get_current_page_from_url(driver)
    
    for attempt in range(1, max_retries + 1):
        try:
            WebDriverWait(driver, wait_time).until(
                EC.presence_of_element_located(LISTING_SELECTOR)
            )
            return True
        except TimeoutException as exc:
            last_exception = exc
            
            # Ser conservador en páginas bajas para evitar falsos positivos
            be_conservative = (attempt < max_retries) and (current_page < MIN_EXPECTED_PAGES)
            
            if is_last_page(driver, be_conservative=be_conservative):
                # Doble verificación: si estamos en página baja, intentar navegar directamente
                if current_page < MIN_EXPECTED_PAGES and attempt < max_retries:
                    print(
                        Fore.YELLOW
                        + f"⚠️ Posible falso positivo en página {current_page}. Intentando navegación directa..."
                        + Style.RESET_ALL
                    )
                    next_page = current_page + 1
                    driver.get(f"https://www.coronelmayorista.com/#/articulos?page={next_page}&ORDER=ORD%3DASC&VIEW_TYPE=GRID_VI")
                    time.sleep(3)
                    continue
                    
                print(Fore.GREEN + f"✅ Catálogo sin más productos visibles (página {current_page})." + Style.RESET_ALL)
                return False
                
            print(
                Fore.YELLOW
                + f"⚠️ Lista de productos no cargó (intento {attempt}/{max_retries}, página {current_page}). Reintentando..."
                + Style.RESET_ALL
            )
            time.sleep(3)
            driver.refresh()
            time.sleep(2)

    # Último intento: navegación directa a la siguiente página
    if current_page < MIN_EXPECTED_PAGES:
        print(
            Fore.YELLOW
            + f"⚠️ Agotados reintentos en página {current_page}. Último intento con navegación directa..."
            + Style.RESET_ALL
        )
        next_page = current_page + 1
        driver.get(f"https://www.coronelmayorista.com/#/articulos?page={next_page}&ORDER=ORD%3DASC&VIEW_TYPE=GRID_VI")
        time.sleep(5)
        try:
            WebDriverWait(driver, wait_time).until(
                EC.presence_of_element_located(LISTING_SELECTOR)
            )
            return True
        except TimeoutException:
            pass

    if last_exception:
        raise last_exception
    return False

def scraping_product(driver, max_retries=MAX_RETRIES, wait_time=WAIT_TIME):
    """
    Extrae información de productos
    """
    
    # Esperar a que carguen los productos con reintentos controlados
    try:
        listing_ready = wait_for_listing(driver, wait_time=wait_time, max_retries=max_retries)
    except TimeoutException as exc:
        current_page = get_current_page_from_url(driver)
        print(Fore.RED + f"✖ No se pudo preparar la página {current_page}: {exc}" + Style.RESET_ALL)
        return [], ""

    if not listing_ready:
        # No hay más productos para procesar
        return [], ""
    
    products = []
    
    # Obtener la categoría del breadcrumb
    try:
        breadcrumb = driver.find_element(By.CSS_SELECTOR, "#breadcrumb .breadcrumb2")
        categoria = breadcrumb.text.strip()
    except:
        categoria = ""
        #print(f"{Fore.RED}⚠️ No se pudo obtener la categoría{Style.RESET_ALL}")
    
    # Obtener todos los productos de una vez
    product_elements = driver.find_elements(By.CSS_SELECTOR, ".col-art .card-product")
    total_products = len(product_elements)
    
    print(f"{Fore.CYAN}📦 Procesando {total_products} productos{Style.RESET_ALL}")
    
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
            if variant:
                print(f"{Fore.CYAN}🎨 Variante: {Style.RESET_ALL}{variant}")
            print("-" * 50)
            
        except Exception as e:
            print(f"Error al extraer producto: {e}")
            continue

    
    # Return both products and category
    return products, categoria

def update_tiendanube_stock(scraped_products):
    """
    Actualiza el stock y la visibilidad de los productos en Tienda Nube.
    - Si un producto existe en el scraping, su stock se establece en 999999.
    - Si no existe, su stock se establece en 0.
    - Los productos cuyo SKU termina en '-local' se omiten.
    - Un producto se oculta (published=False) si todas sus variantes tienen stock 0.
    """
    print(Fore.CYAN + "\n🔄 Actualizando stock y visibilidad en Tienda Nube..." + Style.RESET_ALL)

    try:
        # 1. Obtener todos los productos de Tienda Nube
        tiendanube_products = []
        page = 1
        per_page = 200
        total_products = 0
        print("Obteniendo productos de Tienda Nube...")
        while True:
            progress = f"[{'=' * (page % 10)}{' ' * (9 - (page % 10))}]"
            print(f"\r📦 Página {page} {progress} ({total_products} productos)", end='', flush=True)
            response = requests.get(f"{BASE_URL}/products", headers=headers, params={'page': page, 'per_page': per_page})
            response.raise_for_status()
            page_products = response.json()
            if not page_products:
                break
            tiendanube_products.extend(page_products)
            total_products += len(page_products)
            if len(page_products) < per_page:
                break
            page += 1
        print(f"\nTotal de productos obtenidos: {len(tiendanube_products)}")

        # 2. Preparar datos y contadores
        scraped_codes = {p['codigo']: p for p in scraped_products}
        updates = {'infinito': 0, 'cero': 0, 'visibles': 0, 'ocultos': 0, 'error': 0}

        # 3. Procesar cada producto
        for tn_product in tiendanube_products:
            product_id = tn_product['id']
            product_name = tn_product.get('name', {}).get('es', 'Sin nombre')
            variants = tn_product.get('variants', [])
            product_published = tn_product.get('published', True)
            
            product_has_stock = False

            # Actualizar stock de variantes
            for variant in variants:
                sku = variant.get('sku', '')
                if not sku:
                    continue

                if sku.endswith('-local'):
                    print(f"{Fore.BLUE}ℹ️  Omitiendo producto local: {product_name} (SKU: {sku}){Style.RESET_ALL}")
                    product_has_stock = True  # Asumimos que los locales siempre tienen stock para la visibilidad
                    continue

                new_stock = 999999 if sku in scraped_codes else 0
                if new_stock > 0:
                    product_has_stock = True
                    updates['infinito'] += 1
                    print(f"{Fore.GREEN}✓ Stock infinito para {product_name} (SKU: {sku}){Style.RESET_ALL}")
                else:
                    updates['cero'] += 1
                    print(f"{Fore.YELLOW}⚠️ Stock 0 para {product_name} (SKU: {sku}){Style.RESET_ALL}")
                
                # Actualizar stock en la API
                try:
                    update_url = f"{BASE_URL}/products/{product_id}/variants/{variant['id']}"
                    response = requests.put(update_url, headers=headers, json={'stock': new_stock}, timeout=10)
                    response.raise_for_status()
                except requests.exceptions.RequestException as e:
                    updates['error'] += 1
                    print(f"{Fore.RED}❌ Error actualizando stock de {product_name} (SKU: {sku}): {e}{Style.RESET_ALL}")
                time.sleep(0.5)

            # Actualizar visibilidad del producto principal
            should_be_published = product_has_stock
            if product_published != should_be_published:
                try:
                    update_url = f"{BASE_URL}/products/{product_id}"
                    response = requests.put(update_url, headers=headers, json={'published': should_be_published}, timeout=10)
                    response.raise_for_status()
                    if should_be_published:
                        updates['visibles'] += 1
                        print(f"{Fore.GREEN}🟢 Producto '{product_name}' ahora visible.{Style.RESET_ALL}")
                    else:
                        updates['ocultos'] += 1
                        print(f"{Fore.RED}🔴 Producto '{product_name}' ahora oculto.{Style.RESET_ALL}")
                except requests.exceptions.RequestException as e:
                    updates['error'] += 1
                    print(f"{Fore.RED}❌ Error actualizando visibilidad de {product_name}: {e}{Style.RESET_ALL}")
            else:
                 print(f"{Fore.WHITE}⚪ Visibilidad de '{product_name}' no cambia.{Style.RESET_ALL}")

        # 4. Mostrar resumen
        print(f"\n{Fore.GREEN}✅ Actualización completada:{Style.RESET_ALL}")
        print(f"  - {updates['infinito']} variantes con stock infinito.")
        print(f"  - {updates['cero']} variantes con stock cero.")
        print(f"  - {updates['visibles']} productos se hicieron visibles.")
        print(f"  - {updates['ocultos']} productos se ocultaron.")
        if updates['error'] > 0:
            print(f"  - {Fore.RED}{updates['error']} errores de actualización.{Style.RESET_ALL}")

    except Exception as e:
        print(Fore.RED + f"Error general en la actualización: {e}" + Style.RESET_ALL)

def scraping_all_product(driver):
    """
    Extrae información de productos de TODAS las páginas disponibles
    
    Args:
        driver: Instancia de Selenium WebDriver
        
    Returns:
        Lista de productos encontrados
    """
    print(Fore.YELLOW + "\nNavegando a la lista de precios..." + Fore.RESET)
    driver.get("https://www.coronelmayorista.com/#/articulos?page=1&ORDER=ORD%3DASC&VIEW_TYPE=GRID_VI")
    time.sleep(2)
    
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
    driver.quit()
    return all_products, categoria




# Loguearnos
login_result = login(driver, True)
if not login_result:
    print(Fore.RED + "✖ Scraping cancelado por fallo en el login" + Fore.RESET)
    driver.quit()
    exit(1)

# Ejecutar scraping y actualización de stock
products, _ = scraping_all_product(driver)
if products:
    update_tiendanube_stock(products)

# Cerrar el navegador
driver.quit()
