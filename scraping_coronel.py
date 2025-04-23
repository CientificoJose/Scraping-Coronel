#Usamos en local
from asyncio import wait
from selenium import webdriver
import time
from app.guardar_excel import save_to_excel
from app.login import login
from app.scraping_all_product import scraping_all_product
from app.scraping_product import consolidar_todo_en_base_de_datos
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
from colorama import Fore

# Configurar opciones de Chrome
chrome_options = Options()
chrome_options.add_argument("--start-maximized")  # Abrir maximizado



# Inicializar driver
driver = webdriver.Chrome(options=chrome_options)

#Loguearnos
login_result = login(driver)
if not login_result:
    print(Fore.RED + "✖ Scraping cancelado por fallo en el login" + Fore.RESET)
    driver.quit()
    exit(1)  # Salir con código de error

# Limpia espacios en la columna 'Código' del Excel más reciente
# limpiar_codigos_sqlite()


column_names = [
    "Identificador de URL",  # Obligatorio. Alfanumérico. Identificador único sin espacios ni caracteres especiales.
    "Nombre",  # Obligatorio. Texto. Nombre del producto tal como aparecerá en la tienda.
    "Categorías",  # Opcional. Texto. Categorías y subcategorías separadas por comas.
    "Nombre de propiedad 1",  # Opcional. Texto. Nombre de la variante (por ejemplo, Talle, Color, etc.).
    "Valor de propiedad 1",  # Obligatorio si la propiedad está presente. Texto. Valor de la variante (por ejemplo, S, M, L).
    "Nombre de propiedad 2",  # Opcional. Texto. Similar a propiedad 1, si aplica.
    "Valor de propiedad 2",  # Obligatorio si la propiedad está presente. Texto. Similar a valor de propiedad 1.
    "Nombre de propiedad 3",  # Opcional. Texto. Similar a propiedad 1, si aplica.
    "Valor de propiedad 3",  # Obligatorio si la propiedad está presente. Texto. Similar a valor de propiedad 1.
    "Precio",  # Obligatorio. Numérico. Precio sin el signo $ y con decimales separados por un punto.
    "Precio promocional",  # Opcional. Numérico. Precio reducido opcional con el mismo formato que el precio.
    "Peso (kg)",  # Opcional. Numérico. Peso del producto en kilogramos, con decimales separados por un punto.
    "Alto (cm)",  # Opcional. Numérico. Altura en centímetros (sin decimales).
    "Ancho (cm)",  # Opcional. Numérico. Ancho en centímetros (sin decimales).
    "Profundidad (cm)",  # Opcional. Numérico. Profundidad en centímetros (sin decimales).
    "Stock",  # Opcional. Numérico. Cantidad disponible. Si está vacío, se toma como infinito.
    "SKU",  # Opcional. Alfanumérico. Código interno único para tu referencia.
    "Código de barras",  # Opcional. Numérico. Código de barras del producto.
    "Mostrar en tienda",  # Opcional. Texto. "SI" o "NO". Por defecto es "SI".
    "Envío sin cargo",  # Opcional. Texto. "SI" o "NO".
    "Descripción",  # Opcional. Texto. Detalle descriptivo del producto.
    "Tags",  # Opcional. Texto. Etiquetas separadas por comas para facilitar búsquedas.
    "Título para SEO",  # Opcional. Texto. Título optimizado para motores de búsqueda.
    "Descripción para SEO",  # Opcional. Texto. Descripción optimizada para motores de búsqueda.
    "Marca",  # Opcional. Texto. Marca del producto.
    "Producto Físico",  # Opcional. Texto. "SI" para productos físicos, "NO" para digitales.
    "MPN (Número de pieza del fabricante)",  # Opcional. Texto. Identificación del fabricante (productos industriales).
    "Sexo",  # Opcional. Texto. "Femenino", "Masculino" o "Unisex".
    "Rango de edad",  # Opcional. Texto. Por ejemplo, "Adulto", "5 a 13 años".
    "Costo"  # Opcional. Numérico. Valor interno del costo del producto.
]


