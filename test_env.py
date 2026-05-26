"""
Script de prueba para verificar que las variables de entorno se cargan correctamente.
Ejecutar: python test_env.py
"""
import os
from pathlib import Path

print("=" * 60)
print("🔍 VERIFICACIÓN DE VARIABLES DE ENTORNO")
print("=" * 60)

# 1. Verificar si python-dotenv está instalado
print("\n1️⃣ Verificando python-dotenv...")
try:
    from dotenv import load_dotenv
    print("   ✅ python-dotenv está instalado")
except ImportError:
    print("   ❌ python-dotenv NO está instalado")
    print("   📦 Instálalo con: pip install python-dotenv")
    exit(1)

# 2. Buscar archivos .env
print("\n2️⃣ Buscando archivos de configuración...")
project_root = Path(__file__).parent
env_files = [
    project_root / "API_KEY.ENV",
    project_root / ".env",
    project_root / "api_key.env",
    project_root / "API_KEY.ENV.txt",
    project_root / "api_key.env.txt",
]

found_env = None
for env_file in env_files:
    if env_file.exists():
        print(f"   ✅ Encontrado: {env_file.name}")
        found_env = env_file
    else:
        print(f"   ⚪ No existe: {env_file.name}")

if not found_env:
    print("\n   ❌ No se encontró ningún archivo .env")
    print("   📝 Crea un archivo API_KEY.ENV con el contenido:")
    print("      OPENAI_API_KEY=sk-tu-api-key-aqui")
    exit(1)

# 3. Cargar variables
print(f"\n3️⃣ Cargando variables desde: {found_env.name}")
load_dotenv(found_env)

# 4. Verificar variables
print("\n4️⃣ Variables de entorno:")
print("-" * 40)

openai_key = os.getenv("OPENAI_API_KEY")
deepseek_key = os.getenv("DEEPSEEK_API_KEY")

if openai_key:
    # Mostrar solo los primeros y últimos 4 caracteres
    masked = f"{openai_key[:7]}...{openai_key[-4:]}" if len(openai_key) > 15 else "***"
    print(f"   OPENAI_API_KEY: {masked}")
    print(f"   ✅ Longitud: {len(openai_key)} caracteres")
else:
    print("   OPENAI_API_KEY: ❌ NO DEFINIDA")

if deepseek_key:
    masked = f"{deepseek_key[:7]}...{deepseek_key[-4:]}" if len(deepseek_key) > 15 else "***"
    print(f"   DEEPSEEK_API_KEY: {masked}")
else:
    print("   DEEPSEEK_API_KEY: ⚪ No definida (opcional)")

# 5. Prueba de conexión con OpenAI
print("\n5️⃣ Probando conexión con OpenAI...")
if openai_key and openai_key != "sk-TU_API_KEY_AQUI":
    try:
        from openai import OpenAI
        client = OpenAI(api_key=openai_key)
        
        # Hacer una llamada mínima de prueba
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": "Di solo: OK"}],
            max_tokens=5
        )
        print(f"   ✅ Conexión exitosa!")
        print(f"   📝 Respuesta: {response.choices[0].message.content}")
    except Exception as e:
        print(f"   ❌ Error de conexión: {str(e)[:80]}")
else:
    print("   ⚠️ API Key no configurada o es placeholder")

print("\n" + "=" * 60)
print("📋 RESUMEN:")
if openai_key and openai_key != "sk-TU_API_KEY_AQUI":
    print("   ✅ Todo listo para usar OpenAI GPT-4o-mini")
else:
    print("   ❌ Configura tu OPENAI_API_KEY en API_KEY.ENV")
    print("\n   Formato del archivo API_KEY.ENV:")
    print("   OPENAI_API_KEY=sk-proj-xxxxx...")
print("=" * 60)
