from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from app.login import login
from colorama import Fore, Style, init
import pandas as pd
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

def obtener_ultimo_excel():
    """Obtiene el archivo Excel más reciente de la carpeta productos_coronel"""
    carpeta = os.path.join(os.path.dirname(__file__), 'productos_coronel')
    archivos = glob.glob(os.path.join(carpeta, '*.xlsx'))
    if not archivos:
        return None
    return max(archivos, key=os.path.getmtime)

def limpiar_codigo(codigo):
    """Elimina espacios del código"""
    if isinstance(codigo, str):
        return codigo.replace(" ", "")
    return codigo

def cargar_excel_a_sqlite(excel_path):
    """Carga el Excel a SQLite y limpia los códigos"""
    # Leer el Excel
    df = pd.read_excel(excel_path)
    
    # Limpiar códigos (primera columna)
    primera_columna = df.columns[0]
    df[primera_columna] = df[primera_columna].apply(limpiar_codigo)
    
    # Crear conexión SQLite
    db_path = os.path.join(os.path.dirname(__file__), 'productos_coronel', 'productos.db')
    conn = sqlite3.connect(db_path)
    
    # Guardar en SQLite
    df.to_sql('productos_coronel', conn, if_exists='replace', index=False)
    conn.close()
    
    return db_path

def actualizar_stock_productos():
    """Función principal para actualizar el stock de productos"""
    try:
        # 1. Obtener último Excel
        excel_path = obtener_ultimo_excel()
        if not excel_path:
            print(Fore.RED + "No se encontró ningún archivo Excel en la carpeta productos_coronel" + Style.RESET_ALL)
            return
            
        print(Fore.GREEN + f"Procesando archivo: {os.path.basename(excel_path)}" + Style.RESET_ALL)
        
        # 2. Cargar Excel a SQLite
        db_path = cargar_excel_a_sqlite(excel_path)
        
        # 3. Obtener todos los productos de Tiendanube
        print(Fore.YELLOW + "Obteniendo productos de Tiendanube..." + Style.RESET_ALL)
        response = requests.get(f"{BASE_URL}/products", headers=headers)
        productos_tienda = response.json()
        
        # 4. Conectar a SQLite
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # 5. Obtener códigos del Excel
        cursor.execute("SELECT DISTINCT [Código] FROM productos_coronel")
        codigos_excel = {row[0] for row in cursor.fetchall() if row[0]}
        
        # 6. Procesar cada producto de Tiendanube
        productos_actualizados = 0
        for producto in productos_tienda:
            for variante in producto.get('variants', []):
                sku = variante.get('sku', '')
                if sku and sku not in codigos_excel:
                    # Actualizar stock a 0
                    print(Fore.YELLOW + f"Actualizando stock a 0 para SKU: {sku}" + Style.RESET_ALL)
                    
                    payload = {
                        "stock": 0
                    }
                    
                    response = requests.put(
                        f"{BASE_URL}/products/{producto['id']}/variants/{variante['id']}",
                        headers=headers,
                        json=payload
                    )
                    
                    if response.status_code == 200:
                        productos_actualizados += 1
                    else:
                        print(Fore.RED + f"Error actualizando SKU {sku}: {response.text}" + Style.RESET_ALL)
        
        conn.close()
        print(Fore.GREEN + f"Proceso completado. {productos_actualizados} productos actualizados a stock 0" + Style.RESET_ALL)
        
    except Exception as e:
        print(Fore.RED + f"Error: {str(e)}" + Style.RESET_ALL)

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

# Loguearnos
login_result = login(driver, False)
if not login_result:
    print(Fore.RED + "✖ Scraping cancelado por fallo en el login" + Fore.RESET)
    driver.quit()
    exit(1)

# Ejecutar actualización de stock
actualizar_stock_productos()

# Cerrar el navegador
driver.quit()
