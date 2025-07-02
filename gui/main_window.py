import tkinter as tk
from tkinter import ttk, scrolledtext
import logging

# Asumiendo que AppController se importa donde se usa esta vista.
# from .app import AppController # Evitar importación circular si AppController importa MainWindowView

logger = logging.getLogger(__name__)

class MainWindowView(ttk.Frame):
    def __init__(self, parent: tk.Tk, controller): # 'controller' será una instancia de AppController
        super().__init__(parent)
        self.parent = parent
        self.controller = controller # Guardar referencia al controlador

        self.buttons: Dict[str, ttk.Button] = {} # Para manejar el estado de los botones

        self._setup_widgets()

    def _setup_widgets(self):
        # --- Panel de Control (Botones) ---
        control_frame = ttk.LabelFrame(self, text="Acciones Principales", padding=(10, 5))
        control_frame.pack(side=tk.TOP, fill=tk.X, padx=10, pady=(10,5))

        # Botón: Scraping Completo y Subida
        self.buttons["scrape_upload"] = ttk.Button(
            control_frame,
            text="Scraping Completo y Subida a Tienda",
            command=self.controller.iniciar_scraping_completo_y_subida,
            style="Accent.TButton" # Estilo Accent si se usa Azure theme o similar
        )
        self.buttons["scrape_upload"].pack(side=tk.LEFT, padx=5, pady=5, fill=tk.X, expand=True)

        # Botón: Actualizar Stock
        self.buttons["update_stock"] = ttk.Button(
            control_frame,
            text="Actualizar Stock en Tienda",
            command=self.controller.iniciar_actualizacion_stock
        )
        self.buttons["update_stock"].pack(side=tk.LEFT, padx=5, pady=5, fill=tk.X, expand=True)

        # Frame para otros botones de utilidad
        util_buttons_frame = ttk.Frame(control_frame)
        util_buttons_frame.pack(side=tk.LEFT, padx=5, pady=5, fill=tk.X, expand=True)

        self.buttons["config"] = ttk.Button(
            util_buttons_frame,
            text="Configuración",
            command=self.controller.abrir_configuracion
        )
        self.buttons["config"].pack(side=tk.TOP, fill=tk.X, pady=(0,2))

        self.buttons["init_db"] = ttk.Button(
            util_buttons_frame,
            text="Inicializar BD (Excel)",
            command=self.controller.inicializar_bd_excel
        )
        self.buttons["init_db"].pack(side=tk.TOP, fill=tk.X, pady=(2,0))

        self.buttons["clear_cache"] = ttk.Button(
            util_buttons_frame,
            text="Limpiar Caché API",
            command=self.controller.limpiar_cache_api
        )
        self.buttons["clear_cache"].pack(side=tk.TOP, fill=tk.X, pady=(2,0))


        # --- Panel de Progreso y Estado ---
        status_progress_frame = ttk.LabelFrame(self, text="Estado y Progreso", padding=(10, 5))
        status_progress_frame.pack(side=tk.TOP, fill=tk.X, padx=10, pady=5)

        # Etiqueta de Estado
        self.status_label = ttk.Label(status_progress_frame, text="Listo.", anchor=tk.W, font=("Segoe UI", 9))
        self.status_label.pack(fill=tk.X, padx=5, pady=(0,5))

        # Barra de Progreso Principal
        self.main_progress_bar = ttk.Progressbar(status_progress_frame, orient=tk.HORIZONTAL, length=100, mode='determinate')
        self.main_progress_bar.pack(fill=tk.X, padx=5, pady=(0,5))

        # (Opcional) Barra de Progreso Secundaria (si se decide implementar)
        # self.sub_progress_bar = ttk.Progressbar(status_progress_frame, orient=tk.HORIZONTAL, length=100, mode='determinate')
        # self.sub_progress_bar.pack(fill=tk.X, padx=5, pady=(0,5))


        # --- Área de Logs ---
        log_frame = ttk.LabelFrame(self, text="Registros de Actividad", padding=(10, 5))
        log_frame.pack(side=tk.BOTTOM, fill=tk.BOTH, expand=True, padx=10, pady=(5,10))

        self.log_text_area = scrolledtext.ScrolledText(log_frame, wrap=tk.WORD, height=10, state=tk.DISABLED, font=("Consolas", 9))
        self.log_text_area.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # Configurar tags para colores en el log (opcional, pero útil)
        self.log_text_area.tag_config("INFO", foreground="black")
        self.log_text_area.tag_config("DEBUG", foreground="gray")
        self.log_text_area.tag_config("WARNING", foreground="orange")
        self.log_text_area.tag_config("ERROR", foreground="red")
        self.log_text_area.tag_config("CRITICAL", foreground="red", font=("Consolas", 9, "bold"))

        # Aplicar un tema si está disponible (ej. 'azure' de ttkthemes)
        try:
            # Intentar usar un tema más moderno si está instalado ttkthemes
            # from ttkthemes import ThemedTk
            # if isinstance(self.parent, ThemedTk): # Si la raíz es ThemedTk
            #    pass # Ya está aplicado
            # else: # Aplicar a la raíz si no lo es
            #    style = ttk.Style()
            #    available_themes = style.theme_names() # ('winnative', 'clam', 'alt', 'default', 'classic', 'vista', 'xpnative')
            #    logger.debug(f"Temas TTK disponibles: {available_themes}")
            #    if 'clam' in available_themes: style.theme_use('clam')
            #    elif 'vista' in available_themes: style.theme_use('vista')
            #
            # Para el botón Accent.TButton, se necesita un tema que lo soporte, como Azure de ttkthemes
            # Si no se usa ttkthemes, se puede quitar style="Accent.TButton" o definir un estilo manualmente.
             s = ttk.Style()
             if "Accent.TButton" not in s.layout("TButton"): # Si el estilo Accent no existe
                logger.info("Estilo Accent.TButton no encontrado, usando estilo por defecto para botón principal.")
                self.buttons["scrape_upload"].configure(style="TButton")


        except ImportError:
            logger.info("ttkthemes no instalado. Usando tema por defecto de Tk.")
        except tk.TclError as e:
            logger.warning(f"Error al aplicar tema ttk: {e}. Usando tema por defecto.")


    def update_status(self, message: str):
        """Actualiza la etiqueta de estado."""
        if self.status_label:
            self.status_label.config(text=message)
            self.parent.update_idletasks() # Forzar actualización de la GUI

    def update_progress(self, main_value: Optional[float] = None, sub_value: Optional[float] = None):
        """Actualiza las barras de progreso."""
        if main_value is not None and self.main_progress_bar:
            self.main_progress_bar['value'] = main_value
        # if sub_value is not None and self.sub_progress_bar: # Si se implementa sub-barra
        #     self.sub_progress_bar['value'] = sub_value
        self.parent.update_idletasks()

    def append_log_message(self, message: str, level: int = logging.INFO):
        """Añade un mensaje al área de logs con el nivel de log apropiado."""
        if self.log_text_area:
            self.log_text_area.config(state=tk.NORMAL) # Habilitar para insertar

            level_name = logging.getLevelName(level).upper() # ej. "INFO", "ERROR"
            # Usar el tag si existe, sino texto plano
            if level_name in self.log_text_area.tag_names():
                self.log_text_area.insert(tk.END, f"{message}\n", level_name)
            else:
                self.log_text_area.insert(tk.END, f"{message}\n")

            self.log_text_area.see(tk.END) # Auto-scroll
            self.log_text_area.config(state=tk.DISABLED) # Deshabilitar para hacerlo solo lectura
            self.parent.update_idletasks()

    def set_buttons_state(self, state: str): # state puede ser tk.NORMAL o tk.DISABLED
        """Habilita o deshabilita todos los botones de acción principales."""
        for btn_name, button_widget in self.buttons.items():
            if button_widget:
                button_widget.config(state=state)
        self.parent.update_idletasks()

    def supports_sub_progress(self) -> bool:
        """Indica si la vista tiene una barra de sub-progreso implementada."""
        # return hasattr(self, 'sub_progress_bar') and self.sub_progress_bar is not None
        return False # Por ahora no implementada


