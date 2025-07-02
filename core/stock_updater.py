import logging
import time
from typing import List, Dict, Any, Set

from tqdm import tqdm # Para barras de progreso si se procesan muchos productos
from colorama import Fore, Style # Para logs coloridos, aunque logging puede configurarse también

from core import tiendanube_api # API refactorizada
from core.scraper import CoronelScraper # Scraper refactorizado
from config import settings # Para configuraciones si fueran necesarias aquí

logger = logging.getLogger(__name__)

def obtener_todos_productos_tiendanube_con_sku_y_variante_id() -> List[Dict[str, Any]]:
    """
    Obtiene todos los productos de Tiendanube con su ID, SKU de variante e ID de variante.
    Utiliza la función de búsqueda de la API de Tiendanube que ya maneja paginación y caché.
    """
    logger.info("Obteniendo todos los productos de Tiendanube con detalles de variantes...")
    productos_tn_con_variantes = []

    page = 1
    per_page = 200 # Máximo usual

    # Para la barra de progreso, similar a buscar_producto_por_sku
    # Hacemos una petición inicial para obtener el X-Total-Count.
    try:
        # Usamos una función genérica de la API si existe, o construimos la llamada
        # Asumimos que tiendanube_api puede tener una función para esto o usamos requests directamente
        # Por ahora, construiremos la llamada directa como en el original pero usando el BASE_URL y HEADERS de tiendanube_api

        response_count_headers = {"Authentication": f"bearer {tiendanube_api.ACCESS_TOKEN}", "User-Agent": tiendanube_api.DEFAULT_HEADERS["User-Agent"]}
        response_count = requests.get(f"{tiendanube_api.BASE_URL}/products", headers=response_count_headers, params={'page': 1, 'per_page': 1, 'fields': 'id'})
        response_count.raise_for_status()
        total_products_api = int(response_count.headers.get('X-Total-Count', 0))
        total_pages = (total_products_api + per_page - 1) // per_page if total_products_api > 0 else 0
    except requests.RequestException as e:
        logger.error(f"Error obteniendo el total de productos de Tiendanube para la barra de progreso: {e}")
        total_pages = 10 # Un fallback para que la barra no sea infinita

    if total_pages == 0 and total_products_api > 0 : total_pages = 1

    pbar = None
    if total_pages > 0:
         pbar = tqdm(total=total_pages, desc="Obteniendo Productos de Tiendanube", unit="página", leave=False)

    while True:
        # Esta parte es similar a como `buscar_producto_por_sku` carga productos,
        # pero aquí queremos todos los productos, no buscar uno específico.
        cache_page_key = f"products_page_{page}" # Clave de caché consistente

        if cache_page_key in tiendanube_api.products_cache_mem:
            productos_pagina = tiendanube_api.products_cache_mem[cache_page_key]
            logger.debug(f"Página {page} de productos de Tiendanube cargada desde caché en memoria.")
        else:
            params = {'page': page, 'per_page': per_page, 'fields': 'id,name,variants(id,sku,stock_management,stock)'} # Campos necesarios
            # Reutilizar la llamada GET de la API de Tiendanube si es posible, o hacerla aquí
            # Por simplicidad, la hacemos aquí usando los componentes de tiendanube_api
            try:
                response = requests.get(f"{tiendanube_api.BASE_URL}/products", headers=tiendanube_api.DEFAULT_HEADERS, params=params)
                response.raise_for_status()
                productos_pagina = response.json()
                tiendanube_api.products_cache_mem[cache_page_key] = productos_pagina
                tiendanube_api.save_products_cache_to_disk() # Guardar en disco
                logger.debug(f"Página {page} de productos de Tiendanube obtenida de API y guardada en caché.")
            except requests.RequestException as e:
                logger.error(f"Error obteniendo productos de Tiendanube (página {page}): {e}", exc_info=True)
                if pbar: pbar.close()
                return [] # Retornar vacío si hay error

        if pbar: pbar.update(1)

        if not productos_pagina:
            logger.debug(f"No más productos en Tiendanube en la página {page}.")
            break

        for prod_api in productos_pagina:
            for variante_api in prod_api.get('variants', []):
                productos_tn_con_variantes.append({
                    'tiendanube_id_producto': prod_api['id'],
                    'tiendanube_id_variante': variante_api['id'],
                    'sku': variante_api.get('sku'),
                    'nombre': prod_api.get('name', {}).get('es', 'Sin nombre'), # Asumiendo 'es' para nombre
                    'stock_actual_tn': variante_api.get('stock'),
                    'maneja_stock_tn': variante_api.get('stock_management', False)
                })

        if len(productos_pagina) < per_page:
            break
        page += 1
        if page > total_pages and total_pages > 0 : break


    if pbar: pbar.close()
    logger.info(f"Obtenidos {len(productos_tn_con_variantes)} variantes de productos desde Tiendanube.")
    return productos_tn_con_variantes


