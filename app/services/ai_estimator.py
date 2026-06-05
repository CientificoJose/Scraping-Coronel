from openai import OpenAI
import os
import math
import json
import time
import sys
from typing import List, Dict
from datetime import datetime
from colorama import Fore, Style
from config import OPENAI_API_KEY

# Asegurar soporte de caracteres especiales y emojis en la consola sin crashear
try:
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')
except Exception:
    pass

def guardar_saldo_openai(saldo: float):
    """
    Guarda el saldo restante de OpenAI en 'openai_saldo.json'.
    """
    saldo_file = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), 'openai_saldo.json')
    try:
        with open(saldo_file, 'w', encoding='utf-8') as f:
            json.dump({
                "saldo_usd": saldo,
                "last_updated": datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }, f, indent=4)
    except Exception as e:
        print(Fore.RED + f"⚠️ Error guardando saldo en openai_saldo.json: {e}" + Style.RESET_ALL)

def cargar_saldo_openai() -> float:
    """
    Carga el saldo restante de OpenAI.
    1. Intenta leer 'openai_saldo.json'.
    2. Si no existe, intenta leer la variable de entorno 'OPENAI_SALDO' o 'OPENAI_INITIAL_BALANCE'.
    3. Si tampoco existe, usa un valor inicial por defecto de 5.0 USD y crea el archivo.
    """
    saldo_file = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), 'openai_saldo.json')
    if os.path.exists(saldo_file):
        try:
            with open(saldo_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                return float(data.get('saldo_usd', 5.0))
        except Exception:
            pass
            
    # Si no existe el archivo, buscar en variables de entorno
    env_saldo = os.getenv("OPENAI_SALDO") or os.getenv("OPENAI_INITIAL_BALANCE")
    if env_saldo:
        try:
            saldo = float(env_saldo)
            guardar_saldo_openai(saldo)
            return saldo
        except ValueError:
            pass
            
    # Default
    default_saldo = 5.0
    guardar_saldo_openai(default_saldo)
    return default_saldo

# Configuración del cliente OpenAI
client = None
if OPENAI_API_KEY:
    try:
        client = OpenAI(api_key=OPENAI_API_KEY)
        saldo_inicial = cargar_saldo_openai()
        print(Fore.CYAN + f"ℹ️ Cliente OpenAI inicializado. Saldo estimado restante: ${saldo_inicial:.4f} USD." + Style.RESET_ALL)
        print(Fore.CYAN + f"   (Puedes ajustar tu saldo editando el archivo 'openai_saldo.json')" + Style.RESET_ALL)
    except Exception as e:
        print(Fore.RED + f"⚠️ Error inicializando cliente OpenAI: {e}" + Style.RESET_ALL)
else:
    print(Fore.YELLOW + "⚠️ OPENAI_API_KEY no encontrada en la configuración. Se usarán dimensiones por defecto." + Style.RESET_ALL)

MODEL_NAME = "gpt-4o-mini"

# Variables globales para control de costos de la sesión
TOTAL_SESSION_COST = 0.0
COST_WARNING_THRESHOLD = 0.01  # Límite en dólares para avisar del consumo/saldo bajo
has_warned_cost = False

# Fallback por defecto para dimensiones
DEFAULT_DIMENSIONS = {
    "peso_kg": 0.05,
    "ancho_cm": 0.05,
    "alto_cm": 0.05,
    "profundidad_cm": 0.05
}

EJEMPLO_JSON = """Devuelve SOLO un JSON válido con un array de objetos, (importante nunca dejar en 0.00 ningún valor, el valor mínimo es 0.05 en general) cada uno con:
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
    Obtiene dimensiones y peso para un lote de productos usando OpenAI GPT-4o-mini.
    Si no hay API key o la llamada falla, devuelve la lista de dimensiones por defecto.
    """
    if not client:
        return [DEFAULT_DIMENSIONS.copy() for _ in productos]

    max_retries = 5
    base_delay = 1
    
    log_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'openai_logs')
    try:
        os.makedirs(log_dir, exist_ok=True)
    except Exception:
        pass
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    
    lista_productos = "\n".join([p.get('descripcion', '') for p in productos])
    prompt = f"""Como experto en logística y ecommerce, estima las dimensiones y peso para los siguientes productos:
    
    Lista de productos:
    {lista_productos}
    
    {EJEMPLO_JSON}"""

    # Intentar guardar el prompt en un archivo
    try:
        prompt_file = os.path.join(log_dir, f'prompt_{timestamp}.txt')
        with open(prompt_file, 'w', encoding='utf-8') as f:
            f.write(prompt)
    except Exception:
        pass

    for attempt in range(max_retries):
        while True:  # Bucle interno para permitir reintentos en caliente de cuota
            try:
                delay = min(base_delay * (2 ** attempt), 60)
                if attempt > 0:
                    print(Fore.YELLOW + f"Intento {attempt + 1}/{max_retries} OpenAI, esperando {delay} segundos..." + Style.RESET_ALL)
                    time.sleep(delay)
                
                response = client.chat.completions.create(
                    model=MODEL_NAME,
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0.3,
                    max_tokens=4000,
                    response_format={"type": "json_object"}
                )
                
                # Calcular e informar costo acumulado del lote en la sesión
                if hasattr(response, 'usage') and response.usage:
                    prompt_t = response.usage.prompt_tokens
                    completion_t = response.usage.completion_tokens
                    cost = (prompt_t * 0.15 / 1e6) + (completion_t * 0.60 / 1e6)
                    
                    global TOTAL_SESSION_COST, has_warned_cost
                    TOTAL_SESSION_COST += cost
                    
                    # Decrementar y guardar saldo estimado
                    saldo_actual = cargar_saldo_openai()
                    nuevo_saldo = max(0.0, saldo_actual - cost)
                    guardar_saldo_openai(nuevo_saldo)
                    
                    # Aviso de consumo
                    if TOTAL_SESSION_COST >= COST_WARNING_THRESHOLD and not has_warned_cost:
                        print(Fore.YELLOW + "\n" + "="*70)
                        print(f"💡 [AVISO DE CONSUMO]: El gasto acumulado estimado de esta sesión")
                        print(f"   ha alcanzado ${TOTAL_SESSION_COST:.4f} USD. Recuerda verificar tu saldo.")
                        print("="*70 + Style.RESET_ALL)
                        has_warned_cost = True
                        
                    # Aviso de saldo bajo (cuando queda poco saldo, sea como 0.01$ o menos)
                    if nuevo_saldo <= COST_WARNING_THRESHOLD:
                        print(Fore.RED + "\n" + "="*70)
                        print(f"⚠️ [AVISO DE SALDO BAJO]: ¡Tu saldo estimado de OpenAI se está agotando!")
                        print(f"   Saldo restante estimado: ${nuevo_saldo:.4f} USD (Umbral de aviso: ${COST_WARNING_THRESHOLD:.2f} USD).")
                        print(f"   Por favor, recarga tu saldo para evitar interrupciones.")
                        print("="*70 + Style.RESET_ALL)
                
                content = response.choices[0].message.content
                
                # Guardar respuesta
                try:
                    content_file = os.path.join(log_dir, f'content_{timestamp}_attempt{attempt}.json')
                    with open(content_file, 'w', encoding='utf-8') as f:
                        json.dump({"content": content}, f, indent=2)
                except Exception:
                    pass
                
                content = content.replace('```json', '').replace('```', '').strip()
                data = json.loads(content)
                
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
                    
                print(Fore.RED + f"Formato de respuesta de OpenAI no soportado." + Style.RESET_ALL)
                return [DEFAULT_DIMENSIONS.copy() for _ in productos]
                
            except Exception as e:
                last_error = e
                err_str = str(e)
                print(Fore.RED + f"Intento {attempt + 1} de OpenAI fallido: {err_str}" + Style.RESET_ALL)
                
                # 1. Si es un error de territorio no soportado (ej. ejecutado desde Venezuela),
                # no reintentar (es un bloqueo permanente) y marcar los productos
                if "unsupported_country_region_territory" in err_str:
                    print(Fore.RED + "❌ Conexión a OpenAI prohibida: Territorio no soportado (Venezuela)." + Style.RESET_ALL)
                    for prod in productos:
                        prod['unsupported_region'] = True
                    return [DEFAULT_DIMENSIONS.copy() for _ in productos]
                    
                # 2. Si es un error de saldo agotado (insufficient_quota), pausar y pedir recarga
                if "insufficient_quota" in err_str:
                    print(Fore.RED + "\n" + "="*70)
                    print("⚠️ ERROR: Tu saldo de OpenAI se ha agotado (insufficient_quota).")
                    print("Para continuar con las dimensiones correctas, por favor recarga tu saldo en:")
                    print("https://platform.openai.com/settings/organization/billing")
                    print("="*70 + Style.RESET_ALL)
                    
                    import sys
                    resp = input(Fore.CYAN + "👉 Presiona ENTER para volver a intentar (después de recargar), o escribe 'salir' para cerrar: " + Style.RESET_ALL).strip().lower()
                    if resp == "salir":
                        print(Fore.YELLOW + "Saliendo del programa..." + Style.RESET_ALL)
                        sys.exit(0)
                        
                    # Volver a intentar este lote inmediatamente (re-inicia el while True sin avanzar attempt)
                    continue
                    
                # Guardar error en log para otros fallos, y romper el bucle interno para hacer backoff
                try:
                    error_file = os.path.join(log_dir, f'error_{timestamp}_attempt{attempt}.txt')
                    with open(error_file, 'w', encoding='utf-8') as f:
                        f.write(f"Error: {str(e)}\n\nPrompt:\n{prompt}")
                except Exception:
                    pass
                break
    
    print(Fore.RED + f"Error de OpenAI después de {max_retries} intentos: {str(last_error)}. Usando valores por defecto." + Style.RESET_ALL)
    return [DEFAULT_DIMENSIONS.copy() for _ in productos]

