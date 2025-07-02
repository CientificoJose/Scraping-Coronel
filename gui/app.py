import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
import logging
import threading
from queue import Queue # Para comunicación segura entre hilos

from .main_window import MainWindowView
from .dialogs import ConfigDialog

from core.scraper import CoronelScraper
from core import data_manager
from core import tiendanube_api
from core.product_uploader import ProductUploader
from core.stock_updater import sincronizar_stock_tiendanube

from config import settings # Para obtener configuraciones por defecto

logger = logging.getLogger(__name__)

# Constantes para tipos de mensajes de la cola
MSG_UPDATE_STATUS = "update_status"
MSG_UPDATE_PROGRESS = "update_progress"
MSG_APPEND_LOG = "append_log"
MSG_TASK_COMPLETE = "task_complete"
MSG_ENABLE_BUTTONS = "enable_buttons"


class AppController:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("Gestor de Scraping y Tiendanube - By Jules")
        # Centrar la ventana (opcional, pero útil)
        window_width = 800
        window_height = 600
        screen_width = root.winfo_screenwidth()
        screen_height = root.winfo_screenheight()
        center_x = int(screen_width/2 - window_width / 2)
        center_y = int(screen_height/2 - window_height / 2)
        self.root.geometry(f'{window_width}x{window_height}+{center_x}+{center_y}')

        self.root.protocol("WM_DELETE_WINDOW", self._on_closing)

        # --- Configuración actual de la aplicación ---
        # Estos valores se cargarán/guardarán desde ConfigDialog o un archivo de configuración de la GUI
        self.current_ganancia_porcentaje = settings.get_current_ganancia_porcentaje()
        self.current_descargar_imagenes = settings.get_current_download_images_state()

        # Cola para comunicación desde hilos de trabajo a la GUI
        self.gui_queue = Queue()

        # Crear la vista principal
        self.main_view = MainWindowView(self.root, self)
        self.main_view.pack(expand=True, fill=tk.BOTH)

        # Procesar la cola de la GUI periódicamente
        self.root.after(100, self._process_gui_queue)

        self.active_thread: Optional[threading.Thread] = None
        logger.info("AppController inicializado.")

    def _process_gui_queue(self):
        """Procesa mensajes de la cola de la GUI."""
        try:
            while not self.gui_queue.empty():
                message_type, data = self.gui_queue.get_nowait()

                if message_type == MSG_UPDATE_STATUS:
                    self.main_view.update_status(data)
                elif message_type == MSG_UPDATE_PROGRESS:
                    # data podría ser un solo valor para progreso general,
                    # o una tupla (valor, sub_valor) para progreso principal y secundario
                    if isinstance(data, tuple) and len(data) == 2:
                         self.main_view.update_progress(data[0], data[1])
                    elif isinstance(data, (int,float)):
                         self.main_view.update_progress(main_value=data)
                    else:
                        logger.warning(f"Dato de progreso no reconocido: {data}")

                elif message_type == MSG_APPEND_LOG:
                    level, message = data
                    self.main_view.append_log_message(message, level)
                elif message_type == MSG_TASK_COMPLETE:
                    task_name, success, message = data
                    final_message = f"{task_name} completada: {'Éxito' if success else 'Fallo'}. {message}"
                    messagebox.showinfo("Tarea Completada", final_message)
                    self.main_view.update_status(f"{task_name} finalizada.")
                    self._enable_buttons_on_gui_thread() # Habilitar botones después de mostrar el mensaje
                elif message_type == MSG_ENABLE_BUTTONS:
                    self.main_view.set_buttons_state(tk.NORMAL)

                self.gui_queue.task_done()
        except Exception as e:
            logger.error(f"Error procesando cola de GUI: {e}", exc_info=True)

        self.root.after(100, self._process_gui_queue) # Reprogramar

    def _put_in_gui_queue(self, msg_type: str, data: Any):
        """Helper para poner mensajes en la cola de la GUI."""
        self.gui_queue.put((msg_type, data))

    def _log_to_gui_and_logger(self, level: int, message: str, logger_func=None):
        """Envia log a la GUI y al logger estándar."""
        self._put_in_gui_queue(MSG_APPEND_LOG, (level, message))
        if logger_func:
            logger_func(message)
        else:
            # Mapear nivel de logging de Python a nombre para la GUI
            level_name = logging.getLevelName(level)
            if level == logging.INFO: logger.info(message)
            elif level == logging.WARNING: logger.warning(message)
            elif level == logging.ERROR: logger.error(message)
            elif level == logging.CRITICAL: logger.critical(message)
            else: logger.debug(message)


    def _run_task_in_thread(self, task_func, task_name: str, *args):
        """Ejecuta una función en un hilo separado."""
        if self.active_thread and self.active_thread.is_alive():
            messagebox.showwarning("Tarea en Progreso", "Ya hay una tarea en ejecución. Por favor, espere a que termine.")
            return

        self.main_view.set_buttons_state(tk.DISABLED)
        self.main_view.update_status(f"Iniciando {task_name}...")
        self.main_view.update_progress(0,0) # Resetear progreso

        self.active_thread = threading.Thread(target=self._thread_wrapper, args=(task_func, task_name, *args), daemon=True)
        self.active_thread.start()

    def _thread_wrapper(self, task_func, task_name: str, *args):
        """Wrapper para ejecutar la tarea y manejar el resultado."""
        success = False
        message = ""
        try:
            task_func(*args)
            success = True
            message = "Operación finalizada con éxito."
            self._log_to_gui_and_logger(logging.INFO, f"{task_name} completado exitosamente.")
        except Exception as e:
            message = f"Error durante {task_name}: {str(e)}"
            logger.error(f"Error en el hilo de {task_name}: {e}", exc_info=True)
            self._log_to_gui_and_logger(logging.ERROR, f"Error crítico en {task_name}: {e}")
        finally:
            self._put_in_gui_queue(MSG_TASK_COMPLETE, (task_name, success, message))
            # Habilitar botones se hace desde _process_gui_queue después del messagebox de MSG_TASK_COMPLETE
            # para asegurar que el usuario vea el mensaje antes de que los botones se habiliten.
            # Si MSG_TASK_COMPLETE no muestra messagebox, entonces se puede habilitar aquí:
            # self._put_in_gui_queue(MSG_ENABLE_BUTTONS, None)


    def _enable_buttons_on_gui_thread(self):
        """Asegura que los botones se habiliten en el hilo de la GUI."""
        self._put_in_gui_queue(MSG_ENABLE_BUTTONS, None)

    # --- Callbacks para los botones de MainWindowView ---
    def iniciar_scraping_completo_y_subida(self):
        task_name = "Scraping Completo y Subida a Tiendanube"
        self._run_task_in_thread(self._task_scraping_completo_y_subida, task_name)

    def _task_scraping_completo_y_subida(self):
        """Lógica para el scraping completo y subida."""
        self._log_to_gui_and_logger(logging.INFO, "Iniciando tarea: Scraping Completo y Subida...")

        # 0. Inicializar/Actualizar BD desde Excel
        self._put_in_gui_queue(MSG_UPDATE_STATUS, "Inicializando BD desde Excel...")
        if not data_manager.inicializar_base_de_datos_desde_excel():
            self._log_to_gui_and_logger(logging.ERROR, "Fallo al inicializar la BD desde Excel. Abortando.")
            raise Exception("Fallo en inicialización de BD desde Excel.")
        self._log_to_gui_and_logger(logging.INFO, "Base de datos inicializada/actualizada desde Excel.")
        self._put_in_gui_queue(MSG_UPDATE_PROGRESS, main_value=5)


        # 1. Scraping
        self._put_in_gui_queue(MSG_UPDATE_STATUS, "Iniciando scraping de Coronel Mayorista...")
        scraper = CoronelScraper(headless=True) # Configurable headless
        all_scraped_products = []
        try:
            if not scraper.login():
                self._log_to_gui_and_logger(logging.ERROR, "Fallo en login de Coronel. Abortando.")
                raise Exception("Login fallido en Coronel Mayorista.")
            self._log_to_gui_and_logger(logging.INFO, "Login en Coronel Mayorista exitoso.")
            self._put_in_gui_queue(MSG_UPDATE_PROGRESS, main_value=10)

            # Opcional: Descargar lista de precios (el scraper puede hacerlo internamente si se desea)
            # if not scraper.descargar_lista_precios_excel():
            #     self._log_to_gui_and_logger(logging.WARNING, "No se pudo descargar la lista de precios Excel nueva.")
            # else:
            #     self._log_to_gui_and_logger(logging.INFO, "Lista de precios Excel descargada.")
            #     # Re-inicializar BD si se descargó una nueva y se quiere usar inmediatamente
            #     data_manager.inicializar_base_de_datos_desde_excel()


            # Callbacks para progreso del scraper
            def scraper_progreso_global(pagina_actual, total_paginas):
                # Progreso general del scraping (0-50% de la tarea total)
                # Estimación: si scraping es 50% de la tarea, y hay N paginas.
                # Aquí necesitamos una mejor estimación de progreso total.
                self._put_in_gui_queue(MSG_UPDATE_STATUS, f"Scrapeando página {pagina_actual}...")
                # Actualizar progreso general (ej. 10% a 60% para scraping)
                # Esto es complejo de mapear directamente a un progreso 0-100.
                # Por ahora, solo actualizaremos el estado.

            def scraper_progreso_pagina(proc_en_pagina, total_en_pagina):
                self._put_in_gui_queue(MSG_UPDATE_STATUS, f"Scrapeando producto {proc_en_pagina}/{total_en_pagina} en página...")
                # Actualizar sub-progreso si la GUI lo soporta
                self._put_in_gui_queue(MSG_UPDATE_PROGRESS, (60 + (proc_en_pagina/total_en_pagina)*30 if total_en_pagina > 0 else 0 ) if self.main_view.supports_sub_progress() else None)


            def scraper_producto_encontrado(producto):
                self._log_to_gui_and_logger(logging.DEBUG, f"Producto scrapeado: {producto.get('codigo')}")
                # Guardar producto en BD inmediatamente
                if not data_manager.guardar_o_actualizar_producto(producto):
                     self._log_to_gui_and_logger(logging.WARNING, f"No se pudo guardar en BD el producto scrapeado: {producto.get('codigo')}")


            all_scraped_products = scraper.scrapear_todos_productos_sitio(
                descargar_imagenes=self.current_descargar_imagenes,
                callback_producto_encontrado=scraper_producto_encontrado, # Guardar directamente
                callback_progreso_global=scraper_progreso_global,
                callback_progreso_pagina=scraper_progreso_pagina
            )
            if not all_scraped_products:
                 self._log_to_gui_and_logger(logging.WARNING, "El scraping no recolectó productos.")
                 # No necesariamente un error fatal, podría no haber productos o ser una categoría vacía.
            else:
                self._log_to_gui_and_logger(logging.INFO, f"Scraping finalizado. {len(all_scraped_products)} productos procesados y guardados en BD.")

            self._put_in_gui_queue(MSG_UPDATE_PROGRESS, main_value=60)

        finally:
            if scraper: scraper.close()

        # 2. Subida a Tiendanube
        self._put_in_gui_queue(MSG_UPDATE_STATUS, "Iniciando subida/actualización a Tiendanube...")
        uploader = ProductUploader(
            ganancia_porcentaje=self.current_ganancia_porcentaje,
            descargar_imagenes=self.current_descargar_imagenes,
            callback_progreso=self._uploader_callback_progreso # Pasar un callback para la GUI
        )
        uploader.subir_productos_a_tiendanube() # Esta función ya loguea internamente
        self._log_to_gui_and_logger(logging.INFO, "Proceso de subida/actualización a Tiendanube finalizado.")
        self._put_in_gui_queue(MSG_UPDATE_PROGRESS, main_value=100)


    def _uploader_callback_progreso(self, actual, total, mensaje):
        """Callback para el progreso del ProductUploader."""
        self._put_in_gui_queue(MSG_UPDATE_STATUS, f"Subiendo a Tiendanube: {mensaje} ({actual}/{total})")
        # Mapear progreso de subida (ej. 60% a 100% de la tarea total)
        progreso_uploader = (actual / total) * 40 if total > 0 else 0
        self._put_in_gui_queue(MSG_UPDATE_PROGRESS, main_value=60 + progreso_uploader)


    def iniciar_actualizacion_stock(self):
        task_name = "Actualización de Stock en Tiendanube"
        self._run_task_in_thread(self._task_actualizar_stock, task_name)

    def _task_actualizar_stock(self):
        """Lógica para la actualización de stock."""
        self._log_to_gui_and_logger(logging.INFO, "Iniciando tarea: Actualización de Stock...")

        def stock_updater_progreso(actual, total, mensaje):
            self._put_in_gui_queue(MSG_UPDATE_STATUS, f"Actualizando stock: {mensaje} ({actual}/{total})")
            progreso = (actual/total) * 100 if total > 0 else 0
            self._put_in_gui_queue(MSG_UPDATE_PROGRESS, main_value=progreso)

        # La función sincronizar_stock_tiendanube ya maneja el scraper y la API de Tiendanube.
        # Se le pasa True para headless, y el callback.
        sincronizar_stock_tiendanube(headless_scraper=True, callback_progreso=stock_updater_progreso)
        self._log_to_gui_and_logger(logging.INFO, "Actualización de stock finalizada.")
        self._put_in_gui_queue(MSG_UPDATE_PROGRESS, main_value=100)


    def abrir_configuracion(self):
        logger.debug("Abriendo diálogo de configuración.")
        config_dialog = ConfigDialog(self.root, "Configuración de la Aplicación",
                                     self.current_ganancia_porcentaje,
                                     self.current_descargar_imagenes)

        if config_dialog.result: # result es None si se cancela
            self.current_ganancia_porcentaje = config_dialog.ganancia_porcentaje
            self.current_descargar_imagenes = config_dialog.descargar_imagenes

            # Guardar en settings (que ahora tiene setters para estos valores)
            settings.set_current_ganancia_porcentaje(self.current_ganancia_porcentaje)
            settings.set_current_download_images_state(self.current_descargar_imagenes)

            self._log_to_gui_and_logger(logging.INFO, f"Configuración guardada: Ganancia {self.current_ganancia_porcentaje}%, Descargar Imágenes: {self.current_descargar_imagenes}")
            messagebox.showinfo("Configuración Guardada", "La nueva configuración se aplicará en las próximas operaciones.")


    def limpiar_cache_api(self):
        task_name = "Limpiar Caché API Tiendanube"
        self._run_task_in_thread(self._task_limpiar_cache_api, task_name)

    def _task_limpiar_cache_api(self):
        self._log_to_gui_and_logger(logging.INFO, "Limpiando caché de la API de Tiendanube...")
        tiendanube_api.limpiar_cache_productos_tiendanube()
        self._log_to_gui_and_logger(logging.INFO, "Caché de la API de Tiendanube limpiada.")
        self._put_in_gui_queue(MSG_UPDATE_PROGRESS, main_value=100)


    def inicializar_bd_excel(self):
        task_name = "Inicializar BD desde Excel"
        self._run_task_in_thread(self._task_inicializar_bd_excel, task_name)

    def _task_inicializar_bd_excel(self):
        self._log_to_gui_and_logger(logging.INFO, "Inicializando/Actualizando base de datos desde Excel...")
        self._put_in_gui_queue(MSG_UPDATE_STATUS, "Buscando Excel y procesando...")
        exito = data_manager.inicializar_base_de_datos_desde_excel()
        if exito:
            self._log_to_gui_and_logger(logging.INFO, "Base de datos inicializada/actualizada desde Excel exitosamente.")
        else:
            self._log_to_gui_and_logger(logging.ERROR, "Fallo al inicializar/actualizar la base de datos desde Excel.")
        self._put_in_gui_queue(MSG_UPDATE_PROGRESS, main_value=100)

    def _on_closing(self):
        """Maneja el evento de cierre de la ventana."""
        if self.active_thread and self.active_thread.is_alive():
            if messagebox.askokcancel("Salir", "Hay una tarea en ejecución. ¿Está seguro que desea salir? La tarea podría no completarse correctamente."):
                # Aquí se podría intentar una cancelación "grácil" de la tarea si fuera posible
                logger.warning("Cerrando aplicación con tarea activa.")
                self.root.destroy()
            else:
                return # No cerrar
        else:
            if messagebox.askokcancel("Salir", "¿Está seguro que desea salir de la aplicación?"):
                self.root.destroy()

    def start(self):
        logger.info("Iniciando bucle principal de la GUI.")
        self.root.mainloop()

# Este archivo no se ejecutará directamente así en la estructura final,
# sino que main.py importará AppController y lo iniciará.
# Pero para pruebas rápidas de la GUI:
if __name__ == '__main__':
    # Configurar logging para ver salidas de la GUI y de los módulos core
    from config.logging_config import setup_logging
    setup_logging() # Asegurar que el logging esté configurado

    root = tk.Tk()
    app = AppController(root)
    app.start()
