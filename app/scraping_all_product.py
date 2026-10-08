from colorama import Fore, Style
from .scraping_product import scraping_product
from app.core.logger import registrar_error
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time

def boton_esta_deshabilitado(btn):
    """
    Verifica con precisión si el botón 'siguiente' está verdaderamente deshabilitado
    o inactivo en la aplicación web Angular de Coronel Mayorista.
    """
    try:
        # 1. Chequeo de la propiedad nativa de Selenium
        if not btn.is_enabled():
            return True
        
        # 2. Atributo disabled en el DOM
        dis_attr = btn.get_attribute("disabled")
        if dis_attr is not None and str(dis_attr).strip().lower() in ["true", "disabled", ""]:
            return True
            
        # 3. Clase 'disabled' explícita
        classes = (btn.get_attribute("class") or "").lower()
        if "disabled" in classes:
            return True
            
        # 4. En Coronel Mayorista, los botones activos poseen la clase 'btn-shadow'
        if "btn-shadow" not in classes:
            return True
            
        return False
    except Exception:
        return True

def scraping_all_product(driver):
    """
    Extrae información de productos de TODAS las páginas disponibles con verificación robusta
    anti-falsos positivos en el botón de paginación 'siguiente'.
    
    Args:
        driver: Instancia de Selenium WebDriver
        
    Returns:
        Lista de diccionarios con información de todos los productos y categoría
    """
    all_products = []
    categoria = None
    page_number = 1
    
    while True:
        print(Fore.YELLOW + f"\nProcesando página {page_number}..." + Fore.RESET)
        current_products, categoria, db_path = scraping_product(driver)
        
        if not current_products:
            print(Fore.GREEN + "No se encontraron productos - fin del scraping" + Fore.RESET)
            break
            
        all_products.extend(current_products)
        
        try:
            current_url = driver.current_url
            boton_siguiente = None
            
            # Reintentar hasta 4 veces la verificación del botón siguiente para evitar
            # falsos positivos causados por retardos de scroll o renderizado en Angular
            for intento_check in range(4):
                try:
                    # 1. Scroll al fondo de la página
                    driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                    time.sleep(0.8)
                    
                    # 2. Localizar botón 'siguiente'
                    btn = WebDriverWait(driver, 8).until(
                        EC.presence_of_element_located((By.ID, "siguiente"))
                    )
                    
                    # 3. Scroll enfocado directo al botón para forzar a Angular a evaluar su estado
                    driver.execute_script("arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});", btn)
                    time.sleep(0.8)
                    
                    # 4. Re-obtener referencia fresca
                    btn = driver.find_element(By.ID, "siguiente")
                    
                    if boton_esta_deshabilitado(btn):
                        print(Fore.YELLOW + f"⏳ Comprobando botón siguiente (intento {intento_check + 1}/4): parece deshabilitado, re-verificando..." + Fore.RESET)
                        time.sleep(1.5)
                        continue
                    else:
                        # Botón confirmado activo
                        boton_siguiente = btn
                        break
                except Exception:
                    time.sleep(1)
            
            if boton_siguiente is None:
                print(Fore.GREEN + "✅ Botón siguiente confirmado como DESHABILITADO tras múltiples verificaciones - última página alcanzada." + Fore.RESET)
                break
                
            # Avanzar a la siguiente página
            print(Fore.CYAN + f"➡ Avanzando a la página {page_number + 1}..." + Fore.RESET)
            try:
                driver.execute_script("arguments[0].click();", boton_siguiente)
            except Exception:
                boton_siguiente.click()
            
            # Esperar cambio de página de forma robusta
            try:
                first_sku = current_products[0]['codigo'] if current_products else None
                
                def next_page_loaded(d):
                    if d.current_url != current_url:
                        return True
                    try:
                        new_first_product = d.find_element(By.CSS_SELECTOR, ".col-art .card-product")
                        new_sku = new_first_product.find_element(By.CSS_SELECTOR, ".span-codigo").text.replace("Código: ", "").strip()
                        return new_sku != first_sku
                    except Exception:
                        return False

                WebDriverWait(driver, 14).until(next_page_loaded)
                time.sleep(1.5)  # Estabilización tras cargar la nueva página
                page_number += 1
            except Exception:
                print(Fore.YELLOW + "⚠️ Tiempo de espera de cambio de página superado, verificando si cargaron productos..." + Fore.RESET)
                time.sleep(2)
                cards = driver.find_elements(By.CSS_SELECTOR, ".col-art .card-product")
                if cards:
                    page_number += 1
                else:
                    print(Fore.RED + "❌ No se detectaron productos nuevos en la siguiente página - finalizando scraping." + Fore.RESET)
                    break
                
        except Exception as e:
            print(Fore.RED + f"🚨 Error crítico en paginación: {str(e)}" + Fore.RESET)
            registrar_error("Error crítico en paginación de scraping", e)
            print(Fore.YELLOW + "Terminando scraping por seguridad" + Fore.RESET)
            break
            
    print(Fore.GREEN + f"\nSCRAPING COMPLETADO - {len(all_products)} productos recolectados en total" + Fore.RESET)
    # Ordenar los productos por código (de mayor a menor) antes de retornar
    all_products.sort(key=lambda x: x['codigo'], reverse=True)
    return all_products, categoria, db_path
