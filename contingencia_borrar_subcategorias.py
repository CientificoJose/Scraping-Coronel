import requests
import json
import time

# Variables globales que se configurarán con las credenciales del usuario
STORE_ID = "5950659"
ACCESS_TOKEN = "cdcad052f53bae4972979dbf6900925d4e9a36dc"
BASE_URL = f"https://api.tiendanube.com/v1/{STORE_ID}"
HEADERS = {
    "Authentication": f"bearer {ACCESS_TOKEN}",
    "Content-Type": "application/json",
    "User-Agent": "API-KEY (jgstore244@gmail.com)"
}



def configurar_credenciales():
    """Solicita y configura las credenciales de la API de Tiendanube."""
    global STORE_ID, ACCESS_TOKEN, BASE_URL, HEADERS
    
    print("\n--- Configuración de Credenciales ---")
    # Permite reingresar credenciales si ya existen y el usuario quiere cambiarlas, 
    # o si estaban vacías.
    store_id_input = input(f"Por favor, ingresa tu STORE_ID de Tiendanube (actual: {STORE_ID if STORE_ID else 'No establecido'}): ").strip()
    if store_id_input:
        STORE_ID = store_id_input

    access_token_input = input(f"Por favor, ingresa tu ACCESS_TOKEN de Tiendanube (actual: {'*' * len(ACCESS_TOKEN) if ACCESS_TOKEN else 'No establecido'}): ").strip()
    if access_token_input:
        ACCESS_TOKEN = access_token_input
    
    # Obtener el email actual del User-Agent si existe
    current_email_user_agent = HEADERS.get("User-Agent", "CustomPythonScript (No establecido)").replace("CustomPythonScript (","").replace(")","")
    if current_email_user_agent == "No establecido": current_email_user_agent = ""

    email_user_agent_input = input(f"Ingresa un email para el User-Agent (ej: tuemail@example.com) (actual: {current_email_user_agent if current_email_user_agent else 'No establecido'}): ").strip()
    if email_user_agent_input:
        email_user_agent = email_user_agent_input
    elif current_email_user_agent: # Mantener el actual si no se ingresa uno nuevo y existía uno
        email_user_agent = current_email_user_agent
    else: # Si no hay actual y no se ingresa nuevo
        print("Error: El email para User-Agent es obligatorio si no hay uno configurado previamente.")
        return False


    if not STORE_ID or not ACCESS_TOKEN or not email_user_agent:
        print("Error: STORE_ID, ACCESS_TOKEN y el email para User-Agent son obligatorios.")
        return False

    BASE_URL = f"https://api.tiendanube.com/v1/{STORE_ID}"
    HEADERS = {
        "Authentication": f"bearer {ACCESS_TOKEN}",
        "Content-Type": "application/json",
        "User-Agent": f"CustomPythonScript ({email_user_agent})" 
    }
    print("Credenciales configuradas/actualizadas exitosamente.")
    return True

def obtener_todas_las_categorias():
    """
    Obtiene todas las categorías de la tienda, manejando la paginación.
    """
    if not BASE_URL:
        print("Error: Las credenciales no han sido configuradas. Llama a configurar_credenciales() primero (Opción 6).")
        return None

    todas_las_categorias_lista = []
    pagina = 1
    por_pagina = 200  # Máximo permitido por la API de Tiendanube

    print("\nObteniendo categorías de la tienda...")
    while True:
        try:
            # Incluir 'description' y 'parent' en los fields para una información más completa si se necesitara
            params = {"page": pagina, "per_page": por_pagina, "fields": "id,name,parent,handle,description"}
            response = requests.get(f"{BASE_URL}/categories", headers=HEADERS, params=params)
            response.raise_for_status()  # Lanza una excepción para errores 4XX/5XX
            
            categorias_pagina_actual = response.json()
            if not categorias_pagina_actual:  # No hay más categorías
                break
            
            todas_las_categorias_lista.extend(categorias_pagina_actual)
            print(f"  Página {pagina} obtenida, {len(categorias_pagina_actual)} categorías.")

            if len(categorias_pagina_actual) < por_pagina: # Última página
                break
            
            pagina += 1
            time.sleep(0.5) # Pequeña pausa para no saturar la API

        except requests.exceptions.RequestException as e:
            print(f"Error al obtener categorías (página {pagina}): {e}")
            if response is not None:
                print(f"Respuesta del servidor ({response.status_code}): {response.text}")
            return None
        except json.JSONDecodeError:
            print(f"Error al decodificar JSON de la respuesta (página {pagina}). Respuesta: {response.text}")
            return None

    print(f"Total de categorías obtenidas: {len(todas_las_categorias_lista)}")
    return todas_las_categorias_lista

