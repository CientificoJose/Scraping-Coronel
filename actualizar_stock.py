


#Usamos en local
from asyncio import wait
from selenium import webdriver
import time
from app.login import login
import os
import openpyxl
from datetime import datetime
from selenium.webdriver.chrome.options import Options

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
from colorama import Fore, Style

# Configurar opciones de Chrome
chrome_options = Options()
chrome_options.add_argument("--start-maximized")  # Abrir maximizado
chrome_options.add_argument('--log-level=3')  # Desactivar la mayoría de los logs
chrome_options.add_experimental_option('excludeSwitches', ['enable-logging'])  # Desactivar mensajes de logging
chrome_options.add_argument("--disable-logging")  # Desactivar logging
chrome_options.add_argument("--disable-dev-shm-usage")  # Desactivar mensajes de memoria compartida

# Inicializar driver
driver = webdriver.Chrome(options=chrome_options)

#Loguearnos
login_result = login(driver, False)
if not login_result:
    print(Fore.RED + "✖ Scraping cancelado por fallo en el login" + Fore.RESET)
    driver.quit()
    exit(1)  # Salir con código de error


