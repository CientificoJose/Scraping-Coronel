from api_tiendanube import crear_producto, buscar_producto_por_sku, actualizar_producto, limpiar_cache_productos
from colorama import Fore, Style
from app.core.db import obtener_productos_de_db as core_obtener_productos_de_db
from app.core.logger import registrar_error
import concurrent.futures
import threading
import json
import time
import os
import sys

def run_sync(ganancia=None, download_images=None, concurrency=3):
    """
    Función ejecutable para sincronizar productos desde SQLite local hacia Tiendanube.
    Soporta ejecución concurrente mediante ThreadPoolExecutor para acelerar la subida.
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
    print(f"Concurrencia de subida: {concurrency} hilos simultáneos")
    
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
    
    total_productos = len(todos_los_productos)
    if total_productos == 0:
        print(Fore.YELLOW + "⚠ No hay productos en la base de datos para sincronizar." + Fore.RESET)
        return
        
    print(Fore.CYAN + f"\nIniciando procesamiento concurrente de {total_productos} productos con {concurrency} trabajadores..." + Fore.RESET)
    
    start_total = time.time()
    lock = threading.Lock()
    contador = {"procesados": 0, "creados": 0, "actualizados": 0, "errores": 0}
    
    def procesar_un_producto(producto):
        try:
            start = time.time()
            producto_id = buscar_producto_por_sku(producto['codigo'])
            if producto_id:
                result = actualizar_producto(producto_id, producto, ganancia, download_images)
                tipo = 'actualizado'
            else:
                result = crear_producto(producto, db_path, ganancia, download_images)
                tipo = 'creado'
            elapsed = time.time() - start
            
            with lock:
                contador["procesados"] += 1
                idx = contador["procesados"]
                if tipo == 'actualizado':
                    contador["actualizados"] += 1
                    print(Fore.YELLOW + f"↻ [{idx}/{total_productos}] Producto {producto['codigo']} actualizado ({elapsed:.2f}s)" + Fore.RESET)
                else:
                    contador["creados"] += 1
                    print(Fore.GREEN + f"✔ [{idx}/{total_productos}] Producto {producto['codigo']} creado ({elapsed:.2f}s)" + Fore.RESET)
        except Exception as e:
            with lock:
                contador["procesados"] += 1
                contador["errores"] += 1
                idx = contador["procesados"]
                print(Fore.RED + f"✖ [{idx}/{total_productos}] Error en {producto['codigo']}: {str(e)}" + Fore.RESET)
            registrar_error(f"Error sincronizando producto {producto.get('codigo')}", e)

    # Procesamiento concurrente
    if concurrency > 1:
        with concurrent.futures.ThreadPoolExecutor(max_workers=concurrency) as executor:
            futures = [executor.submit(procesar_un_producto, prod) for prod in todos_los_productos]
            concurrent.futures.wait(futures)
    else:
        for prod in todos_los_productos:
            procesar_un_producto(prod)
            
    limpiar_cache_productos()
    total_elapsed = time.time() - start_total
    
    print(Fore.GREEN + "\n" + "="*50)
    print(" RESUMEN DE SINCRONIZACIÓN ")
    print("="*50 + Fore.RESET)
    print(f"✔ Procesados: {contador['procesados']}/{total_productos}")
    print(f"★ Creados: {contador['creados']}")
    print(f"↻ Actualizados: {contador['actualizados']}")
    if contador["errores"] > 0:
        print(Fore.RED + f"✖ Errores: {contador['errores']}" + Fore.RESET)
    print(f"⏱ Tiempo total: {total_elapsed:.1f} segundos ({total_elapsed/60:.2f} minutos)")
    print(Fore.GREEN + "="*50 + Fore.RESET)

if __name__ == "__main__":
    print(Fore.CYAN + "\nINICIANDO SINCRONIZACION CON TIENDANUBE..." + Fore.RESET)
    run_sync()