def construir_mapas_categorias(lista_categorias):
    """Construye mapas para búsqueda rápida de categorías por ID y por ID de padre."""
    mapa_por_id = {cat['id']: cat for cat in lista_categorias}
    mapa_por_id_padre = {}
    for cat in lista_categorias:
        id_padre = cat.get('parent') # Puede ser un ID numérico o null
        if id_padre is not None: # Solo si tiene un padre explícito (no es null)
            try:
                # El ID del padre ya debería ser un entero si no es null, según la API.
                # Pero por si acaso viniera como string numérico.
                id_padre_int = int(id_padre) 
            except (ValueError, TypeError):
                 # print(f"Advertencia: ID de padre no válido '{id_padre}' para categoría ID {cat.get('id')}")
                 continue # Saltar esta categoría si el ID del padre no es usable

            if id_padre_int not in mapa_por_id_padre:
                mapa_por_id_padre[id_padre_int] = []
            mapa_por_id_padre[id_padre_int].append(cat)
    return mapa_por_id, mapa_por_id_padre

def imprimir_y_contar_categorias(lista_todas_las_categorias):
    """Imprime y cuenta las categorías padre y sus subcategorías."""
    if not lista_todas_las_categorias:
        print("No hay categorías para mostrar o no se pudieron obtener.")
        return

    padres = [cat for cat in lista_todas_las_categorias if cat.get("parent") is None]
    mapa_por_id, mapa_por_id_padre = construir_mapas_categorias(lista_todas_las_categorias)

    print(f"\n--- Resumen de Categorías ---")
    print(f"Total de categorías padre: {len(padres)}")

    for i, cat_padre in enumerate(padres):
        # El nombre puede estar en múltiples idiomas, priorizamos 'es'
        nombre_padre = cat_padre.get("name", {}).get("es", cat_padre.get("name", {}).get("en", "Nombre no disponible"))
        id_padre = cat_padre.get("id")
        print(f"\n{i+1}. Categoría Padre: {nombre_padre} (ID: {id_padre})")
        
        hijas_directas = mapa_por_id_padre.get(id_padre, [])
        if hijas_directas:
            print(f"   Número de subcategorías directas: {len(hijas_directas)}")
            for j, sub_cat in enumerate(hijas_directas):
                nombre_sub = sub_cat.get("name", {}).get("es", sub_cat.get("name", {}).get("en", "Nombre no disponible"))
                id_sub = sub_cat.get("id")
                print(f"     {j+1}) Subcategoría: {nombre_sub} (ID: {id_sub})")
                
                nietas = mapa_por_id_padre.get(id_sub, [])
                if nietas:
                    print(f"        ¡ALERTA! Esta subcategoría tiene {len(nietas)} sub-subcategorías (nietas):")
                    for k, nieta_cat in enumerate(nietas):
                        nombre_nieta = nieta_cat.get("name", {}).get("es", nieta_cat.get("name", {}).get("en", "Nombre no disponible"))
                        id_nieta = nieta_cat.get("id")
                        print(f"           {k+1}* Nieta: {nombre_nieta} (ID: {id_nieta})")
        else:
            print("   No tiene subcategorías directas.")
    print("--- Fin del Resumen ---")

