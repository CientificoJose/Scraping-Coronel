from api_tiendanube import crear_producto, buscar_producto_por_sku, actualizar_producto, limpiar_cache_productos
from colorama import Fore, Style
from app.core.db import obtener_productos_de_db as core_obtener_productos_de_db
import json
import time
import os
import sys

def run_sync(ganancia=None, download_images=None):
    """
    Función ejecutable para sincronizar productos desde SQLite local hacia Tiendanube.
    """
    # Limpiar caché
    limpiar_cache_productos()
    
    db_path = os.path.join(os.path.dirname(__file__), 'productos.db')
    default_download = 'f'
    
    # Obtener / preguntar ganancia si no se provee
    if ganancia is None:
        if len(sys.argv) > 1:
            try:
                ganancia = int(sys.argv[1])
            except ValueError:
                ganancia = int(input("Ingrese la ganancia porcentaje (entero): "))
        else:
            ganancia = int(input("Ingrese la ganancia porcentaje (entero): "))
            
    # Obtener / preguntar download_images si no se provee
    if download_images is None:
        if len(sys.argv) > 2:
            download_images = sys.argv[2].lower()
            if download_images not in ['t', 'f']:
                download_images = default_download
        else:
            if len(sys.argv) > 1:
                download_images = default_download
            else:
                download_images = input("¿Descargar imágenes? (t/f): ").lower() or default_download

    print(f"Se ingresó {ganancia}% como ganancia porcentaje")
    print(f"Descarga de imágenes: {'Activada' if download_images == 't' else 'Desactivada'}")
    
    # Obtener los productos de la BD
    todos_los_productos = core_obtener_productos_de_db(db_path)
    
    # Mostrar muestra de productos
    print(Fore.GREEN + "\n" + "="*50)
    print(f" DETALLE COMPLETO DE {len(todos_los_productos)} PRODUCTOS, se mostraran 3 productos como muestra ")
    print("="*50 + Fore.RESET)
    
    for i, producto in enumerate(todos_los_productos[:3], 1):
        print(Fore.YELLOW + f"\nProducto #{i}" + "-"*40 + Fore.RESET)
        print(f"{Fore.CYAN}Código:{Fore.RESET} {producto['codigo']}")
        print(f"{Fore.CYAN}Descripción:{Fore.RESET} {producto['descripcion']}")
        print(f"{Fore.CYAN}Precio:{Fore.RESET} {producto['precio']}")
        print(f"{Fore.CYAN}Imagen local:{Fore.RESET} {producto['imagen_local']}")
        print(f"{Fore.CYAN}Codigo de Barras:{Fore.RESET} {producto['codigo_de_barras']}")
        print(f"{Fore.CYAN}imagen_url:{Fore.RESET} {producto['imagen_url']}")
        print(f"{Fore.CYAN}Categoria:{Fore.RESET} {producto['categoria']}")
        print(f"{Fore.CYAN}Subcategoria:{Fore.RESET} {producto['subcategoria']}")
        if producto['variante']:
            print(f"{Fore.MAGENTA}Variante:{Fore.RESET} {producto['variante'].replace('-', '')}")
            
    print(Fore.GREEN + "\n" + "="*50)
    print(f" FIN DEL LISTADO - {len(todos_los_productos)} PRODUCTOS ")
    print("="*50 + Fore.RESET)
    
    # Procesar cada producto
    total_productos = len(todos_los_productos)
    productos_procesados = 0
    
    print(Fore.CYAN + f"\nIniciando procesamiento de {total_productos} productos..." + Fore.RESET)
    
    for producto in todos_los_productos:
        productos_procesados += 1
        try:
            producto_id = buscar_producto_por_sku(producto['codigo'])
            start = time.time()
            if producto_id:
                result = actualizar_producto(producto_id, producto, ganancia, download_images)
                tipo = 'actualizado'
            else:
                result = crear_producto(producto, db_path, ganancia, download_images)
                tipo = 'creado'
            elapsed = time.time() - start
            
            if tipo == 'actualizado':
                print(Fore.YELLOW + f"↻ Producto {producto['codigo']} actualizado en {elapsed:.2f} segundos ({productos_procesados}/{total_productos})" + Fore.RESET)
            else:
                print(Fore.GREEN + f"✔ Producto {producto['codigo']} creado en {elapsed:.2f} segundos ({productos_procesados}/{total_productos})" + Fore.RESET)
        except Exception as e:
            print(Fore.RED + f"✖ Error en producto {producto['codigo']}: {str(e)} ({productos_procesados}/{total_productos})" + Fore.RESET)
            
    limpiar_cache_productos()
    print(Fore.GREEN + f"\nProcesamiento completado. {productos_procesados} productos procesados." + Fore.RESET)

if __name__ == "__main__":
    print(Fore.CYAN + "\nINICIANDO SINCRONIZACION CON TIENDANUBE..." + Fore.RESET)
    run_sync()