def sincronizar_stock_tiendanube(headless_scraper=True, callback_progreso=None):
    """
    Sincroniza el stock de Tiendanube con los productos disponibles en Coronel Mayorista.
    - Productos en Coronel: stock "infinito" (o un número alto como 999999) en Tiendanube.
    - Productos NO en Coronel: stock 0 en Tiendanube.
    - Omite SKUs que terminan en "-local".
    """
    logger.info("Iniciando proceso de sincronización de stock...")

    # 1. Obtener lista de productos actuales de Coronel Mayorista (solo SKUs)
    logger.info("Obteniendo SKUs actuales de Coronel Mayorista...")
    scraper = CoronelScraper(headless=headless_scraper)
    productos_coronel_actuales = []
    try:
        # El scraper necesita estar logueado para obtener_stock_productos_rapido
        if not scraper.login():
            logger.error("Fallo en el login de Coronel Mayorista. No se puede continuar con la sincronización de stock.")
            return False

        # Este método ya hace el scraping de todas las páginas y devuelve [{codigo: "SKU", stock: 999999}, ...]
        productos_coronel_actuales = scraper.obtener_stock_productos_rapido()
    finally:
        scraper.close() # Asegurar que el navegador se cierre

    if not productos_coronel_actuales:
        logger.warning("No se obtuvieron productos de Coronel Mayorista. Verifique el scraping. Asumiendo que no hay stock para ningún producto.")
        # Si no hay productos en Coronel, todos los de Tiendanube deberían ir a stock 0 (excepto -local)

    skus_coronel_actuales: Set[str] = {p['codigo'] for p in productos_coronel_actuales}
    logger.info(f"Encontrados {len(skus_coronel_actuales)} SKUs únicos en Coronel Mayorista.")

    # 2. Obtener todos los productos/variantes de Tiendanube
    # Esta función ya está definida en este módulo
    productos_tiendanube = obtener_todos_productos_tiendanube_con_sku_y_variante_id()
    if not productos_tiendanube:
        logger.warning("No se encontraron productos en Tiendanube para actualizar stock. Proceso finalizado.")
        return True # No es un error si no hay nada que actualizar

    # 3. Comparar y actualizar
    actualizaciones = {'infinito': 0, 'cero': 0, 'omitido_local': 0, 'sin_cambio': 0, 'error': 0}
    total_a_procesar = len(productos_tiendanube)

    logger.info(f"Procesando {total_a_procesar} variantes de Tiendanube para actualizar stock...")

    for i, variante_tn in enumerate(productos_tiendanube):
        sku_tn = variante_tn.get('sku')
        id_producto_tn = variante_tn['tiendanube_id_producto']
        id_variante_tn = variante_tn['tiendanube_id_variante']
        nombre_tn = variante_tn['nombre']
        stock_actual_tn = variante_tn['stock_actual_tn']
        maneja_stock_tn = variante_tn['maneja_stock_tn']

        if callback_progreso:
            callback_progreso(i + 1, total_a_procesar, f"Procesando: {sku_tn if sku_tn else nombre_tn}")

        if not sku_tn:
            logger.warning(f"Variante ID {id_variante_tn} del producto '{nombre_tn}' (ID: {id_producto_tn}) no tiene SKU. Se omite.")
            continue

        if sku_tn.endswith('-local'):
            logger.info(f"SKU '{sku_tn}' ({nombre_tn}) termina en '-local'. Se omite actualización de stock.")
            actualizaciones['omitido_local'] += 1
            continue

        nuevo_stock_valor: Optional[int] = None # None para ilimitado, int para valor específico

        if sku_tn in skus_coronel_actuales:
            nuevo_stock_valor = 999999 # Stock "infinito"
            # Verificar si ya tiene stock "infinito" o un stock alto y no se maneja stock
            if not maneja_stock_tn or (maneja_stock_tn and stock_actual_tn is not None and stock_actual_tn >= 999999): # Considerar si el stock actual ya es "infinito"
                logger.debug(f"SKU '{sku_tn}' ({nombre_tn}) ya tiene stock 'infinito' o no gestionado. No se actualiza.")
                actualizaciones['sin_cambio'] += 1
                continue
            else:
                 logger.info(f"SKU '{sku_tn}' ({nombre_tn}) encontrado en Coronel. Estableciendo stock a {nuevo_stock_valor}.")
                 actualizaciones['infinito'] += 1
        else:
            nuevo_stock_valor = 0 # Stock cero
            # Verificar si ya tiene stock 0
            if maneja_stock_tn and stock_actual_tn == 0:
                logger.debug(f"SKU '{sku_tn}' ({nombre_tn}) ya tiene stock 0. No se actualiza.")
                actualizaciones['sin_cambio'] += 1
                continue
            else:
                logger.info(f"SKU '{sku_tn}' ({nombre_tn}) NO encontrado en Coronel. Estableciendo stock a {nuevo_stock_valor}.")
                actualizaciones['cero'] += 1

        # Realizar la actualización en Tiendanube usando la función de la API
        # La función `actualizar_stock_variante` ya maneja el rate limiting.
        exito_api = tiendanube_api.actualizar_stock_variante(id_producto_tn, id_variante_tn, nuevo_stock_valor)

        if not exito_api:
            logger.error(f"Fallo al actualizar stock para SKU '{sku_tn}' ({nombre_tn}) en Tiendanube.")
            actualizaciones['error'] += 1

        # Pequeña pausa adicional si se realizan muchas actualizaciones, aunque el decorador ya maneja rate limits.
        # time.sleep(0.1) # Opcional

    logger.info(Fore.GREEN + "--- Resumen de Sincronización de Stock ---" + Style.RESET_ALL)
    logger.info(f"  Productos con stock 'infinito' (actualizados o nuevos): {actualizaciones['infinito']}")
    logger.info(f"  Productos con stock 0 (actualizados o nuevos): {actualizaciones['cero']}")
    logger.info(f"  Productos omitidos (SKU termina en '-local'): {actualizaciones['omitido_local']}")
    logger.info(f"  Productos sin cambios de stock necesarios: {actualizaciones['sin_cambio']}")
    if actualizaciones['error'] > 0:
        logger.error(Fore.RED + f"  Errores durante la actualización de stock en API: {actualizaciones['error']}" + Style.RESET_ALL)
    else:
        logger.info(Fore.GREEN + "  No se reportaron errores de API durante la actualización de stock." + Style.RESET_ALL)

    return actualizaciones['error'] == 0


