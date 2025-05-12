# JG-STORE Scraping

## Requisitos previos
1. Python 3.8 o superior instalado
2. Google Chrome instalado (para Selenium)
3. Git instalado (opcional, para clonar el repositorio)
4. SQLite viene incluido con Python, no requiere instalación adicional

## Base de datos
El proyecto utiliza SQLite como base de datos, que viene incluido con Python. La base de datos se creará automáticamente en la primera ejecución del script. No necesitas instalar nada adicional para SQLite.

## Instalación

1. Clona o descarga este repositorio en tu computadora

2. Abre una terminal o línea de comandos y navega hasta la carpeta del proyecto:
```bash
cd ruta/a/JG-STORE/Scraping
```

3. (Recomendado) Crea un entorno virtual:
```bash
# Windows
python -m venv venv
venv\Scripts\activate

# Linux/Mac
python3 -m venv venv
source venv/bin/activate
```

4. Instala las dependencias:
```bash
pip install -r requirements.txt
```

## Configuración
1. Crea un archivo `.env` en la carpeta Scraping con las siguientes variables:
```env
# Credenciales de Tiendanube
ACCESS_TOKEN=tu_token_de_tiendanube
STORE_ID=tu_id_de_tienda

# API Key de OpenAI (necesaria para el módulo deepseek)
OPENAI_API_KEY=tu_api_key_de_openai
```

## Uso
Para ejecutar el script principal:
```bash
python scraping_coronel.py
```

## Notas sobre SQLite
- La base de datos se crea automáticamente en el archivo `productos.db`
- No necesitas instalar ningún software adicional para SQLite
- Para ver el contenido de la base de datos, puedes usar herramientas como:
  - DB Browser for SQLite (interfaz gráfica)
  - SQLite command line tool (línea de comandos)
  Pero estas herramientas son opcionales, no son necesarias para que el script funcione.

## Notas sobre OpenAI
- El módulo deepseek utiliza la API de OpenAI para procesar información de productos
- Necesitas una API key válida de OpenAI (https://platform.openai.com/api-keys)
- La API key debe configurarse en el archivo .env como se muestra arriba
