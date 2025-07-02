import logging
import sys
import os

# Añadir el directorio raíz del proyecto al PYTHONPATH para asegurar que los módulos se encuentren.
# Esto es útil si se ejecuta main.py directamente desde la raíz.
# Si se instala como paquete, esto podría no ser necesario.
project_root = os.path.dirname(os.path.abspath(__file__))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from config.logging_config import setup_logging
from config import settings, credentials # Para asegurar que se carguen y validen

# Configurar el logging tan pronto como sea posible
setup_logging()
logger = logging.getLogger(__name__) # Obtener logger para este módulo

def run_application():
    """
    Punto de entrada principal para ejecutar la aplicación.
    """
    logger.info("=================================================")
    logger.info("    Iniciando Aplicación de Scraping y Gestión   ")
    logger.info("=================================================")

    # Verificar credenciales esenciales (ejemplo)
    tn_creds = credentials.get_tiendanube_credentials()
    if not tn_creds.get('access_token') or not tn_creds.get('store_id'):
        logger.critical("FALTAN CREDENCIALES DE TIENDANUBE. La aplicación podría no funcionar correctamente.")
        # Aquí se podría decidir si salir o continuar con funcionalidad limitada.
        # Por ahora, solo se loguea la advertencia/error.
    else:
        logger.info("Credenciales de Tiendanube cargadas.")

    coronel_creds = credentials.get_coronel_credentials()
    if not coronel_creds.get('cuit') or not coronel_creds.get('password'):
        logger.warning("Credenciales de Coronel Mayorista no encontradas o incompletas. El scraping podría fallar.")
    else:
        logger.info("Credenciales de Coronel Mayorista cargadas.")


    logger.info(f"Directorio base del proyecto: {settings.BASE_DIR}")
    logger.info(f"Directorio de datos: {settings.DATA_DIR}")
    logger.info(f"Base de datos SQLite en: {settings.DB_PATH}")

    # --- Inicialización de la GUI ---
    root = None  # Definir root fuera del try para el finally
    try:
        logger.info("Inicializando interfaz gráfica de usuario (GUI)...")

        # Intentar usar ttkthemes si está disponible para una apariencia mejorada
        tk_root: tk.Tk
        try:
            from ttkthemes import ThemedTk
            # Temas posibles: "arc", "plastik", "radiance", "blue", "clearlooks", "elegance", etc.
            # "arc" es un tema moderno y limpio.
            tk_root = ThemedTk(theme="arc", toplevel=True, themebg=True)
            logger.info("Usando ThemedTk con tema 'arc'.")
        except ImportError:
            logger.info("ttkthemes no encontrado. Usando Tkinter estándar.")
            tk_root = tk.Tk()
        except tk.TclError as e_theme:
            logger.warning(f"Error al aplicar tema ThemedTk: {e_theme}. Usando Tkinter estándar.")
            tk_root = tk.Tk()

        root = tk_root # Asignar a root para el finally

        from gui.app import AppController
        app_controller = AppController(root)
        app_controller.start() # Esto llamará a root.mainloop()

    except ImportError as e_gui:
        logger.critical(f"Error al importar componentes de la GUI: {e_gui}", exc_info=True)
        # Mostrar un error simple si Tkinter no está disponible o hay problemas mayores
        try:
            import tkinter as tk_error
            error_root = tk_error.Tk()
            error_root.withdraw() # Ocultar ventana principal de error
            tk_error.messagebox.showerror("Error de GUI", f"No se pudieron cargar componentes de la GUI: {e_gui}\n\nLa aplicación no puede continuar.")
            error_root.destroy()
        except:
            print(f"ERROR CRÍTICO DE GUI (ImportError): {e_gui}. Verifique su instalación de Python/Tkinter.")
        sys.exit(1)
    except Exception as e_start:
        logger.critical(f"Error crítico al iniciar la aplicación GUI: {e_start}", exc_info=True)
        try:
            import tkinter as tk_error_generic
            error_root_generic = tk_error_generic.Tk()
            error_root_generic.withdraw()
            tk_error_generic.messagebox.showerror("Error Crítico", f"Ocurrió un error inesperado al iniciar: {e_start}\n\nConsulte app.log para más detalles.")
            error_root_generic.destroy()
        except:
            print(f"ERROR CRÍTICO (Excepción genérica): {e_start}. Verifique su instalación de Python/Tkinter.")
        sys.exit(1)
    finally:
        logger.info("Saliendo de la aplicación.")
        # No es necesario root.destroy() aquí si AppController.start() maneja el mainloop
        # y el cierre se gestiona en _on_closing de AppController.


if __name__ == '__main__':
    # Verificar si se está ejecutando como un script congelado por PyInstaller
    # Esto es útil si se quiere cambiar el comportamiento, ej. logs
    if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
        logger.info(f"Aplicación ejecutándose como un paquete congelado (PyInstaller). MEIPASS: {sys._MEIPASS}")
        # Se podrían redirigir logs a un archivo específico en el directorio del usuario, etc.

    run_application()
