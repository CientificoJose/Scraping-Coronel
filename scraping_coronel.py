#Usamos en local
from asyncio import wait
from selenium import webdriver
import time
from app.guardar_excel import save_to_excel
from app.login import login
from app.scraping_all_product import scraping_all_product
from app.scraping_product import consolidar_todo_en_base_de_datos, set_download_images
from selenium.webdriver.chrome.options import Options
from app.limpiar_productos_coronel import limpiar_codigos_sqlite
from api_tiendanube import crear_producto, buscar_producto_por_sku, actualizar_producto
from app.services.ai_estimator import obtener_dimensiones_producto
from app.scraping_product import inicializar_bd
from app.core.browser import get_chrome_driver
import os
import openpyxl
from datetime import datetime
from inputimeout import inputimeout, TimeoutOccurred
from colorama import Fore, Style


#Depurar
from selenium import webdriver
from selenium.webdriver.common.keys import Keys
import csv
import time
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import openpyxl
import pandas as pd
import os
import re
import datetime
from config import preguntar_download
from config import preguntar_porcentaje

# Preguntar al usuario si desea descargar imágenes
DOWNLOAD_IMAGES = preguntar_download() 
# Preguntar al usuario porcentaje
GANANCIA_PORCENTAJE = preguntar_porcentaje()



# Inicializar driver centralizado
driver = get_chrome_driver()

#Loguearnos
login_result = login(driver)
if not login_result:
    print(Fore.RED + "✖ Scraping cancelado por fallo en el login" + Fore.RESET)
    driver.quit()
    exit(1)  # Salir con código de error

# Obtener y mostrar productos de TODAS las páginas
print(Fore.GREEN + "="*50)
print(" INICIANDO SCRAPING COMPLETO DE PRODUCTOS ")
print("="*50 + Fore.RESET)



# 1. Obtener productos sin dimensiones
todos_los_productos_sin_dimensiones, categoria_grupal, DB_PATH = scraping_all_product(driver)

# 2. Consolidar Todo en BD
todos_los_productos = consolidar_todo_en_base_de_datos(todos_los_productos_sin_dimensiones)


# Mostrar resumen
print(Fore.GREEN + "\n" + "="*50)
print(f" SCRAPING COMPLETADO - {len(todos_los_productos)} PRODUCTOS ENCONTRADOS ")
print("="*50 + Fore.RESET)

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
    import subprocess
    comando = ['python', 'subida_tienda.py', str(GANANCIA_PORCENTAJE), DOWNLOAD_IMAGES]
    print(Fore.CYAN + "Ejecutando:", ' '.join(comando) + Style.RESET_ALL)
    try:
        subprocess.run(comando, check=True)
    except subprocess.CalledProcessError as e:
        print(Fore.RED + f"\nError al ejecutar subida_tienda.py: {e}" + Style.RESET)
    except FileNotFoundError:
        print(Fore.RED + "\nError: No se encontró el archivo subida_tienda.py" + Style.RESET)
else:
    print(Fore.YELLOW + "\nProceso de subida cancelado. Los datos del scraping están guardados y puedes ejecutar subida_tienda.py más tarde." + Style.RESET)