if __name__ == '__main__':
    # Prueba rápida de la MainWindowView
    # Esto requiere que AppController exista o se mockee un controlador simple.

    # Configurar logging para ver salidas
    if not logging.getLogger().hasHandlers():
        from config.logging_config import setup_logging
        setup_logging()

    class MockController:
        def iniciar_scraping_completo_y_subida(self): print("Mock: Iniciar Scraping Completo y Subida")
        def iniciar_actualizacion_stock(self): print("Mock: Iniciar Actualización de Stock")
        def abrir_configuracion(self): print("Mock: Abrir Configuración")
        def limpiar_cache_api(self): print("Mock: Limpiar Caché API")
        def inicializar_bd_excel(self): print("Mock: Inicializar BD desde Excel")

    root = tk.Tk()
    root.title("Test MainWindowView")

    # Intentar aplicar un tema de ttkthemes si está disponible
    try:
        from ttkthemes import ThemedTk
        root = ThemedTk(theme="arc") # Probar con "arc", "plastik", " कई otros
    except ImportError:
        logger.info("ttkthemes no encontrado, usando tema Tk por defecto para la prueba.")
    except tk.TclError as e:
        logger.warning(f"Error al aplicar tema en prueba: {e}")


    mock_controller = MockController()
    main_view_test = MainWindowView(root, mock_controller)
    main_view_test.pack(expand=True, fill=tk.BOTH)

    # Simular actualizaciones
    main_view_test.update_status("Probando estado...")
    main_view_test.update_progress(50)
    main_view_test.append_log_message("Este es un mensaje de INFO de prueba.", logging.INFO)
    main_view_test.append_log_message("Este es un mensaje de WARNING de prueba.", logging.WARNING)
    main_view_test.append_log_message("Este es un mensaje de ERROR de prueba.", logging.ERROR)

    # main_view_test.set_buttons_state(tk.DISABLED) # Probar deshabilitar

    root.geometry("750x550")
    root.mainloop()
