@echo off
title BloomCraft Florals - Flower Shop Management System
echo ======================================================================
echo    🌸 Starting BloomCraft Flower Shop Management System...
echo ======================================================================
echo.

if exist "C:\Users\Vamsi\AppData\Local\Programs\Thonny\python.exe" (
    "C:\Users\Vamsi\AppData\Local\Programs\Thonny\python.exe" app.py
    goto end
)

where python >nul 2>nul
if %errorlevel% equ 0 (
    python app.py
    goto end
)

echo [ERROR] Python not found. Please install Python or verify Thonny installation.
pause

:end
