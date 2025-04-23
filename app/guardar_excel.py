import openpyxl
from colorama import Fore
import os

def save_to_excel(products, filename="productos_coronel.xlsx"):
    """
    Guarda la lista de productos en un archivo Excel (.xlsx)
    Args:
        products: Lista de diccionarios con información de productos
        filename: Nombre del archivo Excel a crear
    Returns:
        Ruta absoluta del archivo creado o None si hubo error
    """
    try:
        # Crear workbook y hoja principal
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "Productos"
        
        # Encabezados personalizados
        headers = ["Código", "Descripción", "Precio", "Imagen URL", "Imagen Local"]
        ws.append(headers)
        
        # Agregar datos
        for product in products:
            row = [
                product['codigo'],
                product['descripcion'],
                product['precio'],
                product['imagen_url'],
                product.get('imagen_local', '')
            ]
            ws.append(row)
        
        # Guardar archivo
        wb.save(filename)
        
        # Devolver ruta absoluta
        filepath = os.path.abspath(filename)
        print(Fore.GREEN + f"\n✔ Excel creado exitosamente: {filepath}" + Fore.RESET)
        return filepath
        
    except Exception as e:
        print(Fore.RED + f"\n✖ Error al guardar Excel: {str(e)}" + Fore.RESET)
        return None