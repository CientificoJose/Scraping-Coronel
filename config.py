from colorama import Fore, Style
import threading

# Variables globales de configuración
DOWNLOAD_IMAGES = True

def set_download_images(value):
    """Función para cambiar el estado de descarga de imágenes"""
    global DOWNLOAD_IMAGES
    DOWNLOAD_IMAGES = value
    
def preguntar_download():
    # Preguntar al usuario si desea descargar imágenes
    print(Fore.CYAN + "\n" + "="*50)
    print(" CONFIGURACIÓN DE DESCARGA DE IMÁGENES ")
    print("="*50)
    
    respuesta = None
    
    def input_thread():
        nonlocal respuesta
        respuesta = input("¿Deseas descargar las imágenes de los productos?, ten en cuenta que este proceso durara mucho mas tiempo (s/n): " + Style.RESET_ALL).lower()
    
    thread = threading.Thread(target=input_thread)
    thread.daemon = True
    thread.start()
    thread.join(timeout=5)
    
    if respuesta is None:
        print(Fore.YELLOW + "\nℹ Tiempo de espera agotado (5s), se asume NO descargar imágenes" + Style.RESET_ALL)
        set_download_images(False)
        print(Fore.CYAN + "="*50 + "\n" + Style.RESET_ALL)
        return False
    
    set_download_images(respuesta == 's')
    if respuesta == 's':
        print(Fore.GREEN + "✔ Las imágenes se descargarán durante el proceso" + Style.RESET_ALL)
    else:
        print(Fore.YELLOW + "ℹ Las imágenes NO se descargarán (se mantendrán las referencias)" + Style.RESET_ALL)
    print(Fore.CYAN + "="*50 + "\n" + Style.RESET_ALL)
    return respuesta == 's'