#!/usr/bin/env bash
# Mac va Linux uchun ishga tushirish fayli.
# Windows uchun start.bat faylidan foydalaning.
cd "$(dirname "$0")" || exit 1

echo "=========================================="
echo "   KRIPTO SIGNAL BOT"
echo "=========================================="
echo

# ---------- 1. Python o'rnatilganmi? ----------
if ! command -v python3 >/dev/null 2>&1; then
    echo "[XATO] Kompyuterda Python topilmadi."
    echo
    echo "Mac uchun : https://www.python.org/downloads/ dan yuklab o'rnating"
    echo "Linux uchun: sudo apt install python3 python3-venv"
    echo
    exit 1
fi

# ---------- 2. Sozlamalar (birinchi marta) ----------
if [ ! -f ".env" ]; then
    echo "Birinchi ishga tushirish. Ikkita ma'lumot kerak."
    echo
    printf "1) BotFather'dan olingan token: "
    read -r TOKEN
    echo
    printf "2) Admin Telegram ID raqami (vergul bilan): "
    read -r ADMINS
    echo

    if [ -z "$TOKEN" ]; then
        echo "[XATO] Token bo'sh qoldi. Qaytadan urinib ko'ring."
        exit 1
    fi

    {
        echo "BOT_TOKEN=$TOKEN"
        echo "ADMIN_IDS=$ADMINS"
        echo "DB_PATH=bot_database.db"
        echo "REMINDER_HOURS_BEFORE=24"
    } > .env
    chmod 600 .env
    echo "Sozlamalar saqlandi. Keyingi safar bu so'ralmaydi."
    echo
fi

# ---------- 3. Kerakli dasturlar ----------
if [ ! -x "venv/bin/python3" ]; then
    echo "Kerakli dasturlar o'rnatilmoqda, 1-2 daqiqa kuting..."
    python3 -m venv venv || { echo "[XATO] Muhit yaratilmadi."; exit 1; }
    venv/bin/python3 -m pip install --quiet --upgrade pip
    venv/bin/python3 -m pip install --quiet -r requirements.txt \
        || { echo "[XATO] Dasturlar o'rnatilmadi. Internetni tekshiring."; exit 1; }
    echo "Tayyor."
    echo
fi

# ---------- 4. Ishga tushirish ----------
echo "Bot ishga tushmoqda..."
echo "To'xtatish uchun Ctrl+C bosing yoki oynani yoping."
echo
exec venv/bin/python3 main.py
