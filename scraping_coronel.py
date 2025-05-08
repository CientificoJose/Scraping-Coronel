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
from app.deepseek import obtener_dimensiones_producto
from app.scraping_product import inicializar_bd
import os
import openpyxl
from datetime import datetime

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
from colorama import Fore, Style

# Preguntar al usuario si desea descargar imágenes
print(Fore.CYAN + "\n" + "="*50)
print(" CONFIGURACIÓN DE DESCARGA DE IMÁGENES ")
print("="*50)
respuesta = input("¿Deseas descargar las imágenes de los productos? (s/n): " + Style.RESET_ALL).lower()
set_download_images(respuesta == 's')
if respuesta == 's':
    print(Fore.GREEN + "✔ Las imágenes se descargarán durante el proceso" + Style.RESET_ALL)
else:
    print(Fore.YELLOW + "ℹ Las imágenes NO se descargarán (se mantendrán las referencias)" + Style.RESET_ALL)
print(Fore.CYAN + "="*50 + "\n" + Style.RESET_ALL)

# Configurar opciones de Chrome
chrome_options = Options()
chrome_options.add_argument("--start-maximized")  # Abrir maximizado
chrome_options.add_argument('--log-level=3')  # Desactivar la mayoría de los logs
chrome_options.add_experimental_option('excludeSwitches', ['enable-logging'])  # Desactivar mensajes de logging
chrome_options.add_argument("--disable-logging")  # Desactivar logging
chrome_options.add_argument("--disable-dev-shm-usage")  # Desactivar mensajes de memoria compartida

# Inicializar driver
driver = webdriver.Chrome(options=chrome_options)

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
respuesta = input(Fore.CYAN + "\n¿Deseas proceder con la subida de productos a Tiendanube? (s/n): " + Fore.RESET).lower()

if respuesta == 's':
    print(Fore.YELLOW + "\nIniciando proceso de subida a Tiendanube..." + Fore.RESET)
    import subprocess
    try:
        subprocess.run(['python', 'subida_tienda.py'], check=True)
    except subprocess.CalledProcessError as e:
        print(Fore.RED + f"\nError al ejecutar subida_tienda.py: {e}" + Fore.RESET)
    except FileNotFoundError:
        print(Fore.RED + "\nError: No se encontró el archivo subida_tienda.py" + Fore.RESET)
else:
    print(Fore.YELLOW + "\nProceso de subida cancelado. Los datos del scraping están guardados y puedes ejecutar subida_tienda.py más tarde." + Fore.RESET)
