from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from selenium.common.exceptions import TimeoutException
import time
from colorama import Fore
from tkinter import Tk, Button, Label
import threading
import os
import shutil
from datetime import datetime

# Variable global para controlar el estado del botón
button_clicked = False

def create_floating_button():
    global button_clicked
    root = Tk()
    root.title("Control de Scraping")
    root.overrideredirect(True)
    root.attributes('-topmost', True)
    
    def on_click():
        global button_clicked
        button_clicked = True
        root.destroy()
    
    btn = Button(root, text="CONTINUAR SCRAPING", 
                bg="#4CAF50", fg="white",
                font=('Arial', 12, 'bold'),
                padx=25, pady=15,
                command=on_click)
    btn.pack()
    
    # Posicionamiento
    root.geometry("220x70+20+{}".format(root.winfo_screenheight()-120))
    root.mainloop()

def descargar_lista_precios(driver, download_dir):
    """
    Navega a la página de lista de precios y descarga el Excel
    """
    try:
        wait = WebDriverWait(driver, 15)
        
        # 1. Navegar a la página de lista de precios
        #print(Fore.YELLOW + "\nNavegando a la lista de precios..." + Fore.RESET)
        driver.get('https://www.coronelmayorista.com/#/usuario/listaPrecios')

        
        # 2. Esperar y hacer click en el botón Exportar
        #print(Fore.YELLOW + "Buscando botón de exportar..." + Fore.RESET)
        export_button = wait.until(EC.element_to_be_clickable(
            (By.XPATH, "//button[contains(@class, 'btn-exportar')]")
        ))
        export_button.click()
        
        time.sleep(5)  # Dar tiempo para que se complete la descarga
        
        # 3. Esperar y hacer click en la opción Excel
        #print(Fore.YELLOW + "Seleccionando exportación a Excel..." + Fore.RESET)
        excel_option = wait.until(EC.element_to_be_clickable(
            (By.XPATH, "//button[@mat-menu-item]//span[contains(text(), 'Excel')]/..")
        ))
        excel_option.click()
        
        time.sleep(5)  # Dar tiempo para que se complete la descarga
        
        
        # 4. Esperar a que se descargue el archivo
        #print(Fore.YELLOW + "Esperando la descarga del archivo..." + Fore.RESET)
       
        
        # 5. Mover el archivo descargado a la carpeta productos_coronel
        downloads_folder = os.path.expanduser("~\\Downloads")
        # Buscar el archivo más reciente que contenga "Lista de precios"
        files = [f for f in os.listdir(downloads_folder) if "Lista de Precios" in f]
        if files:
            latest_file = max([os.path.join(downloads_folder, f) for f in files], key=os.path.getctime)
            # Crear nombre de archivo con timestamp
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            new_filename = f"lista_precios_{timestamp}.xlsx"
            new_path = os.path.join(download_dir, new_filename)
            
            # Mover el archivo
            shutil.move(latest_file, new_path)
            #print(Fore.GREEN + f"✔ Excel descargado y movido a: {new_path}" + Fore.RESET)
            return True
        else:
            print(Fore.RED + "✖ No se encontró el archivo descargado" + Fore.RESET)
            return False
            
    except Exception as e:
        print(Fore.RED + f"❌ Error descargando lista de precios: {str(e)}" + Fore.RESET)
        return False

def login(driver, show_button=True):
    """
    Versión optimizada del login para Coronel Mayotista que:
    - Usa CUIT y password (no email)
    - Reemplaza time.sleep() con esperas inteligentes
    - Incluye verificación de login exitoso
    - Descarga automáticamente la lista de precios
    
    Args:
        driver: WebDriver instance
        show_button: bool, opcional. Si es True muestra el botón flotante para continuar, si es False omite este paso
    """
    try:
        print(Fore.YELLOW + "\nIniciando proceso de login..." + Fore.RESET)
        
        # 1. Navegar a página de login
        driver.get('https://www.coronelmayorista.com/#/sign-in')
        
        wait = WebDriverWait(driver, 15)
        
        # 2. Ingresar CUIT
        cuit_field = wait.until(EC.element_to_be_clickable(
            (By.CSS_SELECTOR, 'input[formcontrolname="usuarioCuit"]')
        ))
        cuit_field.clear()
        cuit_field.send_keys('27958596508')
        
        # 3. Ingresar contraseña
        password_field = wait.until(EC.element_to_be_clickable(
            (By.CSS_SELECTOR, 'input[formcontrolname="usuarioPassword"]')
        ))
        password_field.clear()
        password_field.send_keys('95859650')
        
        # 4. Click en Ingresar
        login_button = wait.until(EC.element_to_be_clickable(
            (By.CSS_SELECTOR, 'button.btnIngresar')
        ))
        login_button.click()
        
        # 5. Verificación positiva de login exitoso
        wait.until(EC.url_contains('/#/home'))
        
        # Verificar presencia del elemento de usuario
        try:
            wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, 'li.nav-item.nav-usuario')))
            print(Fore.GREEN + "✔ Login exitoso" + Fore.RESET)
            
            # 6. Descargar lista de precios
            # Crear carpeta productos_coronel si no existe
            download_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'productos_coronel')
            os.makedirs(download_dir, exist_ok=True)
            
            if descargar_lista_precios(driver, download_dir):
                print(Fore.GREEN + "✔ Lista de precios descargada exitosamente" + Fore.RESET)
            else:
                print(Fore.RED + "✖ Error descargando lista de precios" + Fore.RESET)
                
            
            
            # 7. Continuar con el proceso normal
            driver.get('https://www.coronelmayorista.com/#/home')
            
            if show_button:
                print(Fore.YELLOW + "⚠ Navega a la categoría deseada y haz click en el botón verde para continuar" + Fore.RESET)
                
                # Crear y ejecutar el botón en un hilo separado
                threading.Thread(target=create_floating_button, daemon=True).start()
                
                # Esperar activamente pero sin consumir muchos recursos
                while not button_clicked:
                    time.sleep(0.1)
                
                # Continuar con scraping
                wait.until(EC.presence_of_element_located((By.CLASS_NAME, 'itemsBlock')))
            
        except TimeoutException:
            print(Fore.RED + "✖ Error: No se ha iniciado sesión" + Fore.RESET)
            raise
        
        return True
        
    except Exception as e:
        print(Fore.RED + f"❌ Error inesperado: {str(e)}" + Fore.RESET)
        return False