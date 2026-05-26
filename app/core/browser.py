import os
from selenium import webdriver
from selenium.webdriver.chrome.options import Options

def get_chrome_driver(download_dir=None):
    """
    Inicializa y configura una instancia de Selenium WebDriver para Chrome
    de manera centralizada con opciones optimizadas para el scraping y las descargas.
    """
    chrome_options = Options()
    chrome_options.add_argument("--start-maximized")
    chrome_options.add_argument("--disable-extensions")
    chrome_options.add_argument("--log-level=3")
    chrome_options.add_experimental_option("excludeSwitches", ["enable-logging"])
    chrome_options.add_argument("--disable-logging")
    chrome_options.add_argument("--disable-dev-shm-usage")
    
    # Configurar directorio de descarga
    if not download_dir:
        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        download_dir = os.path.join(base_dir, "productos_coronel")
        
    os.makedirs(download_dir, exist_ok=True)
    
    chrome_options.add_experimental_option("prefs", {
        "download.default_directory": os.path.normpath(download_dir),
        "download.prompt_for_download": False,
        "download.directory_upgrade": True,
        "safebrowsing.enabled": True
    })
    
    driver = webdriver.Chrome(options=chrome_options)
    return driver
