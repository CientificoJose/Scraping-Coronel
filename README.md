# Proyecto de Scraping y Gestión de Tienda Online

Este proyecto automatiza el proceso de scraping de productos de un proveedor mayorista (Coronel Mayorista) y la posterior creación, actualización o gestión de stock de dichos productos en una tienda online de Tiendanube. La aplicación cuenta con una interfaz gráfica de usuario (GUI) para facilitar su uso.

## Características Principales

*   **Scraping de Productos:** Extrae información detallada de productos (código, descripción, precio, imágenes, categorías) del sitio web de Coronel Mayorista.
*   **Gestión de Base de Datos Local:** Guarda los productos scrapeados en una base de datos SQLite local.
    *   Inicializa la base de datos a partir de la lista de precios en formato Excel descargada del proveedor.
*   **Integración con Tiendanube:**
    *   Crea nuevos productos en Tiendanube.
    *   Actualiza productos existentes (descripción, precio, imágenes, categorías).
    *   Sincroniza el stock: establece stock "infinito" para productos disponibles en el proveedor y stock "cero" para los no disponibles.
*   **Interfaz Gráfica de Usuario (GUI):**
    *   Permite configurar parámetros como el porcentaje de ganancia y si se deben descargar las imágenes.
    *   Inicia las operaciones de scraping, subida a Tiendanube y actualización de stock.
    *   Muestra el progreso de las tareas y los logs de actividad.
    *   Permite limpiar la caché de la API de Tiendanube.
*   **Configuración Flexible:**
    *   Manejo de credenciales a través de un archivo `.env`.
    *   Logging detallado de las operaciones.

## Estructura del Proyecto

El proyecto sigue una estructura modular para facilitar el mantenimiento y la escalabilidad:

```
proyecto_scraping_grafico/
├── main.py                     # Punto de entrada principal de la aplicación GUI.
├── config/                     # Módulos de configuración
│   ├── settings.py             # Configuraciones generales, rutas, URLs.
│   ├── credentials.py          # Manejo de credenciales (lee .env).
│   └── logging_config.py       # Configuración del logging.
├── core/                       # Lógica de negocio principal
│   ├── scraper.py              # Lógica de scraping de Coronel Mayorista.
│   ├── data_manager.py         # Gestión de la base de datos SQLite local.
│   ├── tiendanube_api.py       # Interacción con la API de Tiendanube.
│   ├── stock_updater.py        # Lógica para sincronización de stock.
│   └── product_uploader.py     # Lógica para subir/actualizar productos.
├── gui/                        # Componentes de la Interfaz Gráfica de Usuario (Tkinter)
│   ├── app.py                  # Controlador principal de la GUI (AppController).
│   ├── main_window.py          # Vista de la ventana principal.
│   └── dialogs.py              # Diálogos personalizados (ej. configuración).
├── utils/                      # Módulos de utilidad
│   └── file_utils.py           # Utilidades para manejo de archivos (ej. guardar Excel).
├── assets/                     # Recursos estáticos para la GUI (iconos, imágenes) - (Vacío por ahora)
├── data/                       # Datos generados o descargados
│   ├── productos_coronel/      # Excels de lista de precios descargados.
│   ├── img-scraping/           # Imágenes de productos scrapeadas (si se habilita).
│   ├── productos.db            # Base de datos SQLite.
│   └── api_cache/              # Caché de respuestas de la API de Tiendanube.
├── tests/                      # Pruebas (Vacío por ahora)
├── .env.example                # Ejemplo de archivo de configuración de credenciales.
├── .gitignore
├── requirements.txt            # Dependencias del proyecto.
└── README.md                   # Este archivo.
```

## Requisitos Previos

*   Python 3.8 o superior.
*   Google Chrome instalado (para el scraping con Selenium).
*   Credenciales de acceso para Coronel Mayorista.
*   Una tienda en Tiendanube con acceso a la API (Store ID y Access Token).

## Instalación y Configuración

1.  **Clonar el Repositorio:**
    ```bash
    git clone <url_del_repositorio>
    cd nombre_del_repositorio
    ```

2.  **Crear un Entorno Virtual (Recomendado):**
    ```bash
    python -m venv venv
    source venv/bin/activate  # En Windows: venv\Scripts\activate
    ```

3.  **Instalar Dependencias:**
    ```bash
    pip install -r requirements.txt
    ```
    El archivo `requirements.txt` debería incluir:
    ```
    selenium
    webdriver-manager
    requests
    openpyxl
    colorama
    tqdm
    python-dotenv
    ttkthemes
    # Añadir cualquier otra dependencia que se haya usado
    ```

4.  **Configurar Credenciales:**
    *   Copie el archivo `.env.example` a `.env`:
        ```bash
        cp .env.example .env
        ```
    *   Edite el archivo `.env` y complete sus credenciales:
        ```
        CORONEL_CUIT=tu_cuit_coronel
        CORONEL_PASSWORD=tu_password_coronel
        TIENDANUBE_ACCESS_TOKEN=tu_access_token_de_tiendanube
        TIENDANUBE_STORE_ID=tu_id_de_tienda_tiendanube
        # DEEPSEEK_API_KEY=tu_clave_api_deepseek (Si se implementa funcionalidad con DeepSeek)
        ```

## Uso de la Aplicación

Ejecute la aplicación desde la raíz del proyecto:

```bash
python main.py
```

Esto abrirá la interfaz gráfica de usuario. Desde allí podrá:

1.  **Configurar:** Establezca el porcentaje de ganancia y si desea descargar imágenes a través del botón "Configuración".
2.  **Inicializar BD (Opcional pero Recomendado la Primera Vez):** Use el botón "Inicializar BD (Excel)" para poblar la base de datos local con los códigos de producto del último Excel de precios de Coronel (asegúrese que un Excel exista en `data/productos_coronel/`, el scraping completo también descarga uno nuevo).
3.  **Scraping Completo y Subida:** Haga clic en "Scraping Completo y Subida a Tienda". La aplicación realizará:
    *   Login en Coronel Mayorista.
    *   (El scraper descarga automáticamente la lista de precios más reciente a `data/productos_coronel/`).
    *   (El sistema de gestión de datos `data_manager` usa el Excel más reciente para poblar códigos de barras antes del scraping detallado).
    *   Scraping de todos los productos de la web.
    *   Guardado de productos en la base de datos local (`data/productos.db`).
    *   Subida (creación o actualización) de estos productos a su Tiendanube.
4.  **Actualizar Stock:** Haga clic en "Actualizar Stock en Tienda" para sincronizar el stock de sus productos en Tiendanube basándose en la disponibilidad actual en Coronel Mayorista.
5.  **Limpiar Caché API:** Si experimenta problemas con datos desactualizados de Tiendanube, puede usar esta opción para limpiar la caché local de la API.

Observe el panel de "Estado y Progreso" y el área de "Registros de Actividad" en la GUI para seguir las operaciones.

## Logging

Los logs detallados de la aplicación se guardan en `app.log` en la raíz del proyecto.

## Desarrollo y Pruebas

*   Los módulos principales de lógica de negocio se encuentran en el directorio `core/`.
*   Los componentes de la GUI están en `gui/`.
*   Para probar módulos individuales del `core` desde la línea de comandos (útil para depuración):
    ```bash
    python -m core.scraper
    python -m core.data_manager
    # etc.
    ```
    Asegúrese que el archivo `.env` esté configurado.

## Contribuciones

Las contribuciones son bienvenidas. Por favor, abra un issue o un Pull Request.

## Licencia

(Especificar una licencia si es necesario, ej. MIT, GPL, etc. Si no, se puede omitir o indicar "Propietario")