def actualizar_dimensiones_en_bd(productos: List[Dict], dimensiones: List[Dict], db_path: str):
    """
    Actualiza la base de datos con las dimensiones obtenidas (delegado a core.db)
    """
    try:
        from app.core.db import actualizar_dimensiones_en_bd as core_actualizar_dimensiones_en_bd
        return core_actualizar_dimensiones_en_bd(productos, dimensiones, db_path)
    except Exception as e:
        print(Fore.RED + f"Error actualizando dimensiones en base de datos: {e}" + Style.RESET_ALL)
        return False

def obtener_dimensiones_producto(todos_los_productos: List[Dict], categoria: str, db_path: str, batch_size: int = 20) -> List[Dict]:
    """
    Procesa todos los productos en lotes para obtener sus dimensiones
    con manejo mejorado de errores y reintentos individuales.
    """
    if not todos_los_productos:
        return []

    if not client:
        # Rápido fallback sin llamadas si no hay API key
        for prod in todos_los_productos:
            prod.update(DEFAULT_DIMENSIONS)
        # Intentar guardarlos con valores por defecto en la BD
        dimensiones_default = [DEFAULT_DIMENSIONS.copy() for _ in todos_los_productos]
        actualizar_dimensiones_en_bd(todos_los_productos, dimensiones_default, db_path)
        return todos_los_productos

    productos_exitosos = 0
    productos_fallidos = []
    
    for i in range(0, len(todos_los_productos), batch_size):
        batch = todos_los_productos[i:i + batch_size]
        lote_num = i // batch_size + 1
        total_lotes = math.ceil(len(todos_los_productos) / batch_size)
        
        # Intento 1: Procesar el lote completo
        dimensiones = obtener_dimensiones_lote(batch, categoria)
        
        if len(dimensiones) == len(batch):
            # Éxito - actualizar todos los productos del lote
            for producto, dim in zip(batch, dimensiones):
                # Validar campos, si faltan rellenar con default
                valid_dim = {}
                for key in ['peso_kg', 'ancho_cm', 'alto_cm', 'profundidad_cm']:
                    try:
                        valid_dim[key] = float(dim.get(key, DEFAULT_DIMENSIONS[key]))
                    except (ValueError, TypeError):
                        valid_dim[key] = DEFAULT_DIMENSIONS[key]
                producto.update(valid_dim)
            actualizar_dimensiones_en_bd(batch, [ {k: p[k] for k in DEFAULT_DIMENSIONS} for p in batch ], db_path)
            productos_exitosos += len(batch)
        else:
            # Fallo - procesar productos individualmente
            for j, producto in enumerate(batch):
                try:
                    dim = obtener_dimensiones_lote([producto], categoria)
                    if dim and len(dim) == 1:
                        valid_dim = {}
                        for key in ['peso_kg', 'ancho_cm', 'alto_cm', 'profundidad_cm']:
                            try:
                                valid_dim[key] = float(dim[0].get(key, DEFAULT_DIMENSIONS[key]))
                            except (ValueError, TypeError):
                                valid_dim[key] = DEFAULT_DIMENSIONS[key]
                        producto.update(valid_dim)
                        actualizar_dimensiones_en_bd([producto], [valid_dim], db_path)
                        productos_exitosos += 1
                    else:
                        producto.update(DEFAULT_DIMENSIONS)
                        actualizar_dimensiones_en_bd([producto], [DEFAULT_DIMENSIONS], db_path)
                        productos_fallidos.append(producto.get('codigo', 'desconocido'))
                except Exception as e:
                    producto.update(DEFAULT_DIMENSIONS)
                    actualizar_dimensiones_en_bd([producto], [DEFAULT_DIMENSIONS], db_path)
                    productos_fallidos.append(producto.get('codigo', 'desconocido'))
                
                time.sleep(1)
        
        time.sleep(2)
    
    if productos_fallidos:
        print(Fore.YELLOW + f"⚠️ Se usaron dimensiones por defecto para {len(productos_fallidos)} productos que fallaron al procesar." + Style.RESET_ALL)
    
    return todos_los_productos
