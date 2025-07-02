import tkinter as tk
from tkinter import ttk, messagebox

class ConfigDialog(tk.Toplevel):
    def __init__(self, parent, title, initial_ganancia, initial_descarga_img):
        super().__init__(parent)
        self.transient(parent) # Hacer que se muestre encima del parent
        self.title(title)
        self.parent = parent
        self.result = None # Para almacenar el resultado (si se guarda o no)

        self.ganancia_var = tk.IntVar(value=initial_ganancia)
        self.descarga_img_var = tk.BooleanVar(value=initial_descarga_img)

        body = ttk.Frame(self)
        self.initial_focus = self._create_body(body)
        body.pack(padx=15, pady=15)

        self._create_buttons()

        if not self.initial_focus:
            self.initial_focus = self

        self.protocol("WM_DELETE_WINDOW", self._on_cancel) # Manejar cierre con 'X'
        self.grab_set() # Hacer el diálogo modal

        self.geometry("+%d+%d" % (parent.winfo_rootx() + 50,
                                  parent.winfo_rooty() + 50))

        self.initial_focus.focus_set()
        self.wait_window(self) # Esperar hasta que esta ventana se cierre

    def _create_body(self, master_frame):
        # --- Sección General ---
        general_group = ttk.LabelFrame(master_frame, text="Configuración General", padding=(10,5))
        general_group.pack(fill=tk.X, pady=5)

        # Ganancia
        ganancia_label = ttk.Label(general_group, text="Porcentaje de Ganancia (%):")
        ganancia_label.grid(row=0, column=0, padx=5, pady=5, sticky=tk.W)
        self.ganancia_entry = ttk.Spinbox(general_group, from_=0, to=1000, increment=1, textvariable=self.ganancia_var, width=7)
        self.ganancia_entry.grid(row=0, column=1, padx=5, pady=5, sticky=tk.EW)

        # Descargar Imágenes
        self.descarga_img_check = ttk.Checkbutton(general_group, text="Descargar Imágenes Localmente", variable=self.descarga_img_var)
        self.descarga_img_check.grid(row=1, column=0, columnspan=2, padx=5, pady=5, sticky=tk.W)

        # --- Sección Credenciales (Informativa) ---
        # Por ahora, solo texto informativo. La edición real de credenciales es más compleja y
        # se recomienda hacerla a través de .env o un gestor de secretos.
        creds_group = ttk.LabelFrame(master_frame, text="Credenciales (Informativo)", padding=(10,5))
        creds_group.pack(fill=tk.X, pady=5)

        info_text = ("Las credenciales de Coronel Mayorista (CUIT/Contraseña) y Tiendanube "
                     "(Access Token/Store ID) se gestionan principalmente a través del archivo '.env' "
                     "en la raíz del proyecto o variables de entorno del sistema.\n\n"
                     "Asegúrese que estén correctamente configuradas para el funcionamiento de la aplicación.")

        creds_info_label = ttk.Label(creds_group, text=info_text, wraplength=350, justify=tk.LEFT)
        creds_info_label.pack(padx=5, pady=5, fill=tk.X)

        return self.ganancia_entry # Widget inicial para el foco

    def _create_buttons(self):
        button_frame = ttk.Frame(self)
        button_frame.pack(fill=tk.X, pady=(0, 10), padx=10)

        ttk.Button(button_frame, text="Guardar", command=self._on_ok, style="Accent.TButton").pack(side=tk.RIGHT, padx=5)
        ttk.Button(button_frame, text="Cancelar", command=self._on_cancel).pack(side=tk.RIGHT, padx=5)


    def _on_ok(self, event=None):
        try:
            self.ganancia_porcentaje = self.ganancia_var.get()
            if not (0 <= self.ganancia_porcentaje <= 10000): # Un rango amplio pero razonable
                messagebox.showerror("Valor Inválido", "El porcentaje de ganancia debe ser un número razonable (ej. 0-10000).", parent=self)
                return
        except tk.TclError:
            messagebox.showerror("Valor Inválido", "El porcentaje de ganancia debe ser un número entero.", parent=self)
            return

        self.descargar_imagenes = self.descarga_img_var.get()
        self.result = True # Indicar que se guardó

        self.parent.focus_set() # Devolver foco a la ventana principal
        self.destroy()

    def _on_cancel(self, event=None):
        self.result = False # Indicar que se canceló
        self.parent.focus_set()
        self.destroy()


if __name__ == '__main__':
    # Prueba rápida del ConfigDialog
    # Esto requiere que AppController exista o se mockee un controlador simple.

    # Configurar logging para ver salidas
    import logging
    if not logging.getLogger().hasHandlers():
        # Asumimos que config.logging_config está disponible en el path para prueba
        try:
            from config.logging_config import setup_logging
            setup_logging()
        except ImportError:
            logging.basicConfig(level=logging.DEBUG)


    root = tk.Tk()
    root.title("Test Dialogs")

    # Intentar aplicar un tema de ttkthemes si está disponible
    try:
        from ttkthemes import ThemedTk
        # root = ThemedTk(theme="arc") # Probar con "arc", "plastik", etc.
        # Para que el ConfigDialog herede el tema, la raíz debe ser ThemedTk
        # Si no, el diálogo puede verse con el tema Tk por defecto.
        # Para esta prueba, si ThemedTk está disponible, lo usamos.
        # Si se va a usar un tema, la instancia principal de la app (root) debería ser ThemedTk.
        themed_root = ThemedTk(theme="arc", toplevel=True) # toplevel=True para que Toplevels hereden
        themed_root.withdraw() # Ocultar la ventana raíz de prueba de ThemedTk

        # Usar la themed_root como parent para el diálogo
        test_parent = themed_root
    except ImportError:
        test_parent = root # Usar la raíz Tk normal si ttkthemes no está
        logging.info("ttkthemes no encontrado, usando tema Tk por defecto para la prueba de diálogo.")
    except tk.TclError as e:
        test_parent = root
        logging.warning(f"Error al aplicar tema en prueba de diálogo: {e}")


    def open_test_dialog():
        # Valores iniciales de ejemplo
        initial_ganancia = 30
        initial_descarga = True

        dialog = ConfigDialog(test_parent, "Configuración de Prueba", initial_ganancia, initial_descarga)

        if dialog.result is True: # Si el usuario guardó
            print(f"Configuración Guardada: Ganancia={dialog.ganancia_porcentaje}%, Descarga Img={dialog.descargar_imagenes}")
        else:
            print("Configuración Cancelada o Cerrada.")

    ttk.Button(root, text="Abrir ConfigDialog", command=open_test_dialog).pack(padx=20, pady=20)

    root.geometry("300x100")
    root.mainloop()

    # Si se usó ThemedTk, asegurarse que su instancia raíz también se cierre si es necesario
    if 'themed_root' in locals() and themed_root.winfo_exists():
        themed_root.destroy()
