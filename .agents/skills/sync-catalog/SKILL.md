---
name: sync-catalog
description: Procedimiento paso a paso para ejecutar el scraping de Coronel Mayorista y sincronización de productos o stock hacia Tiendanube.
---

# Workflow: Sincronización del Catálogo JG-STORE

Este skill detalla el procedimiento para ejecutar, monitorear y diagnosticar las distintas fases de scraping y sincronización.

## 1. Verificación Inicial de Entorno
Antes de cualquier ejecución, validar que las credenciales y el acceso a OpenAI y Tiendanube estén listos:
```bash
python test_env.py
```

## 2. Opciones de Ejecución

### Opción A: Flujo Completo (Recomendado)
Ejecuta secuencialmente scraping de Coronel Mayorista, cálculo de dimensiones con IA, subida/actualización en Tiendanube y ajuste final de stock de productos discontinuados:
```bash
python -X utf8 main.py full-run --ganancia 40 --download-images t --no-prompt
```

### Opción B: Sincronización Rápida (Scrape + Sync sin desactivar stock)
```bash
python -X utf8 main.py scrape-sync --ganancia 40 --download-images t --no-prompt
```

### Opción C: Solo Actualización Rápida de Stock y Discontinuados
Verifica rápidamente qué productos están presentes en la tienda web del mayorista y desactiva o pone stock 0 en Tiendanube para los que ya no existen:
```bash
python -X utf8 main.py stock
```

## 3. Diagnóstico de Problemas Comunes

- **Error de Chrome WebDriver / Sesión caída**: Verificar que Google Chrome esté instalado y actualizado. El driver se gestiona centralizadamente en `app/core/browser.py`.
- **Rate Limit 429 en Tiendanube**: El cliente `app/services/tiendanube.py` maneja reintentos automáticos, pero si ocurre frecuentemente, verificar la caché en `app/api_cache/`.
- **Sin saldo en OpenAI**: El sistema usa fallback automático con medidas por defecto (0.05). Puedes ajustar o recargar el saldo en `openai_saldo.json`.
- **Actualizar Grafo de Conocimiento**: Si se añaden nuevos scripts o funciones:
```bash
python tools/generate_code_graph.py
```
