import argparse
import sys
from colorama import Fore, Style, init

from scraping_coronel import run_scrape
from subida_tienda import run_sync
from actualizar_stock import run_stock
from config import preguntar_download, preguntar_porcentaje

init(autoreset=True)

def ejecutar_menu_interactivo():
    print(Fore.CYAN + "="*60)
    print("           SISTEMA DE SINCRONIZACIÓN JG-STORE")
    print("="*60 + Style.RESET_ALL)
    print("\nSeleccione una opción ingresando su número:")
    print(f"\n  [{Fore.GREEN}1{Style.RESET_ALL}] ⚡ {Fore.GREEN}Scraping + Subida Rápida (Recomendado){Style.RESET_ALL}")
    print("      (Extrae productos del catálogo y los sube a Tiendanube)")
    print(f"\n  [{Fore.YELLOW}2{Style.RESET_ALL}] 🔄 {Fore.YELLOW}Pipeline Completo (Scraping + Subida + Stock){Style.RESET_ALL}")
    print("      (Sincroniza catálogo, stock y oculta discontinuados)")
    print(f"\n  [{Fore.CYAN}3{Style.RESET_ALL}] 🔍 Solo Scraping (Actualiza base de datos local)")
    print(f"  [{Fore.CYAN}4{Style.RESET_ALL}] 📤 Solo Sincronizar (Sube productos locales a Tiendanube)")
    print(f"  [{Fore.CYAN}5{Style.RESET_ALL}] 📦 Solo Actualizar Stock (Actualiza stock/visibilidad)")
    print(f"  [{Fore.RED}6{Style.RESET_ALL}] ❌ Salir")
    print("\n" + "-"*60)
    
    while True:
        opcion = input(Fore.CYAN + "Selección (1-6): " + Style.RESET_ALL).strip()
        if opcion in ["1", "2", "3", "4", "5", "6"]:
            break
        print(Fore.RED + "Opción inválida. Ingrese un número de 1 a 6." + Style.RESET_ALL)
        
    if opcion == "6":
        print(Fore.YELLOW + "Saliendo del sistema..." + Style.RESET_ALL)
        return

    # Pedir ganancia para las opciones de scrape/sync
    ganancia = None
    download_images = None
    if opcion in ["1", "2", "3", "4"]:
        # Preguntar ganancia
        while True:
            resp_g = input(Fore.CYAN + "Ingrese porcentaje de ganancia (Presione Enter para usar 40%): " + Style.RESET_ALL).strip()
            if resp_g == "":
                ganancia = 40
                break
            try:
                ganancia = int(float(resp_g))
                break
            except ValueError:
                print(Fore.RED + "Debe ingresar un número entero válido." + Style.RESET_ALL)
                
        # Preguntar descargas
        while True:
            resp_d = input(Fore.CYAN + "¿Desea descargar las imágenes? (s/n) (Presione Enter para NO): " + Style.RESET_ALL).strip().lower()
            if resp_d in ["", "n"]:
                download_images = "f"
                break
            elif resp_d == "s":
                download_images = "t"
                break
            print(Fore.RED + "Respuesta inválida. Ingrese 's' o 'n'." + Style.RESET_ALL)

    print(Fore.CYAN + "\nIniciando proceso..." + Style.RESET_ALL)
    
    if opcion == "1":
        # scrape-sync
        print(Fore.CYAN + "\n=== [INICIANDO PIPELINE: SCRAPE + SYNC] ===" + Style.RESET_ALL)
        print(Fore.CYAN + "\n--- Paso 1: Scraping ---" + Style.RESET_ALL)
        success, final_ganancia, final_download = run_scrape(ganancia, download_images)
        if not success:
            print(Fore.RED + "\n❌ Pipeline detenido: Scrape falló." + Style.RESET_ALL)
            return
            
        print(Fore.CYAN + "\n--- Paso 2: Sincronización de Productos ---" + Style.RESET_ALL)
        run_sync(final_ganancia, final_download)
        print(Fore.GREEN + "\n★ Proceso completado exitosamente ★" + Style.RESET_ALL)
        
    elif opcion == "2":
        # full-run
        print(Fore.CYAN + "\n=== [INICIANDO PIPELINE COMPLETO] ===" + Style.RESET_ALL)
        print(Fore.CYAN + "\n--- Paso 1: Scraping ---" + Style.RESET_ALL)
        success, final_ganancia, final_download = run_scrape(ganancia, download_images)
        if not success:
            print(Fore.RED + "\n❌ Pipeline detenido: Scrape falló." + Style.RESET_ALL)
            return
            
        print(Fore.CYAN + "\n--- Paso 2: Sincronización de Productos ---" + Style.RESET_ALL)
        run_sync(final_ganancia, final_download)
        
        print(Fore.CYAN + "\n--- Paso 3: Sincronización de Stock ---" + Style.RESET_ALL)
        run_stock()
        print(Fore.GREEN + "\n★ Pipeline completo finalizado ★" + Style.RESET_ALL)
        
    elif opcion == "3":
        # scrape
        print(Fore.CYAN + "\n=== [EJECUTANDO SCRAPE] ===" + Style.RESET_ALL)
        run_scrape(ganancia, download_images)
        
    elif opcion == "4":
        # sync
        print(Fore.CYAN + "\n=== [EJECUTANDO SYNC] ===" + Style.RESET_ALL)
        run_sync(ganancia, download_images)
        
    elif opcion == "5":
        # stock
        print(Fore.CYAN + "\n=== [EJECUTANDO STOCK] ===" + Style.RESET_ALL)
        run_stock()

