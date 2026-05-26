from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from selenium.common.exceptions import TimeoutException
from app.login import login
from api_tiendanube import client
from colorama import Fore, Style, init
from app.core.browser import get_chrome_driver
import pandas as pd
import time
import os
import glob
import sqlite3
import requests
import re
from datetime import datetime
# El stock y visibilidad se actualizan mediante el cliente centralizado importado de api_tiendanube.py



# Inicializar colorama
init()

def formatear_codigo(codigo):
    if not codigo:
        return codigo
    partes = codigo.split('-', 1)
    base = partes[0]
    variante = f"-{partes[1]}" if len(partes) > 1 else ""
    
    match = re.match(r"^([a-zA-Z]+)(\d+.*)$", base)
    if match:
        prefijo, numero = match.groups()
        return f"{prefijo}-{numero}{variante}"
    return codigo

# Iniciar Chrome centralizado
# El driver se inicializa localmente en run_stock()


LISTING_SELECTOR = (By.CLASS_NAME, "itemsBlock")
NEXT_BUTTON_SELECTOR = (By.ID, "siguiente")

# Configuración de tiempos y reintentos (ajustable para conexiones lentas)
MAX_RETRIES = 7
WAIT_TIME = 25
MIN_EXPECTED_PAGES = 680  # Mínimo de páginas esperadas en el catálogo
LOADING_SELECTOR = (By.CSS_SELECTOR, ".loading, .spinner, .loader, [class*='loading'], [class*='spinner']")


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


def wait_for_page_ready(driver, timeout=10):
    """
    Espera a que la página esté lista: sin spinners/loading activos.
    Retorna True si la página parece lista, False si hay timeout.
    """
    try:
        # Esperar a que desaparezca cualquier indicador de loading
        WebDriverWait(driver, timeout).until_not(
            EC.presence_of_element_located(LOADING_SELECTOR)
        )
    except TimeoutException:
        # Si el loading no desaparece, puede que no exista o esté atascado
        pass
    except Exception:
        pass
    
    # Esperar a que el documento esté completo
    try:
        WebDriverWait(driver, timeout).until(
            lambda d: d.execute_script("return document.readyState") == "complete"
        )
    except Exception:
        pass
    
    # Pequeña pausa adicional para que Angular/JS termine de renderizar
    time.sleep(1)
    return True


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
    """
    Asegura que el listado de productos esté presente con reintentos.
    Si estamos en página < MIN_EXPECTED_PAGES, los reintentos son INFINITOS.
    """
    last_exception = None
    current_page = get_current_page_from_url(driver)
    attempt = 0
    consecutive_failures = 0
    
    while True:
        attempt += 1
        
        # Primero esperar a que la página esté lista (sin loading)
        wait_for_page_ready(driver, timeout=10)
        
        try:
            WebDriverWait(driver, wait_time).until(
                EC.presence_of_element_located(LISTING_SELECTOR)
            )
            return True
        except TimeoutException as exc:
            last_exception = exc
            consecutive_failures += 1
            
            # Obtener página actual actualizada
            current_page = get_current_page_from_url(driver)
            
            # Si estamos en página >= MIN_EXPECTED_PAGES, aplicar límite de reintentos
            if current_page >= MIN_EXPECTED_PAGES:
                if is_last_page(driver, be_conservative=False):
                    print(Fore.GREEN + f"✅ Catálogo sin más productos visibles (página {current_page})." + Style.RESET_ALL)
                    return False
                if attempt >= max_retries:
                    if last_exception:
                        raise last_exception
                    return False
            
            # Estrategia de recuperación según número de fallos consecutivos
            if consecutive_failures <= 3:
                # Primeros intentos: refresh simple
                print(
                    Fore.YELLOW
                    + f"⚠️ Lista no cargó (intento {attempt}, página {current_page}). Refresh..."
                    + Style.RESET_ALL
                )
                time.sleep(3)
                driver.refresh()
                time.sleep(2)
                
            elif consecutive_failures <= 6:
                # Intentos medios: navegación directa a la misma página
                print(
                    Fore.YELLOW
                    + f"⚠️ Reintentando página {current_page} con navegación directa (intento {attempt})..."
                    + Style.RESET_ALL
                )
                driver.get(f"https://www.coronelmayorista.com/#/articulos?page={current_page}&ORDER=ORD%3DASC&VIEW_TYPE=GRID_VI")
                time.sleep(5)
                wait_for_page_ready(driver, timeout=15)
                
            else:
                # Muchos fallos: saltar a la siguiente página
                print(
                    Fore.YELLOW
                    + f"⚠️ Demasiados fallos en página {current_page}. Saltando a página {current_page + 1} (intento {attempt})..."
                    + Style.RESET_ALL
                )
                current_page += 1
                driver.get(f"https://www.coronelmayorista.com/#/articulos?page={current_page}&ORDER=ORD%3DASC&VIEW_TYPE=GRID_VI")
                time.sleep(6)
                wait_for_page_ready(driver, timeout=15)
                consecutive_failures = 0  # Reset para la nueva página

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
            
            code = formatear_codigo(code)
            
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
        # 1. Obtener todos los productos de Tienda Nube usando el cliente
        print("Obteniendo productos de Tienda Nube...")
        tiendanube_products = client.get_all_products()
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
                
                # Actualizar stock usando el cliente centralizado
                success = client.update_variant_stock(product_id, variant['id'], new_stock)
                if not success:
                    updates['error'] += 1
                    print(f"{Fore.RED}❌ Error actualizando stock de {product_name} (SKU: {sku}){Style.RESET_ALL}")
                time.sleep(0.5)

            # Actualizar visibilidad del producto principal
            should_be_published = product_has_stock
            if product_published != should_be_published:
                success = client.update_product_visibility(product_id, should_be_published)
                if success:
                    if should_be_published:
                        updates['visibles'] += 1
                        print(f"{Fore.GREEN}🟢 Producto '{product_name}' ahora visible.{Style.RESET_ALL}")
                    else:
                        updates['ocultos'] += 1
                        print(f"{Fore.RED}🔴 Producto '{product_name}' ahora oculto.{Style.RESET_ALL}")
                else:
                    updates['error'] += 1
                    print(f"{Fore.RED}❌ Error actualizando visibilidad de {product_name}{Style.RESET_ALL}")
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




def run_stock():
    # Iniciar Chrome centralizado
    driver = get_chrome_driver()
    try:
        # Loguearnos
        login_result = login(driver, True)
        if not login_result:
            print(Fore.RED + "✖ Scraping cancelado por fallo en el login" + Fore.RESET)
            driver.quit()
            return False

        # Ejecutar scraping y actualización de stock
        products, _ = scraping_all_product(driver)
        if products:
            update_tiendanube_stock(products)
            return True
        return False
    except Exception as e:
        print(Fore.RED + f"Error durante la actualización de stock: {e}" + Fore.RESET)
        try:
            driver.quit()
        except:
            pass
        return False

if __name__ == "__main__":
    run_stock()

