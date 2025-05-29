from api_tiendanube import crear_producto, buscar_producto_por_sku, actualizar_producto, limpiar_cache_productos
from colorama import Fore, Style
import sqlite3
import json
import time
import os
from config import preguntar_download
import sys



# Limpiar caché
limpiar_cache_productos()

# Rutas
global PATH
PATH = os.path.join(os.path.dirname(__file__), 'productos.db')
global GANANCIA_PORCENTAJE
global DOWNLOAD_IMAGES

# Manejo de argumentos
default_download = 'f'  # Valor por defecto para descarga de imágenes

if len(sys.argv) > 1:
    try:
        GANANCIA_PORCENTAJE = int(sys.argv[1])  # Convertir a entero aquí
        if len(sys.argv) > 2:
            DOWNLOAD_IMAGES = sys.argv[2].lower()
            if DOWNLOAD_IMAGES not in ['t', 'f']:
                DOWNLOAD_IMAGES = default_download
        else:
            DOWNLOAD_IMAGES = default_download
    except ValueError:
        print("Error: El primer argumento debe ser un número entero válido")
        GANANCIA_PORCENTAJE = int(input("Ingrese la ganancia porcentaje (entero): "))
        DOWNLOAD_IMAGES = input("¿Descargar imágenes? (t/f): ").lower() or default_download
else:
    GANANCIA_PORCENTAJE = int(input("Ingrese la ganancia porcentaje (entero): "))
    DOWNLOAD_IMAGES = input("¿Descargar imágenes? (t/f): ").lower() or default_download

print(f"Se ingresó {GANANCIA_PORCENTAJE}% como ganancia porcentaje")
print(f"Descarga de imágenes: {'Activada' if DOWNLOAD_IMAGES == 't' else 'Desactivada'}")

def obtener_productos_de_db():
    # Conectar a la base de datos
    conexion = sqlite3.connect(PATH)
    cursor = conexion.cursor()
    
    # Obtener todos los productos
    cursor.execute("SELECT * FROM productos")
    productos = cursor.fetchall()
    
    # Convertir a lista de diccionarios con la estructura deseada
    lista_productos = []
    for producto in productos:
        lista_productos.append({
            'codigo': producto[0],          # codigo
            'codigo_de_barras': producto[1], # codigo_barra
            'descripcion': producto[2],     # descripcion
            'precio': producto[3],          # precio
            'imagen_url': producto[4],      # imagen_url
            'imagen_local': producto[5],    # imagen_local
            'variante': producto[6].replace('-', '') if producto[6] else None,  # variante
            'categoria': producto[7],       # categoria
            'subcategoria': producto[8],    # subcategoria
            'peso_kg': producto[9],         # peso_kg
            'ancho_cm': producto[10],       # ancho_cm
            'alto_cm': producto[11],        # alto_cm
            'profundidad_cm': producto[12]  # profundidad_cm
        })
    
    # Cerrar conexión
    conexion.close()
    
    return lista_productos

# Obtener los productos en formato JSON
todos_los_productos = obtener_productos_de_db()


# Mostrar TODOS los productos encontrados
print(Fore.GREEN + "\n" + "="*50)
print(f" DETALLE COMPLETO DE {len(todos_los_productos)} PRODUCTOS, se mostraran 3 productos como muestra ")
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
    #print(f"{Fore.CYAN}Dimensiones:{Fore.RESET} {producto['peso_kg']}, {producto['ancho_cm']}, {producto['alto_cm']}, {producto['profundidad_cm']}")
    
    # Mostrar variante solo si existe
    if producto['variante']:
        print(f"{Fore.MAGENTA}Variante:{Fore.RESET} {producto['variante'].replace('-', '')}")

print(Fore.GREEN + "\n" + "="*50)
print(f" FIN DEL LISTADO - {len(todos_los_productos)} PRODUCTOS ")


print("="*50 + Fore.RESET)

def procesar_producto(producto):
    try:
        producto_id = buscar_producto_por_sku(producto['codigo'])
        start = time.time()
        
        if producto_id:
            result = actualizar_producto(producto_id, producto, GANANCIA_PORCENTAJE, DOWNLOAD_IMAGES)
            tipo = 'actualizado'
        else:
            result = crear_producto(producto, PATH, GANANCIA_PORCENTAJE, DOWNLOAD_IMAGES)
            tipo = 'creado'
            
        elapsed = time.time() - start
        return (tipo, producto['codigo'], result, elapsed)
    except Exception as e:
        return ('error', producto['codigo'], str(e), 0)

def procesar_productos():
    productos = obtener_productos_de_db()
    total_productos = len(productos)
    productos_procesados = 0
    
    print(Fore.CYAN + f"\nIniciando procesamiento de {total_productos} productos..." + Fore.RESET)
    
    for producto in productos:
        productos_procesados += 1
        tipo, codigo, detalle, elapsed = procesar_producto(producto)
        
        if tipo == 'actualizado':
            print(Fore.YELLOW + f"↻ Producto {codigo} actualizado en {elapsed:.2f} segundos ({productos_procesados}/{total_productos})" + Fore.RESET)
        elif tipo == 'creado':
            print(Fore.GREEN + f"✔ Producto {codigo} creado en {elapsed:.2f} segundos ({productos_procesados}/{total_productos})" + Fore.RESET)
        else:
            print(Fore.RED + f"✖ Error en producto {codigo}: {detalle} ({productos_procesados}/{total_productos})" + Fore.RESET)
    
    # Limpiar caché al finalizar
    limpiar_cache_productos()
    print(Fore.GREEN + f"\nProcesamiento completado. {productos_procesados} productos procesados." + Fore.RESET)

if __name__ == "__main__":
    print(Fore.CYAN + "\nINICIANDO SINCRONIZACION CON TIENDANUBE..." + Fore.RESET)
    procesar_productos()