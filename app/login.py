from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from selenium.common.exceptions import TimeoutException
import time
from colorama import Fore
from tkinter import Tk, Button, Label
import threading


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



def login(driver):
    """
    Versión optimizada del login para Coronel Mayotista que:
    - Usa CUIT y password (no email)
    - Reemplaza time.sleep() con esperas inteligentes
    - Incluye verificación de login exitoso
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
        except TimeoutException:
            print(Fore.RED + "✖ Error: No se ha iniciadpo session" + Fore.RESET)
            raise
        
        
       # En tu función login, después del login exitoso:
        print(Fore.YELLOW + "⚠ Navega a la categoría deseada y haz click en el botón verde para continuar" + Fore.RESET)

        # Crear y ejecutar el botón en un hilo separado
        threading.Thread(target=create_floating_button, daemon=True).start()

        # Esperar activamente pero sin consumir muchos recursos
        while not button_clicked:
            time.sleep(0.1)

        # Continuar con scraping
        wait.until(EC.presence_of_element_located((By.CLASS_NAME, 'itemsBlock')))
        
        return True
        
    except Exception as e:
        print(Fore.RED + f"❌ Error inesperado: {str(e)}" + Fore.RESET)
        return False