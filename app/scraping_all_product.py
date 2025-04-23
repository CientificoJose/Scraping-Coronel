from colorama import Fore
from .scraping_product import scraping_product
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time

def scraping_all_product(driver):
    """
    Extrae información de productos de TODAS las páginas disponibles con verificación robusta
    
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
            # Preparación y scroll
            current_url = driver.current_url
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            
            # Localizar botón siguiente
            next_button = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.ID, "siguiente"))
            )
            
            # VERIFICACIÓN DEFINITIVA DE ÚLTIMA PÁGINA
            if next_button.get_attribute("disabled") is not None:
                print(Fore.GREEN + "✅ Botón siguiente DESHABILITADO - última página confirmada" + Fore.RESET)
                break
                
            # Verificar también por clase btn-shadow (estado activo)
            if "btn-shadow" not in next_button.get_attribute("class"):
                print(Fore.GREEN + "✅ Botón siguiente INACTIVO - última página confirmada" + Fore.RESET)
                break
                
            # Intentar cambio de página
            driver.execute_script("arguments[0].click();", next_button)
            
            # Esperar cambios con timeout más corto
            try:
                WebDriverWait(driver, 5).until(
                    lambda d: (
                        d.current_url != current_url or
                        len(scrape_products(driver)) > len(current_products)
                    )
                )
                page_number += 1
            except:
                print(Fore.RED + "❌ No hubo cambio de página - última página confirmada" + Fore.RESET)
                break
                
        except Exception as e:
            print(Fore.RED + f"🚨 Error crítico: {str(e)}" + Fore.RESET)
            print(Fore.YELLOW + "Terminando scraping por seguridad" + Fore.RESET)
            break
            
   
    print(Fore.GREEN + f"\nSCRAPING COMPLETADO - {len(all_products)} productos recolectados" + Fore.RESET)
    # Ordenar los productos por código (de mayor a menor) antes de retornar
    all_products.sort(key=lambda x: x['codigo'], reverse=True)
    return all_products, categoria, db_path
