@echo off
chcp 65001 > nul
title Sincronizador JG-STORE - Coronel Mayorista

rem Crear acceso directo con icono si no existe
if not exist "%~dp0Sincronizar_JG_Store.lnk" (
    powershell -ExecutionPolicy Bypass -File "%~dp0Crear_Acceso_Directo.ps1" > nul 2>&1
)
echo ============================================================
echo           INICIANDO SINCRONIZADOR DE TIENDA
echo ============================================================
echo.
python -X utf8 main.py
if errorlevel 1 (
    echo.
    echo ============================================================
    echo ⚠️  ATENCIÓN: El proceso terminó con un error o advertencia.
    echo 📁 Revisa el registro detallado en: logs\errores.log
    echo ============================================================
    echo.
)
echo.
echo Presione cualquier tecla para salir...
pause > nul
