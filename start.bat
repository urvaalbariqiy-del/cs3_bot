@echo off
chcp 65001 >nul
setlocal enabledelayedexpansion
title Kripto Signal Bot
cd /d "%~dp0"

echo ==========================================
echo    KRIPTO SIGNAL BOT
echo ==========================================
echo.

REM ---------- 1. Python o'rnatilganmi? ----------
python --version >nul 2>&1
if errorlevel 1 (
    echo [XATO] Kompyuterda Python topilmadi.
    echo.
    echo Nima qilish kerak:
    echo   1. https://www.python.org/downloads/ saytiga kiring
    echo   2. Sariq "Download Python" tugmasini bosing
    echo   3. Faylni oching va o'rnatishni boshlang
    echo   4. MUHIM: "Add Python to PATH" katagiga belgi qo'ying!
    echo   5. O'rnatib bo'lgach, shu faylni qayta ikki marta bosing
    echo.
    pause
    exit /b 1
)

REM ---------- 2. Sozlamalar (birinchi marta) ----------
if not exist ".env" (
    echo Birinchi ishga tushirish. Ikkita ma'lumot kerak.
    echo.
    set /p "TOKEN=1. BotFather'dan olingan token: "
    echo.
    set /p "ADMINS=2. Admin Telegram ID raqami, vergul bilan: "
    echo.
    if "!TOKEN!"=="" (
        echo [XATO] Token bo'sh qoldi. Qaytadan urinib ko'ring.
        pause
        exit /b 1
    )
    >  ".env" echo BOT_TOKEN=!TOKEN!
    >> ".env" echo ADMIN_IDS=!ADMINS!
    >> ".env" echo DB_PATH=bot_database.db
    >> ".env" echo REMINDER_HOURS_BEFORE=24
    echo Sozlamalar saqlandi. Keyingi safar bu so'ralmaydi.
    echo.
)

REM ---------- 3. Kerakli dasturlar ----------
if not exist "venv\Scripts\python.exe" (
    echo Kerakli dasturlar o'rnatilmoqda, 1-2 daqiqa kuting...
    python -m venv venv
    if errorlevel 1 (
        echo [XATO] Muhit yaratilmadi.
        pause
        exit /b 1
    )
    venv\Scripts\python.exe -m pip install --quiet --upgrade pip
    venv\Scripts\python.exe -m pip install --quiet -r requirements.txt
    if errorlevel 1 (
        echo [XATO] Dasturlar o'rnatilmadi. Internetni tekshiring.
        pause
        exit /b 1
    )
    echo Tayyor.
    echo.
)

REM ---------- 4. Ishga tushirish ----------
echo Bot ishga tushmoqda...
echo To'xtatish uchun shu oynani yoping.
echo.
venv\Scripts\python.exe main.py

echo.
echo Bot to'xtadi.
pause
