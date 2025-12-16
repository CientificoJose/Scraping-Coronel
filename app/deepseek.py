from openai import OpenAI
import os
import math
import json
from typing import List, Dict
from datetime import datetime
import time
from contextlib import closing
import sqlite3
import requests


# Cargar variables de entorno
#load_dotenv(os.path.join(os.path.dirname(__file__), '..', 'API_KEY.ENV'))

# API Key de OpenAI - REEMPLAZA CON TU API KEY
api_key = os.getenv("OPENAI_API_KEY", "sk-TU_API_KEY_AQUI")

# Modelo más económico de OpenAI
MODEL_NAME = "gpt-4o-mini"  # $0.15/1M input, $0.60/1M output

# Configuración del cliente OpenAI
client = OpenAI(
    api_key=api_key
)


# Funciones auxiliares
EJEMPLO_JSON = """Devuelve SOLO un JSON válido con un array de objetos,(imporante nunca dejar en 0.00 ningun valor, el valor minimo es 0.05 en general) cada uno con:
- peso_kg (float, peso en kg)
- ancho_cm (float, ancho en cm)
- alto_cm (float, altura en cm)
- profundidad_cm (float, profundidad en cm)

Ejemplo de respuesta válida:
[{
    "peso_kg": 0.5,
    "ancho_cm": 15.0,
    "alto_cm": 10.0,
    "profundidad_cm": 5.0
}]"""

    
def obtener_dimensiones_lote(productos: List[Dict], categoria: str) -> List[Dict]:
    """
    Obtiene dimensiones y peso para un lote de productos usando OpenAI GPT-4o-mini
    
    Args:
        productos: Lista de diccionarios con datos de productos
        categoria: Categoría de los productos para el prompt
    
    Returns:
        Lista de diccionarios con las dimensiones y pesos estimados
    """
    # Configuración de reintentos
    max_retries = 5
    base_delay = 1  # segundos
    
    # Crear directorio de logs si no existe
    log_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'openai_logs')
    os.makedirs(log_dir, exist_ok=True)
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    
    # 1. Preparar el prompt
    lista_productos = "\n".join([p['descripcion'] for p in productos])
    prompt = f"""Como experto en logística y ecommerce, estima las dimensiones y peso para los siguientes productos:
    
    Lista de productos:
    {lista_productos}
    
    {EJEMPLO_JSON}"""

    # Guardar el prompt en un archivo
    prompt_file = os.path.join(log_dir, f'prompt_{timestamp}.txt')
    with open(prompt_file, 'w', encoding='utf-8') as f:
        f.write(prompt)

    # 2. Llamar a la API de OpenAI con reintentos
    last_error = None
    
    for attempt in range(max_retries):
        try:
            # Calcular delay exponencial
            delay = min(base_delay * (2 ** attempt), 60)  # Máximo 60 segundos
            if attempt > 0:
                print(f"Intento {attempt + 1}/{max_retries}, esperando {delay} segundos...")
                time.sleep(delay)
            
            # Llamar a la API
            response = client.chat.completions.create(
                model=MODEL_NAME,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3,
                max_tokens=4000,
                response_format={"type": "json_object"}
            )
            
            # 3. Procesar respuesta
            content = response.choices[0].message.content
            
            # Guardar respuesta
            content_file = os.path.join(log_dir, f'content_{timestamp}_attempt{attempt}.json')
            with open(content_file, 'w', encoding='utf-8') as f:
                json.dump({"content": content}, f, indent=2)
            
            # Limpiar y parsear JSON
            content = content.replace('```json', '').replace('```', '').strip()
            data = json.loads(content)
            
            # Manejar diferentes formatos de respuesta
            if isinstance(data, dict):
                if all(key in data for key in ['peso_kg', 'ancho_cm', 'alto_cm', 'profundidad_cm']):
                    return [data]
                
                for key in data:
                    if isinstance(data[key], list):
                        return data[key]
                
                if 'data' in data and isinstance(data['data'], list):
                    return data['data']
                
                if 'resultados' in data and isinstance(data['resultados'], list):
                    return data['resultados']
                
            if isinstance(data, list):
                return data
                
            print(f"Formato no soportado. Revisar archivo: {content_file}")
            return []
            
        except Exception as e:
            last_error = e
            print(f"Intento {attempt + 1} fallido: {str(e)}")
            
            # Guardar error en log
            error_file = os.path.join(log_dir, f'error_{timestamp}_attempt{attempt}.txt')
            with open(error_file, 'w', encoding='utf-8') as f:
                f.write(f"Error: {str(e)}\n\nPrompt:\n{prompt}")
    
    print(f"Error después de {max_retries} intentos: {str(last_error)}")
    return []


