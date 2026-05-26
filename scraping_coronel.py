# Usamos en local
import time
import os
import sys
import subprocess
from colorama import Fore, Style
from inputimeout import inputimeout, TimeoutOccurred

from app.login import login
from app.scraping_all_product import scraping_all_product
from app.scraping_product import consolidar_todo_en_base_de_datos, set_download_images
from app.core.browser import get_chrome_driver
from config import preguntar_download, preguntar_porcentaje

def run_scrape(ganancia=None, download_images=None):
    """
    Función ejecutable para realizar el scraping del catálogo de Coronel Mayorista.
    Retorna (success, ganancia, download_images)
    """
    if download_images is None:
        download_images = preguntar_download()
    
    download_bool = (download_images == 't')
    set_download_images(download_bool)

    if ganancia is None:
        ganancia = preguntar_porcentaje()

    # Inicializar driver centralizado
    driver = get_chrome_driver()
    
    try:
        # Loguearnos
        login_result = login(driver)
        if not login_result:
            print(Fore.RED + "✖ Scraping cancelado por fallo en el login" + Fore.RESET)
            driver.quit()
            return False, ganancia, download_images
        
        print(Fore.GREEN + "="*50)
        print(" INICIANDO SCRAPING COMPLETO DE PRODUCTOS ")
        print("="*50 + Fore.RESET)
        
        # 1. Obtener productos sin dimensiones
        todos_los_productos_sin_dimensiones, categoria_grupal, db_path = scraping_all_product(driver)
        
        # 2. Consolidar Todo en BD
        todos_los_productos = consolidar_todo_en_base_de_datos(todos_los_productos_sin_dimensiones)
        
        print(Fore.GREEN + "\n" + "="*50)
        print(f" SCRAPING COMPLETADO - {len(todos_los_productos)} PRODUCTOS ENCONTRADOS ")
        print("="*50 + Fore.RESET)
        return True, ganancia, download_images
    except Exception as e:
        print(Fore.RED + f"🚨 Error en el proceso de scraping: {e}" + Fore.RESET)
        return False, ganancia, download_images
    finally:
        try:
            driver.quit()
        except:
            pass

if __name__ == "__main__":
    success, ganancia, download_images = run_scrape()
    if success:
        # 3. Procesar cada producto con Tiendanube
        try:
            respuesta = inputimeout(
                prompt=Fore.CYAN + "\n¿Deseas proceder con la subida de productos a Tiendanube? (s/n) [Timeout 5s]: " + Fore.RESET,
                timeout=5
            ).lower()
        except TimeoutOccurred:
            respuesta = 's'  # Respuesta por defecto si se agota el tiempo
            print(Fore.YELLOW + "\nTiempo agotado. Continuando con la subida automática..." + Style.RESET_ALL)

        if respuesta in ['s', '']:  # Considerar Enter o timeout como 's'
            print(Fore.YELLOW + "\nIniciando proceso de subida a Tiendanube..." + Style.RESET_ALL)
            comando = ['python', 'subida_tienda.py', str(ganancia), download_images]
            print(Fore.CYAN + "Ejecutando:", ' '.join(comando) + Style.RESET_ALL)
            try:
                subprocess.run(comando, check=True)
            except subprocess.CalledProcessError as e:
                print(Fore.RED + f"\nError al ejecutar subida_tienda.py: {e}" + Style.RESET)
            except FileNotFoundError:
                print(Fore.RED + "\nError: No se encontró el archivo subida_tienda.py" + Style.RESET)
        else:
            print(Fore.YELLOW + "\nProceso de subida cancelado. Los datos del scraping están guardados y puedes ejecutar subida_tienda.py más tarde." + Style.RESET)