
import requests
from colorama import Fore, Style, init

# Inicializar colorama
init()

# Configuración de la API de Tiendanube
ACCESS_TOKEN = "cdcad052f53bae4972979dbf6900925d4e9a36dc"
STORE_ID = "5950659"
BASE_URL = f"https://api.tiendanube.com/v1/{STORE_ID}"
headers = {
    "Authentication": f"bearer {ACCESS_TOKEN}",
    "Content-Type": "application/json",
    "User-Agent": "API-KEY (jgstore244@gmail.com)"
}

def get_all_categories():
    """
    Obtiene todas las categorías usando paginación
    """
    all_categories = []
    page = 1
    per_page = 200  # Máximo permitido por la API
    
    while True:
        print(f"{Fore.CYAN}Obteniendo página {page} de categorías...{Style.RESET_ALL}")
        response = requests.get(
            f"{BASE_URL}/categories",
            headers=headers,
            params={
                'page': page,
                'per_page': per_page
            }
        )
        
        if response.status_code != 200:
            print(f"{Fore.RED}Error al obtener categorías: {response.text}{Style.RESET_ALL}")
            break
            
        categories = response.json()
        if not categories:  # Si no hay más categorías
            break
            
        all_categories.extend(categories)
        
        # Verificar si hay más páginas
        if len(categories) < per_page:
            break
            
        page += 1
    
    return all_categories

def eliminar_categorias_duplicadas():
    """
    Elimina las categorías duplicadas con el nombre 'LIBRERÍA'
    """
    try:
        # Obtener todas las categorías con paginación
        categories = get_all_categories()
        
        print(f"\n{Fore.CYAN}Categorías encontradas ({len(categories)} total):{Style.RESET_ALL}")
        for cat in categories:
            name = cat.get('name', {}).get('es', '')
            print(f"  ID: {cat['id']} - Nombre: {name} - Productos: {cat.get('total_products', 0)}")
        
        # Filtrar categorías que contengan 'LIBRERIA' o 'LIBRERÍA'
        libreria_categories = [cat for cat in categories 
                              if 'LIBRERIA' in cat.get('name', {}).get('es', '').upper() or 
                                 'LIBRERÍA' in cat.get('name', {}).get('es', '').upper()]
        total_found = len(libreria_categories)
        
        if total_found == 0:
            print(f"{Fore.YELLOW}No se encontraron categorías con el nombre 'LIBRERÍA'{Style.RESET_ALL}")
            return
        
        print(f"{Fore.GREEN}Se encontraron {total_found} categorías con el nombre 'LIBRERÍA'{Style.RESET_ALL}")
        
        # Mantener la primera categoría y eliminar el resto
        keep_category = libreria_categories[0]
        categories_to_delete = libreria_categories[1:]
        
        print(f"\n{Fore.CYAN}Manteniendo categoría:{Style.RESET_ALL}")
        print(f"  ID: {keep_category['id']}")
        print(f"  Nombre: {keep_category['name']['es']}")
        print(f"  Productos: {keep_category.get('total_products', 0)}")
        
        if not categories_to_delete:
            print(f"\n{Fore.GREEN}No hay categorías duplicadas para eliminar{Style.RESET_ALL}")
            return
        
        print(f"\n{Fore.YELLOW}Eliminando {len(categories_to_delete)} categorías duplicadas...{Style.RESET_ALL}")
        
        # Eliminar categorías duplicadas
        for cat in categories_to_delete:
            try:
                delete_response = requests.delete(
                    f"{BASE_URL}/categories/{cat['id']}",
                    headers=headers
                )
                
                if delete_response.status_code == 200:
                    print(f"{Fore.GREEN}✓ Categoría {cat['id']} eliminada correctamente{Style.RESET_ALL}")
                else:
                    print(f"{Fore.RED}✗ Error al eliminar categoría {cat['id']}: {delete_response.text}{Style.RESET_ALL}")
                    
            except Exception as e:
                print(f"{Fore.RED}Error al eliminar categoría {cat['id']}: {str(e)}{Style.RESET_ALL}")
        
        print(f"\n{Fore.GREEN}¡Proceso completado!{Style.RESET_ALL}")
        
    except Exception as e:
        print(f"{Fore.RED}Error al obtener categorías: {str(e)}{Style.RESET_ALL}")

# Ejecutar la función
if __name__ == '__main__':
    print(f"{Fore.CYAN}=== Iniciando limpieza de categorías duplicadas ==={Style.RESET_ALL}")
    eliminar_categorias_duplicadas()