if __name__ == '__main__':
    # Bloque de prueba (ejecutar con python -m core.stock_updater)
    if not logging.getLogger().hasHandlers():
        from config.logging_config import setup_logging
        setup_logging()

    logger.info("Probando el StockUpdater...")

    # Para probar, asegúrate que:
    # 1. Las credenciales de Tiendanube y Coronel estén en .env o configuradas.
    # 2. Haya productos en tu Tiendanube para ver los cambios.
    # 3. El scraper de Coronel pueda funcionar (chromedriver, etc.)

    # Definir un callback de progreso simple para la consola
    def progreso_consola(actual, total, mensaje=""):
        print(f"\rProgreso: {actual}/{total} - {mensaje[:50].ljust(50)}", end="")
        if actual == total:
            print() # Nueva línea al final

    # Ejecutar la sincronización
    # Poner headless_scraper=False para ver el navegador durante el scraping de Coronel.
    # exito_sincro = sincronizar_stock_tiendanube(headless_scraper=True, callback_progreso=progreso_consola)

    # if exito_sincro:
    #     logger.info(Fore.GREEN + "Sincronización de stock completada exitosamente (o sin errores de API)." + Style.RESET_ALL)
    # else:
    #     logger.error(Fore.RED + "Sincronización de stock finalizada con errores de API." + Style.RESET_ALL)

    # Prueba de obtener productos de Tiendanube (para depurar esa parte)
    # productos_tn = obtener_todos_productos_tiendanube_con_sku_y_variante_id()
    # if productos_tn:
    #     logger.info(f"Primeros 5 productos de Tiendanube (o menos):")
    #     for p_tn in productos_tn[:5]:
    #         logger.info(f"  ID: {p_tn['tiendanube_id_producto']}, SKU: {p_tn['sku']}, Nombre: {p_tn['nombre']}, Stock TN: {p_tn['stock_actual_tn']}")
    # else:
    #     logger.info("No se obtuvieron productos de Tiendanube para la prueba.")

    logger.info("Pruebas de StockUpdater finalizadas.")
