import os
import sqlite3
from colorama import Fore
from .scraping_product import inicializar_bd

def limpiar_codigos_sqlite():
    try:
        conn = inicializar_bd(excel_path='productos_coronel')
        if conn is None:  # Verificación explícita
            print(Fore.RED + "\n✖ No se pudo conectar a la base de datos" + Fore.RESET)
            return False
            
        cursor = conn.cursor()
        
        # 2. Crear tabla temporal si no existe
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS productos_limpios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            codigo_original TEXT,
            codigo_limpio TEXT
        )
        """)
        
        # 3. Obtener datos de la tabla original (ajusta el nombre según tu esquema)
        cursor.execute("SELECT id, codigo FROM productos")  # Cambia 'codigo' por tu columna
        productos = cursor.fetchall()
        
        # 4. Procesar y limpiar los códigos
        modificados = 0
        for producto in productos:
            id_prod, codigo = producto
            if codigo and ' ' in codigo:
                codigo_limpio = codigo.replace(' ', '')
                cursor.execute(
                    "INSERT INTO productos_limpios (codigo_original, codigo_limpio) VALUES (?, ?)",
                    (codigo, codigo_limpio)
                )
                modificados += 1
        
        # 5. Confirmar cambios
        conn.commit()
        print(Fore.GREEN + f"\n✔ Procesados {modificados} códigos" + Fore.RESET)
        return True
        
    except Exception as e:
        print(Fore.RED + f"\n✖ Error en SQLite: {str(e)}" + Fore.RESET)
        return False
    finally:
        if conn is not None:  # Solo cerrar si existe
            conn.close()