def eliminar_categoria_api(id_categoria):
    """Elimina una única categoría por su ID mediante una llamada a la API."""
    if not BASE_URL:
        print("Error: Las credenciales no han sido configuradas.")
        return False
    
    try:
        print(f"Intentando eliminar categoría ID: {id_categoria}...")
        response = requests.delete(f"{BASE_URL}/categories/{id_categoria}", headers=HEADERS)
        time.sleep(0.5) # Pausa para no saturar la API
        response.raise_for_status()
        print(f"Categoría ID: {id_categoria} eliminada exitosamente.")
        return True
    except requests.exceptions.RequestException as e:
        print(f"Error al eliminar categoría ID: {id_categoria}. Error: {e}")
        if response is not None:
            print(f"Respuesta del servidor ({response.status_code}): {response.text}")
        return False

def eliminar_rama_recursivamente(id_categoria_a_eliminar, mapa_por_id, mapa_por_id_padre):
    """
    Elimina recursivamente todas las subcategorías de una categoría dada, y luego la categoría misma.
    """
    hijas = mapa_por_id_padre.get(id_categoria_a_eliminar, [])
    
    for cat_hija in hijas:
        id_hija = cat_hija.get("id")
        nombre_hija = cat_hija.get("name", {}).get("es", "Desconocido")
        print(f"  Procesando para eliminar recursivamente subcategoría '{nombre_hija}' (ID: {id_hija}), hija de {id_categoria_a_eliminar}")
        eliminar_rama_recursivamente(id_hija, mapa_por_id, mapa_por_id_padre) 

    categoria_actual_data = mapa_por_id.get(id_categoria_a_eliminar, {})
    nombre_actual = categoria_actual_data.get("name", {}).get("es", "Desconocido")
    print(f"Eliminando categoría '{nombre_actual}' (ID: {id_categoria_a_eliminar}) después de sus hijas (si las tuvo).")
    eliminar_categoria_api(id_categoria_a_eliminar)

def eliminar_nietos_de_categoria_referencia(nombre_categoria_ref, lista_todas_las_categorias):
    """
    Para una categoría de referencia dada (por nombre), elimina todos los "nietos"
    (es decir, los hijos de sus hijos directos) y su descendencia.
    La categoría de referencia y sus hijos directos se conservan.
    """
    if not lista_todas_las_categorias:
        print("No hay categorías para procesar.")
        return

    mapa_por_id, mapa_por_id_padre = construir_mapas_categorias(lista_todas_las_categorias)
    
    id_categoria_referencia = None
    datos_categoria_referencia = None
    # Buscar la categoría de referencia por su nombre (puede ser padre o subcategoría)
    for id_cat, data_cat in mapa_por_id.items():
        nombre_cat_es = data_cat.get("name", {}).get("es", "").strip().lower()
        nombre_cat_en = data_cat.get("name", {}).get("en", "").strip().lower() # Considerar inglés también
        nombre_ref_lower = nombre_categoria_ref.strip().lower()
        if nombre_cat_es == nombre_ref_lower or nombre_cat_en == nombre_ref_lower :
            id_categoria_referencia = id_cat
            datos_categoria_referencia = data_cat
            break # Tomar la primera que coincida
    
    if not id_categoria_referencia:
        print(f"No se encontró la categoría de referencia '{nombre_categoria_ref}'. Verifica el nombre.")
        return

    nombre_real_ref = datos_categoria_referencia.get("name",{}).get("es", datos_categoria_referencia.get("name",{}).get("en","Desconocido"))
    print(f"Procesando para eliminar 'nietos' de la categoría de referencia: '{nombre_real_ref}' (ID: {id_categoria_referencia})")
    
    hijos_directos_de_ref = mapa_por_id_padre.get(id_categoria_referencia, [])
    if not hijos_directos_de_ref:
        print(f"La categoría '{nombre_real_ref}' no tiene subcategorías directas (hijos). No hay 'nietos' que eliminar.")
        return

    nietos_eliminados_contador = 0
    for hijo_directo in hijos_directos_de_ref: 
        id_hijo = hijo_directo.get("id")
        nombre_hijo = hijo_directo.get("name", {}).get("es", hijo_directo.get("name", {}).get("en", "Desconocido"))
        print(f"  Verificando hijo directo: '{nombre_hijo}' (ID: {id_hijo}) de '{nombre_real_ref}'")
        
        # Estos son los "nietos" de la categoría de referencia
        nietos_de_categoria_ref = mapa_por_id_padre.get(id_hijo, []) 
        if nietos_de_categoria_ref:
            print(f"    '{nombre_hijo}' tiene {len(nietos_de_categoria_ref)} subcategorías (nietos de '{nombre_real_ref}') para eliminar:")
            for nieta_cat in nietos_de_categoria_ref:
                id_nieta = nieta_cat.get("id")
                nombre_nieta = nieta_cat.get("name", {}).get("es", nieta_cat.get("name", {}).get("en", "Desconocido"))
                print(f"      Eliminando nieto: '{nombre_nieta}' (ID: {id_nieta}) y su posible descendencia...")
                eliminar_rama_recursivamente(id_nieta, mapa_por_id, mapa_por_id_padre)
                nietos_eliminados_contador +=1
        else:
            print(f"    '{nombre_hijo}' no tiene subcategorías (nietos de '{nombre_real_ref}').")
            
    if nietos_eliminados_contador > 0:
        print(f"\nSe procesaron para eliminación {nietos_eliminados_contador} categorías 'nietas' (y su posible descendencia) bajo '{nombre_real_ref}'.")
    else:
        print(f"\nNo se encontraron categorías 'nietas' para eliminar bajo '{nombre_real_ref}'.")
    print("Es recomendable recargar todas las categorías (opción 4 del menú) para ver el estado actualizado.")

