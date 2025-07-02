import logging
import time
from typing import List, Dict, Any, Callable, Optional

from tqdm import tqdm # Para barras de progreso
from colorama import Fore, Style # Para logs coloridos

from core import data_manager # Para obtener productos de la BD local
from core import tiendanube_api # Para interactuar con Tiendanube
from config import settings # Para configuraciones por defecto

logger = logging.getLogger(__name__)

class ProductUploader:
    def __init__(self,
                 ganancia_porcentaje: Optional[float] = None,
                 descargar_imagenes: Optional[bool] = None,
                 callback_progreso: Optional[Callable[[int, int, str], None]] = None):
        """
        Inicializa el ProductUploader.

        Args:
            ganancia_porcentaje (float, opcional): Porcentaje de ganancia a aplicar.
                                                   Si es None, usa DEFAULT_GANANCIA_PORCENTAJE de settings.
            descargar_imagenes (bool, opcional): Si se deben descargar imágenes o usar URLs.
                                                Si es None, usa DEFAULT_DOWNLOAD_IMAGES de settings.
            callback_progreso (Callable, opcional): Función para reportar progreso.
                                                    Recibe (actual, total, mensaje).
        """
        self.ganancia_porcentaje = ganancia_porcentaje if ganancia_porcentaje is not None else settings.DEFAULT_GANANCIA_PORCENTAJE
        self.descargar_imagenes = descargar_imagenes if descargar_imagenes is not None else settings.DEFAULT_DOWNLOAD_IMAGES
        self.callback_progreso = callback_progreso

        logger.info(f"ProductUploader inicializado con: Ganancia: {self.ganancia_porcentaje}%, Descargar Imágenes: {self.descargar_imagenes}")

    def _procesar_un_producto(self, producto_db: Dict[str, Any]) -> Dict[str, Any]:
        """
        Procesa un solo producto: lo busca en Tiendanube y decide si crearlo o actualizarlo.
        Retorna un diccionario con el resultado del procesamiento.
        """
        sku_producto = producto_db.get('codigo')
        if not sku_producto:
            logger.warning(f"Producto en BD sin SKU. Datos: {producto_db}")
            return {'sku': None, 'accion': 'omitido', 'status': 'error', 'mensaje': 'Producto sin SKU'}

        logger.debug(f"Procesando producto SKU: {sku_producto} - {producto_db.get('descripcion', '')[:30]}...")
        start_time = time.time()

        try:
            # Asegurarse que el producto_db tenga todos los campos esperados por la API de Tiendanube,
            # incluso si son None. La API los manejará.
            # Los campos principales son: codigo, descripcion, precio, categoria, subcategoria,
            # codigo_de_barras, imagen_url, imagen_local, stock.
            # La función data_manager.obtener_todos_los_productos() ya debería devolverlos.

            id_producto_tiendanube = tiendanube_api.buscar_producto_por_sku(sku_producto)

            if id_producto_tiendanube:
                logger.info(f"SKU {sku_producto} encontrado en Tiendanube (ID: {id_producto_tiendanube}). Actualizando...")
                exito = tiendanube_api.actualizar_producto_tiendanube(
                    id_tiendanube=id_producto_tiendanube,
                    producto_data=producto_db,
                    ganancia_porcentaje=self.ganancia_porcentaje,
                    descargar_imagenes=self.descargar_imagenes
                )
                accion = 'actualizado'
                status = 'exito' if exito else 'error'
            else:
                logger.info(f"SKU {sku_producto} NO encontrado en Tiendanube. Creando...")
                nuevo_id = tiendanube_api.crear_producto_tiendanube(
                    producto_data=producto_db,
                    ganancia_porcentaje=self.ganancia_porcentaje,
                    descargar_imagenes=self.descargar_imagenes
                )
                accion = 'creado'
                status = 'exito' if nuevo_id else 'error'

            elapsed_time = time.time() - start_time
            mensaje = f"Producto {sku_producto} {accion} {'exitosamente' if status == 'exito' else 'con error'} en {elapsed_time:.2f}s."
            if status == 'exito': logger.info(Fore.GREEN + mensaje + Style.RESET_ALL)
            else: logger.error(Fore.RED + mensaje + Style.RESET_ALL)

            return {'sku': sku_producto, 'accion': accion, 'status': status, 'tiempo_s': elapsed_time}

        except Exception as e:
            elapsed_time = time.time() - start_time
            logger.error(f"Excepción no controlada procesando SKU {sku_producto}: {e}", exc_info=True)
            return {'sku': sku_producto, 'accion': 'error_critico', 'status': 'error', 'mensaje': str(e), 'tiempo_s': elapsed_time}


    def subir_productos_a_tiendanube(self):
        """
        Obtiene todos los productos de la base de datos local y los sube (crea o actualiza) a Tiendanube.
        """
        logger.info("Iniciando proceso de subida/actualización de productos a Tiendanube...")

        # 0. Opcional: Limpiar caché de productos de Tiendanube si se desea forzar recarga total.
        #    La caché de productos de Tiendanube ahora se maneja más internamente en tiendanube_api.py
        #    y se invalida (borra y guarda vacía) tras crear/actualizar productos.
        #    Si se quiere una limpieza explícita antes de un gran lote:
        # tiendanube_api.limpiar_cache_productos_tiendanube()
        # logger.info("Caché de productos de Tiendanube limpiada antes de la subida.")


        # 1. Obtener productos de la base de datos local
        productos_db = data_manager.obtener_todos_los_productos()
        if not productos_db:
            logger.warning("No hay productos en la base de datos local para subir. Proceso finalizado.")
            return

        total_productos = len(productos_db)
        logger.info(f"Se procesarán {total_productos} productos desde la base de datos local.")

        # Mostrar algunos productos de ejemplo (como en el script original)
        logger.info(Fore.GREEN + "\n" + "="*50)
        logger.info(f" DETALLE DE EJEMPLO - PRIMEROS {min(3, total_productos)} PRODUCTOS DE LA BD LOCAL")
        logger.info("="*50 + Style.RESET_ALL)
        for i, p_db_ejemplo in enumerate(productos_db[:3]):
            logger.info(Fore.YELLOW + f"\nEjemplo Producto BD #{i+1}" + "-"*30 + Style.RESET_ALL)
            for k, v in p_db_ejemplo.items():
                logger.info(f"  {k}: {v}")
        logger.info(Fore.GREEN + "\n" + "="*50 + Style.RESET_ALL)


        # 2. Procesar cada producto
        resultados_procesamiento = []
        productos_exitosos = 0
        productos_fallidos = 0

        for i, producto_actual_db in enumerate(productos_db):
            sku_actual = producto_actual_db.get('codigo', 'SKU_DESCONOCIDO')
            desc_actual = producto_actual_db.get('descripcion', 'DESC_DESCONOCIDA')[:30]
            if self.callback_progreso:
                self.callback_progreso(i + 1, total_productos, f"SKU: {sku_actual} - {desc_actual}")

            resultado_item = self._procesar_un_producto(producto_actual_db)
            resultados_procesamiento.append(resultado_item)

            if resultado_item['status'] == 'exito':
                productos_exitosos += 1
            else:
                productos_fallidos += 1

        # 3. Resumen final
        logger.info(Fore.CYAN + "\n" + "--- RESUMEN FINAL DE SUBIDA/ACTUALIZACIÓN ---" + Style.RESET_ALL)
        logger.info(f"Total de productos en BD local: {total_productos}")
        logger.info(Fore.GREEN + f"Productos procesados con éxito (creados o actualizados): {productos_exitosos}" + Style.RESET_ALL)
        if productos_fallidos > 0:
            logger.error(Fore.RED + f"Productos con errores durante el procesamiento: {productos_fallidos}" + Style.RESET_ALL)
            logger.warning("Revise los logs anteriores para detalles sobre los errores.")

        # Calcular estadísticas de acciones
        creados = len([r for r in resultados_procesamiento if r['accion'] == 'creado' and r['status'] == 'exito'])
        actualizados = len([r for r in resultados_procesamiento if r['accion'] == 'actualizado' and r['status'] == 'exito'])
        omitidos_sin_sku = len([r for r in resultados_procesamiento if r['accion'] == 'omitido'])

        logger.info(f"  - Creados exitosamente: {creados}")
        logger.info(f"  - Actualizados exitosamente: {actualizados}")
        if omitidos_sin_sku > 0:
            logger.warning(f"  - Omitidos (sin SKU en BD): {omitidos_sin_sku}")

        # 4. Opcional: Limpiar caché de productos de Tiendanube al final
        #    Esto podría ser útil si se espera que otras partes del sistema accedan a datos frescos
        #    inmediatamente, aunque la caché se invalida por producto durante la operación.
        # tiendanube_api.limpiar_cache_productos_tiendanube()
        # logger.info("Caché de productos de Tiendanube limpiada después de la subida.")

        logger.info("Proceso de subida/actualización de productos a Tiendanube finalizado.")


