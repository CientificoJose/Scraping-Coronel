import time
import os
import shutil
from datetime import datetime
import logging
from typing import List, Dict, Any, Tuple, Optional

from selenium import webdriver
from selenium.webdriver.chrome.options import Options as ChromeOptions
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException, WebDriverException
from webdriver_manager.chrome import ChromeDriverManager # Para manejar el driver automáticamente

import requests # Para descargar imágenes
import urllib3 # Para silenciar warnings de requests

from config import settings, credentials
from core import data_manager # Para obtener códigos de barra, etc.

# Silenciar advertencias de InsecureRequestWarning de urllib3 al descargar imágenes con verify=False
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

logger = logging.getLogger(__name__)

class CoronelScraper:
    """
    Clase para encapsular la lógica de scraping del sitio Coronel Mayorista.
    """
    def __init__(self, headless=True):
        self.driver: Optional[webdriver.Chrome] = None
        self.headless = headless
        self.logged_in = False
        self.coronel_creds = credentials.get_coronel_credentials()

    def _initialize_driver(self):
        """Inicializa el WebDriver de Selenium."""
        logger.info("Inicializando WebDriver de Chrome...")
        chrome_options = ChromeOptions()
        if self.headless:
            chrome_options.add_argument("--headless")
        chrome_options.add_argument("--start-maximized")
        chrome_options.add_argument("--disable-extensions")
        chrome_options.add_argument('--log-level=3')
        chrome_options.add_experimental_option('excludeSwitches', ['enable-logging'])
        chrome_options.add_argument("--disable-logging") # General
        chrome_options.add_argument("--no-sandbox") # Necesario para algunos entornos Linux/Docker
        chrome_options.add_argument("--disable-dev-shm-usage") # Necesario para algunos entornos Linux/Docker

        # Preferencias para descarga de archivos (Excel)
        # La ruta de descarga se configurará para que sea settings.PRODUCTOS_CORONEL_DIR
        # Sin embargo, Selenium no siempre puede controlar bien las descargas si hay diálogos del SO.
        # La estrategia de buscar en Downloads es más robusta.
        prefs = {
            "download.default_directory": settings.PRODUCTOS_CORONEL_DIR,
            "download.prompt_for_download": False,
            "download.directory_upgrade": True,
            "safebrowsing.enabled": True
        }
        chrome_options.add_experimental_option("prefs", prefs)

        try:
            service = ChromeService(ChromeDriverManager().install())
            self.driver = webdriver.Chrome(service=service, options=chrome_options)
            logger.info("WebDriver de Chrome inicializado correctamente.")
        except WebDriverException as e:
            logger.error(f"Error al inicializar WebDriver con webdriver-manager: {e}", exc_info=True)
            logger.info("Intentando inicializar WebDriver con ruta de driver por defecto (si está en PATH)...")
            try:
                self.driver = webdriver.Chrome(options=chrome_options) # Intento fallback
                logger.info("WebDriver de Chrome inicializado correctamente (fallback).")
            except WebDriverException as e_fallback:
                logger.critical(f"Error crítico al inicializar WebDriver (fallback): {e_fallback}", exc_info=True)
                raise  # Relanzar la excepción si falla críticamente

    def login(self) -> bool:
        """
        Realiza el login en Coronel Mayorista.
        Retorna True si el login fue exitoso, False en caso contrario.
        """
        if not self.driver:
            self._initialize_driver()
            if not self.driver: # Si aún no hay driver después de inicializar
                return False

        if self.logged_in:
            logger.info("Ya se ha iniciado sesión previamente.")
            return True

        logger.info("Iniciando proceso de login en Coronel Mayorista...")
        try:
            self.driver.get(settings.LOGIN_URL)
            wait = WebDriverWait(self.driver, settings.DEFAULT_TIMEOUT)

            cuit_field = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, 'input[formcontrolname="usuarioCuit"]')))
            cuit_field.clear()
            cuit_field.send_keys(self.coronel_creds['cuit'])
            logger.info(f"CUIT ingresado: {self.coronel_creds['cuit'][:4]}...")


            password_field = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, 'input[formcontrolname="usuarioPassword"]')))
            password_field.clear()
            password_field.send_keys(self.coronel_creds['password'])
            logger.info("Contraseña ingresada.")

            login_button = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, 'button.btnIngresar')))
            login_button.click()

            # Verificación de login exitoso
            wait.until(EC.url_contains('/#/home'))
            wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, 'li.nav-item.nav-usuario')))

            self.logged_in = True
            logger.info("Login en Coronel Mayorista exitoso.")
            return True

        except TimeoutException:
            logger.error("Timeout durante el login. No se pudo encontrar algún elemento o verificar la URL de home.", exc_info=True)
            # Capturar screenshot podría ser útil aquí para depuración
            # self.driver.save_screenshot("error_login_timeout.png")
        except Exception as e:
            logger.error(f"Error inesperado durante el login: {e}", exc_info=True)

        self.logged_in = False
        return False

    def descargar_lista_precios_excel(self) -> bool:
        """
        Navega a la sección de lista de precios y descarga el archivo Excel.
        Mueve el archivo descargado a la carpeta definida en settings.PRODUCTOS_CORONEL_DIR.
        Retorna True si la descarga y movimiento fueron exitosos, False en caso contrario.
        """
        if not self.logged_in:
            logger.warning("Se requiere login para descargar la lista de precios. Intentando loguear...")
            if not self.login():
                return False

        if not self.driver: # Asegurar que el driver exista
            logger.error("Driver no inicializado. No se puede descargar lista de precios.")
            return False

        logger.info("Iniciando descarga de la lista de precios en formato Excel...")
        download_target_dir = settings.PRODUCTOS_CORONEL_DIR
        os.makedirs(download_target_dir, exist_ok=True) # Asegurar que el directorio exista

        try:
            self.driver.get(settings.LISTA_PRECIOS_URL)
            wait = WebDriverWait(self.driver, settings.DEFAULT_TIMEOUT + 5) # Un poco más de tiempo para esta página

            export_button = wait.until(EC.element_to_be_clickable((By.XPATH, "//button[contains(@class, 'btn-exportar')]")))
            export_button.click()
            logger.info("Botón 'Exportar' clickeado.")

            # Espera corta para que aparezca el menú desplegable
            time.sleep(1)

            excel_option = wait.until(EC.element_to_be_clickable((By.XPATH, "//button[@mat-menu-item]//span[contains(text(), 'Excel')]/..")))
            excel_option.click()
            logger.info("Opción 'Excel' seleccionada para la descarga.")

            # Esperar a que la descarga se complete. Esta es la parte más tricky.
            # La estrategia de verificar el archivo más nuevo en 'Downloads' es más robusta.
            time.sleep(10) # Dar un tiempo generoso para que la descarga comience y termine. Ajustar si es necesario.

            # Mover el archivo desde la carpeta de descargas del sistema a nuestro directorio de datos.
            # Esto asume que el navegador está configurado para descargar sin preguntar.
            downloads_folder = os.path.expanduser("~\\Downloads") # Estándar para Windows. Ajustar para otros OS si es necesario.
            if not os.path.isdir(downloads_folder): # Fallback para otros OS o si no es la ruta esperada
                downloads_folder = os.path.join(os.path.expanduser("~"), "Downloads")
                if not os.path.isdir(downloads_folder):
                    logger.error(f"No se pudo determinar la carpeta de descargas del sistema. Se buscará en {download_target_dir}")
                    downloads_folder = download_target_dir # Buscar en el directorio de destino (si Selenium lo puso ahí)


            logger.info(f"Buscando archivo descargado en: {downloads_folder} (y alternativamente en {download_target_dir})")

            # Buscar el archivo más reciente que contenga "Lista de Precios" y sea .xlsx
            # Intentar primero en la carpeta de descargas del sistema, luego en nuestro directorio de destino
            # (por si Selenium logró descargarlo directamente allí gracias a las prefs).
            found_file_path = None
            possible_folders = [downloads_folder, download_target_dir]

            for folder_to_check in possible_folders:
                if not os.path.isdir(folder_to_check): continue
                try:
                    excel_files = [
                        os.path.join(folder_to_check, f)
                        for f in os.listdir(folder_to_check)
                        if "lista de precios" in f.lower() and f.lower().endswith('.xlsx') and not f.startswith('~$')
                    ]
                    if excel_files:
                        latest_file = max(excel_files, key=os.path.getctime)
                        if os.path.exists(latest_file):
                            found_file_path = latest_file
                            logger.info(f"Archivo Excel candidato encontrado: {found_file_path}")
                            break # Encontrado, salir del bucle de carpetas
                except Exception as e_list:
                    logger.warning(f"Error listando archivos en {folder_to_check}: {e_list}")


            if found_file_path:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                new_filename = f"lista_precios_coronel_{timestamp}.xlsx"
                final_path = os.path.join(download_target_dir, new_filename)

                shutil.move(found_file_path, final_path)
                logger.info(f"Lista de precios descargada y movida exitosamente a: {final_path}")
                return True
            else:
                logger.error("No se encontró el archivo Excel descargado que coincida con los criterios.")
                return False

        except TimeoutException:
            logger.error("Timeout durante la descarga de la lista de precios.", exc_info=True)
        except Exception as e:
            logger.error(f"Error inesperado descargando la lista de precios: {e}", exc_info=True)
        return False

    def _extraer_info_producto_detalle(self, descargar_imagenes_localmente: bool) -> Optional[Dict[str, Any]]:
        """
        Extrae información de la página de detalle de un producto.
        Asume que el driver ya está en la página de detalle.
        """
        if not self.driver: return None
        wait = WebDriverWait(self.driver, settings.DEFAULT_TIMEOUT)

        try:
            # Precio
            precio = "0"
            try:
                # Precio tachado (oferta)
                precio_elem = self.driver.find_element(By.CSS_SELECTOR, "span.tachado")
                precio = precio_elem.text.strip()
            except NoSuchElementException:
                # Precio normal (sin oferta)
                try:
                    precio_elem = self.driver.find_element(By.CSS_SELECTOR, "span.sintachar")
                    precio = precio_elem.text.strip()
                except NoSuchElementException:
                    logger.warning("No se pudo encontrar el precio del producto en detalle (ni tachado ni sin tachar).")

            # Código
            codigo_original = ""
            try:
                codigo_elem = self.driver.find_element(By.CLASS_NAME, "codigo") # ej: "Código: ABC-123"
                codigo_original = codigo_elem.text.replace("Código:", "").strip()
            except NoSuchElementException:
                logger.warning("No se pudo encontrar el código del producto en detalle.")
                return None # Código es esencial

            # Descripción
            descripcion = ""
            try:
                desc_elem = self.driver.find_element(By.CLASS_NAME, "description")
                descripcion = desc_elem.text.strip()
            except NoSuchElementException:
                logger.warning(f"No se encontró descripción para el producto {codigo_original}.")

            # Categorías (breadcrumb)
            categoria_principal = None
            subcategoria = None
            try:
                breadcrumb_elem = self.driver.find_element(By.CSS_SELECTOR, ".breadcrumb")
                categorias_elems = breadcrumb_elem.find_elements(By.CSS_SELECTOR, ".breadcrumb-item.breadcrumb2")
                categorias_text = [span.text.strip() for span in categorias_elems if span.text.strip()]
                if categorias_text:
                    categoria_principal = categorias_text[0]
                if len(categorias_text) > 1:
                    subcategoria = categorias_text[1]
            except NoSuchElementException:
                logger.warning(f"No se encontró breadcrumb de categorías para {codigo_original}.")

            # Variante (Adicional)
            variante_texto = ""
            codigo_final = codigo_original # Código que se usará, puede incluir la variante
            try:
                adicional_elem = self.driver.find_element(By.CLASS_NAME, "adicional") # ej: "ORO", "100ML"
                variante_texto = adicional_elem.text.strip().upper().replace(' ', '').replace('/', '-').replace('\\', '-')
                if variante_texto:
                    codigo_final = f"{codigo_original}-{variante_texto}"
            except NoSuchElementException:
                pass # No todos los productos tienen variante

            # Imagen
            imagen_url = None
            imagen_local_rel_path = None # Ruta relativa a settings.IMG_SCRAPING_DIR
            try:
                img_elem = wait.until(EC.presence_of_element_located((By.CLASS_NAME, "ngxImageZoomThumbnail")))
                imagen_url = img_elem.get_attribute("src")

                if descargar_imagenes_localmente and imagen_url:
                    os.makedirs(settings.IMG_SCRAPING_DIR, exist_ok=True)
                    img_name = f"{codigo_final}.jpg" # Usar código final (con variante) para el nombre
                    img_local_abs_path = os.path.join(settings.IMG_SCRAPING_DIR, img_name)

                    try:
                        response = requests.get(imagen_url, stream=True, timeout=10, verify=False)
                        if response.status_code == 200:
                            with open(img_local_abs_path, 'wb') as f:
                                for chunk in response.iter_content(1024):
                                    f.write(chunk)
                            imagen_local_rel_path = img_name # Guardar solo el nombre del archivo
                            logger.debug(f"Imagen descargada para {codigo_final} en {img_local_abs_path}")
                        else:
                            logger.warning(f"Error al descargar imagen {imagen_url} (status {response.status_code}) para {codigo_final}")
                    except requests.RequestException as req_e:
                        logger.error(f"Error de red descargando imagen {imagen_url} para {codigo_final}: {req_e}")
            except TimeoutException:
                logger.warning(f"No se encontró miniatura de imagen (ngxImageZoomThumbnail) para {codigo_final}.")
            except Exception as img_e:
                logger.error(f"Error procesando imagen para {codigo_final}: {img_e}", exc_info=True)

            # Código de barras (consultar a data_manager usando el código original sin variante)
            codigo_de_barras = data_manager.obtener_codigo_barra_por_codigo_producto(codigo_original)

            producto_info = {
                'codigo': codigo_final,
                'codigo_original_excel': codigo_original, # Para referencia si se necesita
                'descripcion': descripcion,
                'precio': precio,
                'imagen_url': imagen_url,
                'imagen_local': imagen_local_rel_path, # Ruta relativa o None
                'variante': variante_texto if variante_texto else None,
                'categoria': categoria_principal,
                'subcategoria': subcategoria,
                'codigo_de_barras': codigo_de_barras,
                'stock': 999999 # Stock por defecto para productos scrapeados (como en actualizar_stock.py)
                                # Esto podría ser configurable o ajustado después.
            }
            logger.info(f"Producto extraído de detalle: {codigo_final} - {descripcion[:30]}...")
            return producto_info

        except Exception as e:
            logger.error(f"Error extrayendo detalles del producto: {e}", exc_info=True)
            return None

    def scrapear_productos_categoria_actual(self, descargar_imagenes: bool, callback_producto_encontrado=None, callback_progreso_pagina=None) -> List[Dict[str, Any]]:
        """
        Extrae información de todos los productos de la categoría/página actual en el navegador.
        Navega a la página de detalle de cada producto.
        Args:
            descargar_imagenes (bool): Si se deben descargar las imágenes localmente.
            callback_producto_encontrado (function): Función a llamar después de procesar cada producto.
                                                     Recibe el diccionario del producto.
            callback_progreso_pagina (function): Función a llamar con el progreso de la página actual.
                                                 Recibe (productos_procesados_en_pagina, total_productos_en_pagina).
        Returns:
            Lista de diccionarios, cada uno representando un producto scrapeado.
        """
        if not self.driver:
            logger.error("Driver no inicializado. No se puede scrapear.")
            return []

        productos_scrapeados_pagina = []
        try:
            wait = WebDriverWait(self.driver, settings.DEFAULT_TIMEOUT)
            wait.until(EC.presence_of_element_located((By.CLASS_NAME, "itemsBlock")))

            # Obtener todos los elementos de producto en la página actual
            # Es importante re-localizar estos elementos en cada iteración si la página cambia (al volver de detalle)
            # Por ahora, asumimos que el scrapeo de una página se hace sin salir de ella para los links,
            # sino que se abren en nueva pestaña o se vuelve. La estrategia aquí será click->extraer->volver.

            product_card_elements = self.driver.find_elements(By.CSS_SELECTOR, ".col-art .card-product")
            num_productos_en_pagina = len(product_card_elements)
            logger.info(f"Encontrados {num_productos_en_pagina} productos en la página actual.")

            if num_productos_en_pagina == 0:
                return []

            # Iterar por índice porque la lista de elementos puede volverse "stale" al navegar
            for i in range(num_productos_en_pagina):
                # Re-localizar los elementos en cada iteración para evitar StaleElementReferenceException
                product_cards = self.driver.find_elements(By.CSS_SELECTOR, ".col-art .card-product")
                if i >= len(product_cards): # Si por alguna razón hay menos elementos ahora
                    logger.warning(f"Se esperaba el producto índice {i} pero solo hay {len(product_cards)}.")
                    break

                card = product_cards[i]

                try:
                    # Scroll suave hacia el elemento para asegurar que sea clickeable
                    self.driver.execute_script("arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});", card)
                    time.sleep(0.5) # Pequeña pausa para el scroll

                    # Click en la tarjeta del producto para ir a la página de detalle
                    # Usar JavaScript click si el click normal falla, es más robusto a veces.
                    try:
                        wait.until(EC.element_to_be_clickable(card))
                        card.click()
                    except:
                        logger.warning("Click normal en tarjeta de producto falló, intentando con JavaScript click.")
                        self.driver.execute_script("arguments[0].click();", card)

                    logger.debug(f"Navegando a detalle del producto {i+1}/{num_productos_en_pagina}...")

                    # Esperar a que la página de detalle cargue (un elemento distintivo)
                    wait.until(EC.presence_of_element_located((By.CLASS_NAME, "precios"))) # Clase "precios" en detalle

                    # Extraer información del detalle
                    info_producto = self._extraer_info_producto_detalle(descargar_imagenes)

                    if info_producto:
                        productos_scrapeados_pagina.append(info_producto)
                        if callback_producto_encontrado:
                            callback_producto_encontrado(info_producto)

                    # Volver a la página de listado de productos
                    self.driver.back()

                    # Esperar a que la página de listado cargue de nuevo
                    wait.until(EC.presence_of_element_located((By.CLASS_NAME, "itemsBlock")))
                    logger.debug("Regreso a la página de listado.")
                    time.sleep(0.5) # Pequeña pausa después de volver

                except TimeoutException:
                    logger.error(f"Timeout procesando el producto índice {i} en la página. Saltando.", exc_info=True)
                    # Si hay un error, es importante volver a la página de listado si es posible
                    current_url = self.driver.current_url
                    if "/#/articulos" not in current_url: # Si no estamos en la de artículos
                        self.driver.get(settings.ARTICULOS_URL) # Forzar vuelta a una URL conocida de listado
                        wait.until(EC.presence_of_element_located((By.CLASS_NAME, "itemsBlock")))
                except Exception as e_prod:
                    logger.error(f"Error procesando el producto índice {i} en la página: {e_prod}", exc_info=True)
                    # Intentar volver a la página de listado
                    if "/#/articulos" not in self.driver.current_url:
                        try:
                            self.driver.back()
                            wait.until(EC.presence_of_element_located((By.CLASS_NAME, "itemsBlock")))
                        except:
                            self.driver.get(settings.ARTICULOS_URL) # Fallback
                            wait.until(EC.presence_of_element_located((By.CLASS_NAME, "itemsBlock")))

                if callback_progreso_pagina:
                    callback_progreso_pagina(i + 1, num_productos_en_pagina)

            return productos_scrapeados_pagina

        except Exception as e:
            logger.error(f"Error general al scrapear productos de la categoría actual: {e}", exc_info=True)
            return []


    def scrapear_todos_productos_sitio(self, url_categoria_inicial: Optional[str]=None, descargar_imagenes: bool = False, callback_producto_encontrado=None, callback_progreso_global=None, callback_progreso_pagina=None) -> List[Dict[str, Any]]:
        """
        Extrae información de productos de TODAS las páginas de una categoría o del sitio.
        Args:
            url_categoria_inicial (str, opcional): URL de la primera página de la categoría a scrapear.
                                                   Si es None, usa settings.ARTICULOS_URL.
            descargar_imagenes (bool): Si se deben descargar imágenes.
            callback_producto_encontrado (function): Se pasa a scrapear_productos_categoria_actual.
            callback_progreso_global (function): Llamado con (pagina_actual, total_paginas_estimado).
                                                 Total_paginas_estimado puede ser None si no se puede determinar.
            callback_progreso_pagina (function): Se pasa a scrapear_productos_categoria_actual.
        Returns:
            Lista de todos los productos encontrados.
        """
        if not self.logged_in:
            logger.warning("Se requiere login para scrapear todos los productos. Intentando loguear...")
            if not self.login():
                return []

        if not self.driver:
            logger.error("Driver no inicializado.")
            return []

        start_url = url_categoria_inicial if url_categoria_inicial else settings.ARTICULOS_URL
        self.driver.get(start_url)
        logger.info(f"Iniciando scraping de todos los productos desde: {start_url}")

        todos_los_productos_del_sitio = []
        pagina_actual_num = 1

        # TODO: Estimar total de páginas si es posible para el callback_progreso_global

        while True:
            logger.info(f"Procesando página {pagina_actual_num}...")
            if callback_progreso_global:
                callback_progreso_global(pagina_actual_num, None) # Total páginas es difícil de saber a priori aquí

            productos_de_esta_pagina = self.scrapear_productos_categoria_actual(descargar_imagenes, callback_producto_encontrado, callback_progreso_pagina)

            if not productos_de_esta_pagina:
                logger.info(f"No se encontraron productos en la página {pagina_actual_num} o error. Fin del scraping de esta categoría/sitio.")
                break

            todos_los_productos_del_sitio.extend(productos_de_esta_pagina)
            logger.info(f"Acumulados {len(todos_los_productos_del_sitio)} productos en total.")

            # Intentar ir a la siguiente página
            try:
                self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);") # Scroll down
                time.sleep(0.5)

                wait = WebDriverWait(self.driver, settings.DEFAULT_TIMEOUT)
                next_button = wait.until(EC.element_to_be_clickable((By.ID, "siguiente")))

                if next_button.get_attribute("disabled") or "btn-shadow" not in next_button.get_attribute("class"):
                    logger.info("Botón 'siguiente' deshabilitado o inactivo. Se alcanzó la última página.")
                    break

                current_url_before_click = self.driver.current_url
                self.driver.execute_script("arguments[0].click();", next_button) # JS click es más robusto

                # Esperar a que la URL cambie o que el contenido de la página cambie (ej. primer producto diferente)
                try:
                    wait.until(lambda d: d.current_url != current_url_before_click or \
                                   (len(d.find_elements(By.CSS_SELECTOR, ".col-art .card-product")) > 0 and \
                                    d.find_elements(By.CSS_SELECTOR, ".col-art .card-product")[0].text != \
                                    product_cards[0].text if productos_de_esta_pagina else False) # Compara si el primer producto cambió
                    )
                except TimeoutException:
                    logger.warning("Timeout esperando cambio de URL o contenido después de click en 'siguiente'. Asumiendo última página.")
                    break

                pagina_actual_num += 1
                time.sleep(1) # Pausa para que la nueva página cargue completamente

            except TimeoutException:
                logger.info("No se encontró el botón 'siguiente' o no era clickeable. Se asume última página.")
                break
            except Exception as e_next:
                logger.error(f"Error al intentar ir a la siguiente página: {e_next}", exc_info=True)
                break

        logger.info(f"Scraping completo del sitio/categoría finalizado. Total de productos recolectados: {len(todos_los_productos_del_sitio)}")
        return todos_los_productos_del_sitio

    def obtener_stock_productos_rapido(self, url_categoria_inicial: Optional[str]=None) -> List[Dict[str, Any]]:
        """
        Realiza un scraping más rápido enfocado solo en obtener códigos de producto y asumir stock "infinito".
        No entra a la página de detalle de cada producto, extrae de la grilla.
        Esta función es similar a la lógica de `actualizar_stock.py`.
        """
        if not self.logged_in:
            if not self.login(): return []
        if not self.driver: return []

        start_url = url_categoria_inicial if url_categoria_inicial else settings.ARTICULOS_URL
        self.driver.get(start_url)
        logger.info(f"Iniciando scraping rápido de stock desde: {start_url}")

        productos_con_stock = []
        pagina_actual_num = 1

        while True:
            logger.info(f"Procesando página {pagina_actual_num} para stock rápido...")
            try:
                wait = WebDriverWait(self.driver, settings.DEFAULT_TIMEOUT)
                wait.until(EC.presence_of_element_located((By.CLASS_NAME, "itemsBlock")))

                product_cards = self.driver.find_elements(By.CSS_SELECTOR, ".col-art .card-product")
                if not product_cards:
                    logger.info(f"No se encontraron tarjetas de producto en la página {pagina_actual_num}.")
                    break

                for card in product_cards:
                    try:
                        codigo_elem = card.find_element(By.CSS_SELECTOR, ".span-codigo")
                        codigo = codigo_elem.text.replace("Código:", "").strip()

                        variante = ""
                        try:
                            adicional_elem = card.find_element(By.CSS_SELECTOR, ".adicional span")
                            adicional_text = adicional_elem.text.strip().upper().replace(' ', '').replace('/', '-').replace('\\', '-')
                            if adicional_text:
                                variante = adicional_text
                                codigo = f"{codigo}-{variante}"
                        except NoSuchElementException:
                            pass # Sin variante

                        productos_con_stock.append({'codigo': codigo, 'stock': 999999}) # Stock "infinito"
                    except NoSuchElementException:
                        logger.warning("No se pudo extraer código de una tarjeta de producto en la grilla.")
                    except Exception as e_card:
                        logger.error(f"Error extrayendo datos de tarjeta en grilla: {e_card}")

                # Navegar a la siguiente página
                self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                time.sleep(0.5)
                next_button = wait.until(EC.element_to_be_clickable((By.ID, "siguiente")))
                if next_button.get_attribute("disabled") or "btn-shadow" not in next_button.get_attribute("class"):
                    break
                self.driver.execute_script("arguments[0].click();", next_button)
                pagina_actual_num += 1
                time.sleep(1)

            except TimeoutException:
                logger.info("Timeout o no más páginas en scraping rápido de stock.")
                break
            except Exception as e_page:
                logger.error(f"Error en página {pagina_actual_num} durante scraping rápido de stock: {e_page}")
                break

        logger.info(f"Scraping rápido de stock finalizado. {len(productos_con_stock)} productos con stock 'infinito' identificados.")
        return productos_con_stock


    def close(self):
        """Cierra el WebDriver."""
        if self.driver:
            try:
                logger.info("Cerrando WebDriver...")
                self.driver.quit()
                logger.info("WebDriver cerrado.")
            except Exception as e:
                logger.error(f"Error al cerrar WebDriver: {e}", exc_info=True)
            finally:
                self.driver = None
                self.logged_in = False

