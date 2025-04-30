from api_tiendanube import crear_producto, buscar_producto_por_sku, actualizar_producto
from colorama import Fore
import sqlite3
import json

PATH = "c:/Users/USER/OneDrive/Proyectos/JG-STORE/Scraping/productos_libreria.db"




def obtener_productos_de_db():
    # Conectar a la base de datos
    conexion = sqlite3.connect(PATH)
    cursor = conexion.cursor()
    
    # Obtener todos los productos
    cursor.execute("SELECT * FROM productos")
    productos = cursor.fetchall()
    
    # Convertir a lista de diccionarios con la estructura deseada
    lista_productos = []
    for producto in productos:
        lista_productos.append({
            'codigo': producto[0],          # codigo
            'codigo_de_barras': producto[1], # codigo_barra
            'descripcion': producto[2],     # descripcion
            'precio': producto[3],          # precio
            'imagen_url': producto[4],      # imagen_url
            'imagen_local': producto[5],    # imagen_local
            'variante': producto[6].replace('-', '') if producto[6] else None,  # variante
            'categoria': producto[7],       # categoria
            'subcategoria': producto[8],    # subcategoria
            'peso_kg': producto[9],         # peso_kg
            'ancho_cm': producto[10],       # ancho_cm
            'alto_cm': producto[11],        # alto_cm
            'profundidad_cm': producto[12]  # profundidad_cm
        })
    
    # Cerrar conexión
    conexion.close()
    
    return lista_productos
# Obtener los productos en formato JSON
todos_los_productos = obtener_productos_de_db()

# Si quieres ver el resultado (opcional)
#print(todos_los_productos)





# Mostrar resumen
print(Fore.GREEN + "\n" + "="*50)
print(f" SCRAPING COMPLETADO - {len(todos_los_productos)} PRODUCTOS ENCONTRADOS ")
print("="*50 + Fore.RESET)

# Mostrar TODOS los productos encontrados
print(Fore.GREEN + "\n" + "="*50)
print(f" DETALLE COMPLETO DE {len(todos_los_productos)} PRODUCTOS ENCONTRADOS, se mostraran 3 productos como muestra ")
print("="*50 + Fore.RESET)

for i, producto in enumerate(todos_los_productos[:3], 1):
    # Encabezado del producto
    print(Fore.YELLOW + f"\nProducto #{i}" + "-"*40 + Fore.RESET)
    
    # Información base
    print(f"{Fore.CYAN}Código:{Fore.RESET} {producto['codigo']}")
    print(f"{Fore.CYAN}Descripción:{Fore.RESET} {producto['descripcion']}")
    print(f"{Fore.CYAN}Precio:{Fore.RESET} {producto['precio']}")
    print(f"{Fore.CYAN}Imagen local:{Fore.RESET} {producto['imagen_local']}")
    print(f"{Fore.CYAN}Codigo de Barras:{Fore.RESET} {producto['codigo_de_barras']}")
    print(f"{Fore.CYAN}imagen_url:{Fore.RESET} {producto['imagen_url']}")
    print(f"{Fore.CYAN}Categoria:{Fore.RESET} {producto['categoria']}")
    print(f"{Fore.CYAN}Subcategoria:{Fore.RESET} {producto['subcategoria']}")
    print(f"{Fore.CYAN}Dimensiones:{Fore.RESET} {producto['peso_kg']}, {producto['ancho_cm']}, {producto['alto_cm']}, {producto['profundidad_cm']}")
    
    # Mostrar variante solo si existe
    if producto['variante']:
        print(f"{Fore.MAGENTA}Variante:{Fore.RESET} {producto['variante'].replace('-', '')}")

print(Fore.GREEN + "\n" + "="*50)
print(f" FIN DEL LISTADO - {len(todos_los_productos)} PRODUCTOS ")
print("="*50 + Fore.RESET)


 # 3. Procesar cada producto con Tiendanube
print(Fore.CYAN + "\nINICIANDO SINCRONIZACION CON TIENDANUBE..." + Fore.RESET)

for producto in todos_los_productos:
    # Buscar si el producto ya existe
    producto_id = buscar_producto_por_sku(producto['codigo'])
    
    if producto_id:
        # Actualizar producto existente
        if actualizar_producto(producto_id, producto):
            print(Fore.YELLOW + f"↻ Producto actualizado: {producto['codigo']}" + Fore.RESET)
        else:
            print(Fore.RED + f"✖ Error actualizando: {producto['codigo']}" + Fore.RESET)
    else:
        # Crear nuevo producto
        nuevo_id = crear_producto(producto)
        if nuevo_id:
            print(Fore.GREEN + f"✔ Nuevo producto creado (ID: {nuevo_id}): {producto['codigo']}" + Fore.RESET)
        else:
            print(Fore.RED + f"✖ Error creando: {producto['codigo']}" + Fore.RESET)

print(Fore.CYAN + "\nPROCESO COMPLETADO" + Fore.RESET)