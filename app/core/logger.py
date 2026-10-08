"""
Módulo centralizado de logging para Scraping-Coronel.
Registra todos los errores, excepciones no capturadas y advertencias de la consola
en archivos persistentes dentro del directorio 'logs/'.
"""

import os
import sys
import logging
from logging.handlers import RotatingFileHandler
from datetime import datetime
from typing import Optional
from colorama import Fore, Style

# Asegurar encoding UTF-8 seguro en Windows
try:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
except Exception:
    pass

# Directorio base del proyecto
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
LOGS_DIR = os.path.join(BASE_DIR, "logs")
ERROR_LOG_PATH = os.path.join(LOGS_DIR, "errores.log")
ACTIVITY_LOG_PATH = os.path.join(LOGS_DIR, "actividad.log")

# Asegurar que la carpeta logs exista
os.makedirs(LOGS_DIR, exist_ok=True)

# Logger principal de la aplicación
logger = logging.getLogger("ScrapingCoronel")
logger.setLevel(logging.INFO)

# Evitar duplicar handlers si se importa múltiples veces
if not logger.handlers:
    # Formateador detallado para errores
    error_formatter = logging.Formatter(
        fmt="%(asctime)s | %(levelname)-8s | [%(filename)s:%(lineno)d] | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )

    # Handler para errores (Rotating: máx 5MB, hasta 5 archivos de respaldo)
    error_handler = RotatingFileHandler(
        ERROR_LOG_PATH,
        maxBytes=5 * 1024 * 1024,
        backupCount=5,
        encoding="utf-8"
    )
    error_handler.setLevel(logging.ERROR)
    error_handler.setFormatter(error_formatter)
    logger.addHandler(error_handler)

    # Handler para actividad general
    activity_handler = RotatingFileHandler(
        ACTIVITY_LOG_PATH,
        maxBytes=5 * 1024 * 1024,
        backupCount=3,
        encoding="utf-8"
    )
    activity_handler.setLevel(logging.INFO)
    activity_handler.setFormatter(error_formatter)
    logger.addHandler(activity_handler)


class StderrTee:
    """
    Captura todo lo que se escriba en sys.stderr (tracebacks crudos de Python,
    advertencias de Selenium, etc.) y lo guarda en logs/errores.log sin perder
    la salida en la consola.
    """
    def __init__(self, original_stderr):
        self.original_stderr = original_stderr
        self.buffer = ""

    def write(self, text):
        if self.original_stderr:
            try:
                self.original_stderr.write(text)
            except Exception:
                pass
        
        # Guardar en log si contiene texto significativo
        if text and text.strip():
            try:
                timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                with open(ERROR_LOG_PATH, "a", encoding="utf-8", errors="replace") as f:
                    f.write(f"{timestamp} | STDERR   | {text.rstrip()}\n")
            except Exception:
                pass

    def flush(self):
        if self.original_stderr:
            try:
                self.original_stderr.flush()
            except Exception:
                pass

    def reconfigure(self, **kwargs):
        if hasattr(self.original_stderr, "reconfigure"):
            try:
                self.original_stderr.reconfigure(**kwargs)
            except Exception:
                pass


def _manejador_excepciones_no_controladas(exc_type, exc_value, exc_traceback):
    """
    Hook global para registrar cualquier excepción no atrapada que intente
    cerrar el programa abruptamente.
    """
    if issubclass(exc_type, KeyboardInterrupt):
        # Permitir que Ctrl+C funcione normalmente
        sys.__excepthook__(exc_type, exc_value, exc_traceback)
        return

    logger.critical(
        f"CRASH INESPERADO: {exc_type.__name__}: {exc_value}",
        exc_info=(exc_type, exc_value, exc_traceback)
    )
    try:
        print(Fore.RED + "\n" + "=" * 60 + Style.RESET_ALL)
        print(Fore.RED + "[!] Ocurrió un error inesperado que detuvo la ejecución." + Style.RESET_ALL)
        print(Fore.YELLOW + f"Detalles completos registrados en:\n   {ERROR_LOG_PATH}" + Style.RESET_ALL)
        print(Fore.RED + "=" * 60 + "\n" + Style.RESET_ALL)
    except Exception:
        pass


def inicializar_sistema_logs():
    """
    Activa la captura de errores en consola y el hook de excepciones globales.
    """
    # 1. Configurar hook de excepciones no controladas
    sys.excepthook = _manejador_excepciones_no_controladas

    # 2. Interceptar sys.stderr para que nada escape al archivo de log
    if not isinstance(sys.stderr, StderrTee):
        sys.stderr = StderrTee(sys.stderr)


def registrar_error(mensaje: str, excepcion: Optional[Exception] = None):
    """
    Función utilitaria para registrar un error explícito en logs/errores.log
    con traceback automático si se provee la excepción.
    """
    if excepcion:
        logger.error(f"{mensaje} | Detalle: {type(excepcion).__name__}: {excepcion}", exc_info=True)
    else:
        logger.error(mensaje)


def registrar_info(mensaje: str):
    """Registra información operativa en logs/actividad.log"""
    logger.info(mensaje)