def eliminar_categoria_por_nombre_y_sus_hijas(nombre_categoria_a_eliminar, lista_todas_las_categorias):
    """Elimina una categoría por su nombre y todas sus subcategorías."""
    if not lista_todas_las_categorias:
        print("No hay categorías para procesar.")
        return

    mapa_por_id, mapa_por_id_padre = construir_mapas_categorias(lista_todas_las_categorias)
    
    ids_categorias_a_eliminar = []
    # Buscar todas las categorías que coincidan con el nombre
    for id_cat, data_cat in mapa_por_id.items():
        nombre_cat_es = data_cat.get("name", {}).get("es", "").strip().lower()
        nombre_cat_en = data_cat.get("name", {}).get("en", "").strip().lower() # Considerar inglés también
        nombre_eliminar_lower = nombre_categoria_a_eliminar.strip().lower()
        if nombre_cat_es == nombre_eliminar_lower or nombre_cat_en == nombre_eliminar_lower:
            ids_categorias_a_eliminar.append(id_cat)
            
    if not ids_categorias_a_eliminar:
        print(f"No se encontró ninguna categoría con el nombre '{nombre_categoria_a_eliminar}'. Verifica el nombre.")
        return

    print(f"Se encontraron {len(ids_categorias_a_eliminar)} categorías con el nombre '{nombre_categoria_a_eliminar}'.")
    
    for id_cat_a_eliminar in ids_categorias_a_eliminar:
        if id_cat_a_eliminar in mapa_por_id: # Verificar si aún existe (podría haber sido eliminada como hija)
            data_cat_actual = mapa_por_id[id_cat_a_eliminar] 
            nombre_cat_actual = data_cat_actual.get("name", {}).get("es", data_cat_actual.get("name", {}).get("en", "Desconocido"))
            print(f"\nIniciando eliminación de la categoría '{nombre_cat_actual}' (ID: {id_cat_a_eliminar}) y todas sus subcategorías.")
            eliminar_rama_recursivamente(id_cat_a_eliminar, mapa_por_id, mapa_por_id_padre)
    
    print(f"\nProceso de eliminación para '{nombre_categoria_a_eliminar}' completado.")
    print("Es recomendable recargar todas las categorías (opción 4 del menú) para ver el estado actualizado.")