# --- Ejemplo de uso (para pruebas) ---
if __name__ == '__main__':
    # Configurar logging para ver salidas
    if not logging.getLogger().hasHandlers():
        from config.logging_config import setup_logging
        setup_logging()

    logger.info("Probando el CoronelScraper...")

    # Crear instancia del scraper (headless=False para ver el navegador)
    scraper = CoronelScraper(headless=False)

    try:
        # 1. Login
        if scraper.login():
            logger.info("Login exitoso desde el script de prueba.")

            # 2. Descargar lista de precios (opcional)
            # if scraper.descargar_lista_precios_excel():
            #     logger.info("Descarga de Excel exitosa desde prueba.")
            #     # Inicializar BD desde Excel para que los códigos de barra estén disponibles
            #     if data_manager.inicializar_base_de_datos_desde_excel():
            #         logger.info("Base de datos inicializada desde el Excel descargado.")
            #     else:
            #         logger.error("Fallo al inicializar la BD desde el Excel.")
            # else:
            #     logger.error("Fallo en la descarga de Excel desde prueba.")


            # 3. Scrapear productos de la categoría actual (navega manualmente a una antes de correr)
            # logger.info("Navega a una categoría en el navegador y luego presiona Enter aquí para continuar...")
            # input() # Pausa para navegación manual

            # def mi_callback_producto(producto):
            #     print(f"CALLBACK PRODUCTO: {producto.get('codigo')} - {producto.get('descripcion')[:30]}")
            #     # Aquí se podría llamar a data_manager.guardar_o_actualizar_producto(producto)

            # def mi_callback_progreso_pagina(proc, total):
            #     print(f"CALLBACK PAGINA: {proc}/{total} productos en página actual.")

            # print("\n--- Probando scrapear_productos_categoria_actual ---")
            # productos_pagina_actual = scraper.scrapear_productos_categoria_actual(
            #     descargar_imagenes=False, # True para probar descarga de imágenes
            #     callback_producto_encontrado=mi_callback_producto,
            #     callback_progreso_pagina=mi_callback_progreso_pagina
            # )
            # logger.info(f"Total productos scrapeados de la página actual: {len(productos_pagina_actual)}")
            # if productos_pagina_actual:
            #      logger.info(f"Primer producto de página actual: {productos_pagina_actual[0].get('codigo')}")


            # 4. Scrapear todos los productos del sitio (o desde una URL de categoría)
            # print("\n--- Probando scrapear_todos_productos_sitio ---")
            # def mi_callback_progreso_global(pag_actual, pag_total):
            #     print(f"CALLBACK GLOBAL: Procesando página {pag_actual} (Total estimado: {pag_total if pag_total else 'N/A'})")

            # todos_los_productos = scraper.scrapear_todos_productos_sitio(
            #     # url_categoria_inicial="https://www.coronelmayorista.com/#/articulos?page=1&CAT=278&MAR=0&VIEW_TYPE=GRID_VI&ORDER=ORD%3DASC&DES=&BUSCAR_POR=DES", # Ejemplo de URL de categoría
            #     descargar_imagenes=False,
            #     callback_producto_encontrado=mi_callback_producto,
            #     callback_progreso_global=mi_callback_progreso_global,
            #     callback_progreso_pagina=mi_callback_progreso_pagina
            # )
            # logger.info(f"Total de productos scrapeados del sitio: {len(todos_los_productos)}")
            # if todos_los_productos:
            #     # Guardar en BD
            #     logger.info("Guardando todos los productos en la base de datos...")
            #     num_guardados = data_manager.guardar_multiples_productos(todos_los_productos)
            #     logger.info(f"{num_guardados} productos guardados/actualizados en la BD.")
            # else:
            #     logger.warning("No se scrapearon productos del sitio.")


            # 5. Probar scraping rápido de stock
            print("\n--- Probando obtener_stock_productos_rapido ---")
            stock_rapido = scraper.obtener_stock_productos_rapido()
            logger.info(f"Obtenidos {len(stock_rapido)} productos con stock 'infinito' (scraping rápido).")
            if stock_rapido:
                logger.info("Ejemplos de stock rápido:")
                for p_stock in stock_rapido[:5]:
                    logger.info(f"  Código: {p_stock['codigo']}, Stock: {p_stock['stock']}")


        else:
            logger.error("Login fallido desde el script de prueba.")

    except Exception as e_main:
        logger.critical(f"Error crítico en la prueba del scraper: {e_main}", exc_info=True)
    finally:
        scraper.close()
        logger.info("Prueba del CoronelScraper finalizada.")
