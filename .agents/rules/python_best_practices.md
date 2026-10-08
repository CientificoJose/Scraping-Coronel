# Reglas de Calidad y Mejores Prácticas para Scraping-Coronel

## Estándares de Código Python
1. **Tipado Estricto (Type Hints)**:
   - Al agregar o modificar funciones en `app/core` o `app/services`, incluir anotaciones de tipo (`typing.List`, `typing.Dict`, `typing.Optional`, etc.).
2. **Manejo de Errores y Excepciones**:
   - Evitar bloques `except:` vacíos. Capturar excepciones específicas (`requests.RequestException`, `sqlite3.Error`, etc.).
3. **Manejo de Conexiones a Base de Datos**:
   - Siempre usar `contextlib.closing` o manejadores de contexto (`with sqlite3.connect(...) as conn:`) para garantizar el cierre adecuado de conexiones SQLite.
4. **Resiliencia en Scraping**:
   - Preferir `WebDriverWait` con `EC.presence_of_element_located` o `EC.element_to_be_clickable` en lugar de `time.sleep()` arbitrarios.
5. **Codificación de Caracteres en Windows**:
   - En scripts ejecutables desde terminal Windows, asegurar compatibilidad UTF-8:
     ```python
     import sys
     try:
         sys.stdout.reconfigure(encoding='utf-8', errors='replace')
         sys.stderr.reconfigure(encoding='utf-8', errors='replace')
     except Exception:
         pass
     ```
6. **Mantenimiento del Grafo de Conocimiento**:
   - Al crear nuevos módulos o alterar la firma de funciones principales, ejecutar `python tools/generate_code_graph.py` para mantener sincronizado `docs/KNOWLEDGE_GRAPH.md` y `docs/code_graph.json`.