if __name__ == '__main__':
    # Bloque de prueba (ejecutar con python -m core.product_uploader)
    if not logging.getLogger().hasHandlers():
        from config.logging_config import setup_logging
        setup_logging()

    logger.info("Probando el ProductUploader...")

    # Asegúrate que:
    # 1. Haya productos en tu `productos.db` (puedes generarlos con el scraper).
    # 2. Las credenciales de Tiendanube estén configuradas.
    # 3. La API de Tiendanube y DataManager funcionen.

    # Definir un callback de progreso simple para la consola
    def progreso_consola_uploader(actual, total, mensaje=""):
        print(f"\rSubiendo: {actual}/{total} - {mensaje[:50].ljust(50)}", end="")
        if actual == total:
            print() # Nueva línea al final

    # Crear instancia y ejecutar
    # Puedes probar con diferentes configuraciones de ganancia e imágenes:
    # uploader = ProductUploader(ganancia_porcentaje=50, descargar_imagenes=False, callback_progreso=progreso_consola_uploader)
    # uploader = ProductUploader(callback_progreso=progreso_consola_uploader) # Usará defaults de settings.py

    # uploader.subir_productos_a_tiendanube()

    logger.info("Pruebas de ProductUploader finalizadas.")
    logger.info("NOTA: Para una prueba completa, primero ejecuta el scraper para poblar productos.db, luego este uploader.")
    logger.info("Ejemplo: python -m core.scraper (para poblar la BD con algunos productos)")
    logger.info("Luego: python -m core.product_uploader (para subir esos productos)")
