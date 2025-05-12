# JG-STORE

## Requisitos previos

1. Python 3.8 o superior instalado
2. Google Chrome instalado (para Selenium)
3. Git instalado (opcional, para clonar el repositorio)

## Instalación

1. Clona o descarga este repositorio en tu computadora

2. Abre una terminal o línea de comandos y navega hasta la carpeta del proyecto:

```bash
cd Proyecto/
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

1. Crea un archivo `.env` en la raíz del proyecto con las siguientes variables:

```env
ACCESS_TOKEN=tu_token_de_tiendanube
STORE_ID=tu_id_de_tienda
```

## Uso

Para ejecutar el script principal:

```bash
python ./scraping_coronel.py
```
