import requests
from colorama import Fore, Style, init
from collections import defaultdict

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

def analizar_categorias():
    """
    Analiza y muestra estadísticas de las categorías
    """
    try:
        # Obtener todas las categorías
        categories = get_all_categories()
        
        if not categories:
            print(f"{Fore.YELLOW}No se encontraron categorías{Style.RESET_ALL}")
            return
        
        # Contadores y estadísticas
        total_categories = len(categories)
        categories_with_products = 0
        total_products = 0
        name_counts = defaultdict(int)
        duplicate_names = set()
        
        # Analizar cada categoría
        for cat in categories:
            name = cat.get('name', {}).get('es', '').strip()
            products = cat.get('total_products', 0)
            
            # Contar productos
            if products > 0:
                categories_with_products += 1
                total_products += products
            
            # Contar nombres duplicados
            name_counts[name] += 1
            if name_counts[name] > 1:
                duplicate_names.add(name)
        
        # Mostrar resultados
        print(f"\n{Fore.GREEN}=== Estadísticas de Categorías ==={Style.RESET_ALL}")
        print(f"\n{Fore.CYAN}Totales:{Style.RESET_ALL}")
        print(f"  • Total de categorías: {total_categories}")
        print(f"  • Categorías con productos: {categories_with_products}")
        print(f"  • Categorías sin productos: {total_categories - categories_with_products}")
        print(f"  • Total de productos en categorías: {total_products}")
        
        if duplicate_names:
            print(f"\n{Fore.YELLOW}Categorías Duplicadas:{Style.RESET_ALL}")
            for name in sorted(duplicate_names):
                count = name_counts[name]
                print(f"  • '{name}' aparece {count} veces")
        
        print(f"\n{Fore.CYAN}Listado de Categorías:{Style.RESET_ALL}")
        for cat in sorted(categories, key=lambda x: x.get('name', {}).get('es', '')):
            name = cat.get('name', {}).get('es', '')
            products = cat.get('total_products', 0)
            color = Fore.GREEN if products > 0 else Fore.RED
            print(f"  {color}• {name}: {products} productos{Style.RESET_ALL}")
        
    except Exception as e:
        print(f"{Fore.RED}Error: {str(e)}{Style.RESET_ALL}")

def get_all_products():
    """
    Descarga todos los productos de Tienda Nube con paginación
    """
    all_products = []
    page = 1
    per_page = 200
    while True:
        print(f"{Fore.CYAN}Obteniendo página {page} de productos...{Style.RESET_ALL}")
        response = requests.get(
            f"{BASE_URL}/products",
            headers=headers,
            params={
                'page': page,
                'per_page': per_page
            }
        )
        if response.status_code != 200:
            print(f"{Fore.RED}Error al obtener productos: {response.text}{Style.RESET_ALL}")
            break
        products = response.json()
        if not products:
            break
        all_products.extend(products)
        if len(products) < per_page:
            break
        page += 1
    return all_products

def normalizar_nombre(nombre):
    """Normaliza nombre para comparación (mayúsculas, sin tildes)"""
    import unicodedata
    nombre = nombre.upper().strip()
    nombre = ''.join(
        c for c in unicodedata.normalize('NFD', nombre)
        if unicodedata.category(c) != 'Mn'
    )
    return nombre

def mover_productos_libreria():
    print(f"{Fore.CYAN}\n=== Iniciando organización de productos en LIBRERIA ==={Style.RESET_ALL}")
    categorias = get_all_categories()
    productos = get_all_products()

    # 1. Identificar IDs de categorías LIBRERIA/LIBRERÍA
    libreria_cats = [cat for cat in categorias if normalizar_nombre(cat.get('name', {}).get('es', '')) == 'LIBRERIA']
    if not libreria_cats:
        print(f"{Fore.RED}No se encontraron categorías LIBRERIA/LIBRERÍA{Style.RESET_ALL}")
        return
    principal = libreria_cats[0]
    principal_id = principal['id']
    duplicadas = [cat for cat in libreria_cats if cat['id'] != principal_id]
    print(f"{Fore.GREEN}Categoría principal: {principal_id} - {principal['name']['es']}{Style.RESET_ALL}")
    print(f"{Fore.YELLOW}Categorías duplicadas: {[cat['id'] for cat in duplicadas]}{Style.RESET_ALL}")

    # 2. Analizar productos y preparar movimientos
    productos_a_mover = []
    for prod in productos:
        cats = prod.get('categories', [])
        if not cats:
            continue
        for cat in cats:
            if cat in [d['id'] for d in duplicadas]:
                productos_a_mover.append({
                    'id': prod['id'],
                    'name': prod.get('name', {}).get('es', ''),
                    'from_cat': cat,
                    'to_cat': principal_id,
                    'full': prod
                })
                break
    if not productos_a_mover:
        print(f"{Fore.GREEN}No hay productos que mover de categorías duplicadas.{Style.RESET_ALL}")
    else:
        print(f"{Fore.YELLOW}Se moverán {len(productos_a_mover)} productos a la categoría principal...{Style.RESET_ALL}")
        for p in productos_a_mover:
            print(f"  Producto {p['id']} - {p['name']} de {p['from_cat']} a {p['to_cat']}")
        # 3. Realizar movimientos
        for p in productos_a_mover:
            nuevas_cats = [cat if cat != p['from_cat'] else p['to_cat'] for cat in p['full']['categories']]
            # Evitar duplicados
            nuevas_cats = list(dict.fromkeys(nuevas_cats))
            update_url = f"{BASE_URL}/products/{p['id']}"
            resp = requests.put(update_url, headers=headers, json={'categories': nuevas_cats})
            if resp.status_code == 200:
                print(f"{Fore.GREEN}✓ Producto {p['id']} actualizado{Style.RESET_ALL}")
            else:
                print(f"{Fore.RED}✗ Error al actualizar {p['id']}: {resp.text}{Style.RESET_ALL}")
    # 4. Eliminar categorías duplicadas si ya no tienen productos
    for cat in duplicadas:
        print(f"{Fore.YELLOW}Intentando eliminar categoría duplicada {cat['id']}...{Style.RESET_ALL}")
        del_resp = requests.delete(f"{BASE_URL}/categories/{cat['id']}", headers=headers)
        if del_resp.status_code == 200:
            print(f"{Fore.GREEN}✓ Categoría {cat['id']} eliminada correctamente{Style.RESET_ALL}")
        else:
            print(f"{Fore.RED}✗ Error al eliminar {cat['id']}: {del_resp.text}{Style.RESET_ALL}")

if __name__ == '__main__':
    mover_productos_libreria()

