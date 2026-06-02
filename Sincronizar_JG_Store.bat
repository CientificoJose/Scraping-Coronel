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
echo.
echo Presione cualquier tecla para salir...
pause > nul
