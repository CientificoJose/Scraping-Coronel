import openpyxl
import os
import logging
from typing import List, Dict, Any, Optional

# from colorama import Fore, Style # Reemplazado por logging
from config import settings # Para usar rutas base si es necesario

logger = logging.getLogger(__name__)

def save_products_to_excel(products: List[Dict[str, Any]], filename: str = "productos_exportados.xlsx", output_dir: Optional[str] = None) -> Optional[str]:
    """
    Guarda una lista de productos en un archivo Excel (.xlsx).

    Args:
        products: Lista de diccionarios, donde cada diccionario representa un producto.
                  Se esperan claves como 'codigo', 'descripcion', 'precio', 'imagen_url', 'imagen_local'.
        filename: Nombre del archivo Excel a crear (sin la ruta).
        output_dir: Directorio donde se guardará el archivo. Si es None,
                    se usará settings.DATA_DIR o el directorio actual si DATA_DIR no está definido.

    Returns:
        Ruta absoluta del archivo Excel creado, o None si hubo un error.
    """
    if not products:
        logger.warning("No hay productos para guardar en Excel.")
        return None

    if output_dir is None:
        # Usar un directorio de datos por defecto si está configurado, sino el directorio actual.
        # Esto es para evitar guardar archivos en lugares inesperados si se llama desde diferentes contextos.
        # Idealmente, la GUI o el script que llama a esta función especificaría un output_dir.
        output_dir = getattr(settings, 'DATA_DIR', os.getcwd())

    os.makedirs(output_dir, exist_ok=True) # Asegurar que el directorio de salida exista

    filepath = os.path.join(output_dir, filename)

    try:
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "Productos"

        # Encabezados: se pueden tomar de las claves del primer producto o definir explícitamente.
        # Para mantener consistencia con el original:
        headers = ["Código", "Descripción", "Precio", "Imagen URL", "Imagen Local", "Categoría", "Subcategoría", "Variante", "Cód. Barras"]
        # O podríamos inferirlos del primer producto, pero el orden no estaría garantizado.
        # if products:
        #     headers = list(products[0].keys()) # Esto podría no ser el orden deseado

        ws.append(headers)

        # Agregar datos
        for product_data in products:
            # Mapear los datos del producto a las columnas del header.
            # Esto es más robusto que asumir que product_data.values() estará en el orden correcto.
            row_to_append = [
                product_data.get('codigo'),
                product_data.get('descripcion'),
                product_data.get('precio'),
                product_data.get('imagen_url'),
                product_data.get('imagen_local'),
                product_data.get('categoria'),
                product_data.get('subcategoria'),
                product_data.get('variante'),
                product_data.get('codigo_de_barras') # o 'codigo_barra' si así se llama en el dict
            ]
            ws.append(row_to_append)

        wb.save(filepath)

        logger.info(f"Excel creado exitosamente: {filepath}")
        return os.path.abspath(filepath)

    except Exception as e:
        logger.error(f"Error al guardar la lista de productos en Excel ({filepath}): {e}", exc_info=True)
        return None

if __name__ == '__main__':
    # Bloque de prueba
    if not logging.getLogger().hasHandlers():
        from config.logging_config import setup_logging
        setup_logging()

    logger.info("Probando file_utils.py...")

    # Datos de prueba
    sample_products = [
        {'codigo': 'P001', 'descripcion': 'Producto Uno', 'precio': '10.99', 'imagen_url': 'http://example.com/p001.jpg', 'imagen_local': 'p001.jpg', 'categoria': 'Cat A', 'subcategoria': 'Sub A1', 'variante': 'Rojo', 'codigo_de_barras': '123'},
        {'codigo': 'P002', 'descripcion': 'Producto Dos', 'precio': '25.50', 'imagen_url': 'http://example.com/p002.jpg', 'imagen_local': None, 'categoria': 'Cat B', 'subcategoria': None, 'variante': None, 'codigo_de_barras': '456'},
        {'codigo': 'P003', 'descripcion': 'Producto Tres sin precio', 'precio': None, 'imagen_url': None, 'imagen_local': 'p003.png', 'categoria': 'Cat A', 'subcategoria': 'Sub A2', 'variante': 'Azul', 'codigo_de_barras': '789'},
    ]

    # Probar guardar en Excel
    # Crear un directorio 'test_output' para no ensuciar 'data' durante la prueba.
    test_output_directory = os.path.join(getattr(settings, 'BASE_DIR', os.getcwd()), "test_excel_output")

    excel_path = save_products_to_excel(sample_products, filename="prueba_productos.xlsx", output_dir=test_output_directory)

    if excel_path:
        logger.info(f"Prueba de guardado de Excel exitosa. Archivo en: {excel_path}")
        # Opcional: eliminar el archivo y directorio de prueba después
        # try:
        #     os.remove(excel_path)
        #     os.rmdir(test_output_directory) # Solo si está vacío
        #     logger.info(f"Archivo y directorio de prueba eliminados: {excel_path}")
        # except OSError as e_del:
        #     logger.warning(f"No se pudo eliminar el archivo/directorio de prueba: {e_del}")
    else:
        logger.error("Fallo la prueba de guardado de Excel.")

    logger.info("Pruebas de file_utils.py finalizadas.")