# Obtener y mostrar productos de TODAS las páginas
print(Fore.GREEN + "="*50)
print(" INICIANDO SCRAPING COMPLETO DE PRODUCTOS ")
print("="*50 + Fore.RESET)



# 1. Obtener productos sin dimensiones
todos_los_productos_sin_dimensiones, categoria_grupal, DB_PATH = scraping_all_product(driver)

# 2. Consolidar Todo en BD
consolidar_todo_en_base_de_datos(todos_los_productos_sin_dimensiones)

# 3. integrar dimensiones
todos_los_productos = obtener_dimensiones_producto(
    todos_los_productos_sin_dimensiones,
    categoria=categoria_grupal,
    db_path=DB_PATH
)



# Mostrar resumen
print(Fore.GREEN + "\n" + "="*50)
print(f" SCRAPING COMPLETADO - {len(todos_los_productos)} PRODUCTOS ENCONTRADOS ")
print("="*50 + Fore.RESET)

# Mostrar TODOS los productos encontrados
print(Fore.GREEN + "\n" + "="*50)
print(f" DETALLE COMPLETO DE {len(todos_los_productos)} PRODUCTOS ENCONTRADOS, se mostraran 3 productos como muestra ")
print("="*50 + Fore.RESET)

for i, producto in enumerate(todos_los_productos[:3], 1):
    # Encabezado del producto
    print(Fore.YELLOW + f"\nProducto #{i}" + "-"*40 + Fore.RESET)
    
    # Información base
    print(f"{Fore.CYAN}Código:{Fore.RESET} {producto['codigo']}")
    print(f"{Fore.CYAN}Descripción:{Fore.RESET} {producto['descripcion']}")
    print(f"{Fore.CYAN}Precio:{Fore.RESET} {producto['precio']}")
    print(f"{Fore.CYAN}Imagen local:{Fore.RESET} {producto['imagen_local']}")
    print(f"{Fore.CYAN}Codigo de Barras:{Fore.RESET} {producto['codigo_de_barras']}")
    print(f"{Fore.CYAN}imagen_url:{Fore.RESET} {producto['imagen_url']}")
    print(f"{Fore.CYAN}Categoria:{Fore.RESET} {producto['categoria']}")
    print(f"{Fore.CYAN}Subcategoria:{Fore.RESET} {producto['subcategoria']}")
    print(f"{Fore.CYAN}Dimensiones:{Fore.RESET} {producto['peso_kg']}, {producto['ancho_cm']}, {producto['alto_cm']}, {producto['profundidad_cm']}")
    
    # Mostrar variante solo si existe
    if producto['variante']:
        print(f"{Fore.MAGENTA}Variante:{Fore.RESET} {producto['variante'].replace('-', '')}")

print(Fore.GREEN + "\n" + "="*50)
print(f" FIN DEL LISTADO - {len(todos_los_productos)} PRODUCTOS ")
print("="*50 + Fore.RESET)


 # 3. Procesar cada producto con Tiendanube
print(Fore.CYAN + "\nINICIANDO SINCRONIZACION CON TIENDANUBE..." + Fore.RESET)

for producto in todos_los_productos:
    # Buscar si el producto ya existe
    producto_id = buscar_producto_por_sku(producto['codigo'])
    
    if producto_id:
        # Actualizar producto existente
        if actualizar_producto(producto_id, producto):
            print(Fore.YELLOW + f"↻ Producto actualizado: {producto['codigo']}" + Fore.RESET)
        else:
            print(Fore.RED + f"✖ Error actualizando: {producto['codigo']}" + Fore.RESET)
    else:
        # Crear nuevo producto
        nuevo_id = crear_producto(producto)
        if nuevo_id:
            print(Fore.GREEN + f"✔ Nuevo producto creado (ID: {nuevo_id}): {producto['codigo']}" + Fore.RESET)
        else:
            print(Fore.RED + f"✖ Error creando: {producto['codigo']}" + Fore.RESET)

print(Fore.CYAN + "\nPROCESO COMPLETADO" + Fore.RESET)


