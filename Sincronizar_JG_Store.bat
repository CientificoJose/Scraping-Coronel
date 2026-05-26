@echo off
chcp 65001 > nul
title Sincronizador JG-STORE - Coronel Mayorista
echo ============================================================
echo           INICIANDO SINCRONIZADOR DE TIENDA
echo ============================================================
echo.
python -X utf8 main.py
echo.
echo Presione cualquier tecla para salir...
pause > nul