def actualizar_dimensiones_en_bd(productos: List[Dict], dimensiones: List[Dict], db_path: str):
    """
    Actualiza la base de datos con las dimensiones obtenidas
    
    Args:
        productos: Lista original de productos
        dimensiones: Lista de dimensiones obtenidas
        db_path: Ruta a la base de datos SQLite
    """
    try:
        with closing(sqlite3.connect(db_path)) as conn:
            cursor = conn.cursor()
            
            for producto, dim in zip(productos, dimensiones):
                cursor.execute("""
                    UPDATE productos SET
                        peso_kg = ?,
                        ancho_cm = ?,
                        alto_cm = ?,
                        profundidad_cm = ?
                    WHERE codigo = ?
                """, (
                    dim.get('peso_kg', ''),
                    dim.get('ancho_cm', ''),
                    dim.get('alto_cm', ''),
                    dim.get('profundidad_cm', ''),
                    producto['codigo']
                ))
            
            conn.commit()
            print(f"Actualizadas dimensiones para {len(dimensiones)} productos")
            
    except Exception as e:
        print(f"Error actualizando dimensiones en BD: {str(e)}")



def obtener_dimensiones_producto(todos_los_productos: List[Dict], categoria: str, db_path: str, batch_size: int = 20) -> List[Dict]:
    """
    Procesa todos los productos en lotes para obtener sus dimensiones
    con manejo mejorado de errores y reintentos individuales
    
    Args:
        todos_los_productos: Lista completa de productos
        categoria: Categoría de los productos  
        db_path: Ruta a la base de datos SQLite
        batch_size: Tamaño del lote (default 20)
        
    Returns:
        Lista de productos actualizada con las dimensiones
    """
    productos_exitosos = 0
    productos_fallidos = []
    
    for i in range(0, len(todos_los_productos), batch_size):
        batch = todos_los_productos[i:i + batch_size]
        lote_num = i//batch_size + 1
        total_lotes = math.ceil(len(todos_los_productos)/batch_size)
        #print(f"\nProcesando lote {lote_num} de {total_lotes} ({len(batch)} productos)")
        
        # Intento 1: Procesar el lote completo
        dimensiones = obtener_dimensiones_lote(batch, categoria)
        
        if len(dimensiones) == len(batch):
            # Éxito - actualizar todos los productos del lote
            for producto, dim in zip(batch, dimensiones):
                producto.update(dim)
            actualizar_dimensiones_en_bd(batch, dimensiones, db_path)
            productos_exitosos += len(batch)
            #print(f"✅ Lote {lote_num} completado ({len(batch)} productos)")
        else:
            # Fallo - procesar productos individualmente
            #print(f"⚠️  Fallo en lote {lote_num}, procesando productos individualmente...")
            
            for j, producto in enumerate(batch):
                try:
                    # Procesar producto individual con 2 reintentos
                    dim = obtener_dimensiones_lote([producto], categoria)
                    if dim and len(dim) == 1:
                        producto.update(dim[0])
                        actualizar_dimensiones_en_bd([producto], dim, db_path)
                        productos_exitosos += 1
                        #print(f"  ✅ Producto {j+1} procesado")
                    else:
                        productos_fallidos.append(producto['codigo'])
                        #print(f"  ❌ Producto {j+1} falló")
                except Exception as e:
                    productos_fallidos.append(producto['codigo'])
                    #print(f"  ❌ Producto {j+1} falló: {str(e)}")
                
                time.sleep(1)  # Pausa entre productos
        
        time.sleep(3)  # Pausa más larga entre lotes
    
    # Resumen final
    #print(f"\n📊 Resumen final:")
    #print(f"- Productos procesados exitosamente: {productos_exitosos}/{len(todos_los_productos)}")
    if productos_fallidos:
        print(f"- Productos fallidos: {len(productos_fallidos)}")
        #print(f"- Códigos de productos fallidos: {', '.join(productos_fallidos)}")
    
    return todos_los_productos