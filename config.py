from colorama import Fore, Style
import threading

# Variables globales de configuración
DOWNLOAD_IMAGES = True

def set_download_images(value):
    """Función para cambiar el estado de descarga de imágenes"""
    global DOWNLOAD_IMAGES
    DOWNLOAD_IMAGES = value
    
def preguntar_download():
    return 't'

def preguntar_porcentaje():
    # Preguntar al usuario el porcentaje de ganancia
    print(Fore.CYAN + "\n" + "="*50)
    print(" CONFIGURACIÓN DE PORCENTAJE DE GANANCIA ")
    print("="*50 + Style.RESET_ALL)
    
    while True:
        try:
            respuesta = input(Fore.CYAN + "Ingrese el porcentaje de ganancia (ej: 40 para 40%): " + Style.RESET_ALL)
            porcentaje = int(float(respuesta))  # Convertir a float primero y luego a int
            print(Fore.GREEN + f"✔ Porcentaje de ganancia configurado a: {porcentaje}%" + Style.RESET_ALL)
            print(Fore.CYAN + "="*50 + "\n" + Style.RESET_ALL)
            return porcentaje
        except ValueError:
            print(Fore.RED + "⚠ Error: Debe ingresar un número válido. Intente nuevamente." + Style.RESET_ALL)