def main():
    if len(sys.argv) == 1:
        ejecutar_menu_interactivo()
        return

    parser = argparse.ArgumentParser(
        description="Orquestador Central para Scraping y Sincronización - Coronel Mayorista & Tiendanube",
        formatter_class=argparse.RawTextHelpFormatter
    )
    
    subparsers = parser.add_subparsers(dest="command", required=True, help="Subcomando a ejecutar")
    
    # Subcomando scrape
    parser_scrape = subparsers.add_parser("scrape", help="Ejecuta la extracción de productos y actualización de BD local")
    parser_scrape.add_argument("-g", "--ganancia", type=int, help="Porcentaje de ganancia para precios (ej. 40)")
    parser_scrape.add_argument("-d", "--download-images", choices=["t", "f"], help="Descargar imágenes ('t' o 'f')")
    parser_scrape.add_argument("-y", "--no-prompt", action="store_true", help="No solicitar confirmación interactiva")
    
    # Subcomando sync
    parser_sync = subparsers.add_parser("sync", help="Sincroniza y crea/actualiza los productos de SQLite en Tiendanube")
    parser_sync.add_argument("-g", "--ganancia", type=int, help="Porcentaje de ganancia para precios (ej. 40)")
    parser_sync.add_argument("-d", "--download-images", choices=["t", "f"], help="Descargar imágenes ('t' o 'f')")
    parser_sync.add_argument("-y", "--no-prompt", action="store_true", help="No solicitar confirmación interactiva")

    # Subcomando stock
    parser_stock = subparsers.add_parser("stock", help="Actualiza stock de catálogo en Tiendanube (inactiva discontinuados)")
    
    # Subcomando full-run
    parser_full = subparsers.add_parser("full-run", help="Ejecuta el pipeline completo (scrape -> sync -> stock)")
    parser_full.add_argument("-g", "--ganancia", type=int, help="Porcentaje de ganancia para precios (ej. 40)")
    parser_full.add_argument("-d", "--download-images", choices=["t", "f"], help="Descargar imágenes ('t' o 'f')")
    parser_full.add_argument("-y", "--no-prompt", action="store_true", help="No solicitar confirmación interactiva")
    
    # Subcomando scrape-sync
    parser_scrape_sync = subparsers.add_parser("scrape-sync", help="Ejecuta scrape y sync secuencialmente (sin actualizar stocks)")
    parser_scrape_sync.add_argument("-g", "--ganancia", type=int, help="Porcentaje de ganancia para precios (ej. 40)")
    parser_scrape_sync.add_argument("-d", "--download-images", choices=["t", "f"], help="Descargar imágenes ('t' o 'f')")
    parser_scrape_sync.add_argument("-y", "--no-prompt", action="store_true", help="No solicitar confirmación interactiva")
    
    args = parser.parse_args()

    # Resolver ganancia y descargas
    ganancia = None
    download_images = None
    
    if args.command in ["scrape", "sync", "full-run", "scrape-sync"]:
        if args.no_prompt:
            ganancia = args.ganancia if args.ganancia is not None else 40
            download_images = args.download_images if args.download_images is not None else "f"
        else:
            ganancia = args.ganancia
            download_images = args.download_images

    # Ejecución de comandos
    if args.command == "scrape":
        print(Fore.CYAN + "\n=== [EJECUTANDO SCRAPE] ===" + Style.RESET_ALL)
        success, final_ganancia, final_download = run_scrape(ganancia, download_images)
        if success:
            print(Fore.GREEN + "\n✓ Scrape finalizado con éxito." + Style.RESET_ALL)
        else:
            print(Fore.RED + "\n❌ Scrape falló." + Style.RESET_ALL)
            sys.exit(1)
            
    elif args.command == "sync":
        print(Fore.CYAN + "\n=== [EJECUTANDO SYNC] ===" + Style.RESET_ALL)
        run_sync(ganancia, download_images)
        print(Fore.GREEN + "\n✓ Sincronización de productos finalizada." + Style.RESET_ALL)
        
    elif args.command == "stock":
        print(Fore.CYAN + "\n=== [EJECUTANDO STOCK] ===" + Style.RESET_ALL)
        success = run_stock()
        if success:
            print(Fore.GREEN + "\n✓ Sincronización de stock finalizada con éxito." + Style.RESET_ALL)
        else:
            print(Fore.RED + "\n❌ Sincronización de stock falló." + Style.RESET_ALL)
            sys.exit(1)
            
    elif args.command == "full-run":
        print(Fore.CYAN + "\n=== [INICIANDO FULL RUN] ===" + Style.RESET_ALL)
        
        # 1. Scrape
        print(Fore.CYAN + "\n--- Paso 1: Scraping ---" + Style.RESET_ALL)
        success, final_ganancia, final_download = run_scrape(ganancia, download_images)
        if not success:
            print(Fore.RED + "\n❌ Pipeline detenido: Scrape falló." + Style.RESET_ALL)
            sys.exit(1)
            
        # 2. Sync (usa la ganancia y descargas confirmadas en el paso anterior)
        print(Fore.CYAN + "\n--- Paso 2: Sincronización de Productos ---" + Style.RESET_ALL)
        run_sync(final_ganancia, final_download)
        
        # 3. Stock
        print(Fore.CYAN + "\n--- Paso 3: Sincronización de Stock ---" + Style.RESET_ALL)
        success = run_stock()
        if not success:
            print(Fore.RED + "\n❌ Pipeline finalizó con errores en actualización de stock." + Style.RESET_ALL)
            sys.exit(1)
            
        print(Fore.GREEN + "\n★ Pipeline FULL RUN completado exitosamente de punta a punta ★" + Style.RESET_ALL)
        
    elif args.command == "scrape-sync":
        print(Fore.CYAN + "\n=== [INICIANDO PIPELINE: SCRAPE + SYNC] ===" + Style.RESET_ALL)
        
        # 1. Scrape
        print(Fore.CYAN + "\n--- Paso 1: Scraping ---" + Style.RESET_ALL)
        success, final_ganancia, final_download = run_scrape(ganancia, download_images)
        if not success:
            print(Fore.RED + "\n❌ Pipeline detenido: Scrape falló." + Style.RESET_ALL)
            sys.exit(1)
            
        # 2. Sync (usa los mismos parámetros ganancia y descargas)
        print(Fore.CYAN + "\n--- Paso 2: Sincronización de Productos ---" + Style.RESET_ALL)
        run_sync(final_ganancia, final_download)
        
        print(Fore.GREEN + "\n★ Pipeline SCRAPE-SYNC completado exitosamente ★" + Style.RESET_ALL)

if __name__ == "__main__":
    main()