def main():
    """Función principal que ejecuta el menú interactivo."""
    global categorias_actuales # Para que se pueda modificar en configurar_credenciales si es necesario
    print("Herramienta de Gestión de Categorías de Tiendanube")
    print("================================================")
    
    # Intentar configurar credenciales al inicio. Si falla, el usuario puede reintentar desde el menú.
    if not configurar_credenciales():
        print("Advertencia: Configuración inicial de credenciales fallida o incompleta.")
        print("Puedes reintentar desde la opción 6 del menú.")


    categorias_actuales = None 

    while True:
        print("\nOpciones del Menú:")
        print("1. Listar y contar todas las categorías")
        print("2. Aplanar Jerarquía: Para una categoría de referencia, eliminar sus 'nietos' y su descendencia")
        print("3. Eliminar una categoría por nombre (y todas sus subcategorías)")
        print("4. Cargar/Recargar todas las categorías desde Tiendanube")
        print("5. Salir")
        print("6. Configurar/Actualizar Credenciales de API")
        
        opcion = input("Selecciona una opción: ").strip()
        
        if opcion == '1':
            if not categorias_actuales:
                print("Primero necesitas cargar las categorías (opción 4).")
                continue
            imprimir_y_contar_categorias(categorias_actuales)
        
        elif opcion == '2':
            if not categorias_actuales:
                print("Primero necesitas cargar las categorías (opción 4).")
                continue
            nombre_ref = input("Ingresa el nombre EXACTO de la categoría de referencia (ej: Invierno o Guantes). Se eliminarán los 'nietos' de esta categoría y su descendencia: ").strip()
            if not nombre_ref:
                print("El nombre de la categoría de referencia no puede estar vacío.")
                continue
            
            confirmacion = input(f"¿Estás SEGURO de que quieres eliminar TODAS las sub-subcategorías ('nietos') y su descendencia bajo los hijos directos de '{nombre_ref}'? Esta acción NO se puede deshacer. (escribe 'si' para confirmar): ").strip().lower()
            if confirmacion == 'si':
                eliminar_nietos_de_categoria_referencia(nombre_ref, categorias_actuales)
                categorias_actuales = None # Marcar como desactualizadas, requerir recarga
            else:
                print("Operación cancelada.")

        elif opcion == '3':
            if not categorias_actuales:
                print("Primero necesitas cargar las categorías (opción 4).")
                continue
            nombre_cat_a_eliminar = input("Ingresa el nombre EXACTO de la categoría que deseas eliminar (ej: Invierno). Se eliminarán también todas sus subcategorías: ").strip()
            if not nombre_cat_a_eliminar:
                print("El nombre de la categoría a eliminar no puede estar vacío.")
                continue

            confirmacion = input(f"¿Estás SEGURO de que quieres eliminar la categoría '{nombre_cat_a_eliminar}' y TODAS sus subcategorías? Esta acción NO se puede deshacer. (escribe 'si' para confirmar): ").strip().lower()
            if confirmacion == 'si':
                eliminar_categoria_por_nombre_y_sus_hijas(nombre_cat_a_eliminar, categorias_actuales)
                categorias_actuales = None # Marcar como desactualizadas
            else:
                print("Operación cancelada.")

        elif opcion == '4':
            if not HEADERS: # Chequeo básico si las credenciales están listas
                 print("Las credenciales no están configuradas. Por favor, configúralas primero (opción 6).")
                 continue
            print("Cargando/Recargando categorías...")
            categorias_actuales = obtener_todas_las_categorias()
            if categorias_actuales is not None: # Puede ser una lista vacía si no hay categorías
                print(f"Categorías cargadas/recargadas exitosamente. Total: {len(categorias_actuales)}")
            else:
                print("Fallo al cargar/recargar las categorías. Revisa los mensajes de error.")

        elif opcion == '5':
            print("Saliendo de la herramienta. ¡Hasta luego!")
            break
        
        elif opcion == '6':
            if configurar_credenciales():
                categorias_actuales = None # Forzar recarga de categorías si las credenciales cambian
                print("Credenciales actualizadas. Se recomienda recargar las categorías (opción 4).")
            else:
                print("La actualización de credenciales falló. Intenta de nuevo.")
            
        else:
            print("Opción no válida. Por favor, intenta de nuevo.")

if __name__ == "__main__":
    main()
