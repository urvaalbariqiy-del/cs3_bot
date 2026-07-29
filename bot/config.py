import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN", "")

ADMIN_IDS = {
    int(x.strip()) for x in os.getenv("ADMIN_IDS", "").split(",") if x.strip()
}

DB_PATH = os.getenv("DB_PATH", "bot_database.db")

REMINDER_HOURS_BEFORE = int(os.getenv("REMINDER_HOURS_BEFORE", "24"))

# Tariflarning ichki kodlari va ular kirish huquqiga ega bo'limlar
TARIFF_ACCESS = {
    "lite": {"signals": True, "videos": False, "strategies": False},
    "pro": {"signals": True, "videos": True, "strategies": False},
    "premium": {"signals": True, "videos": True, "strategies": True},
}

TARIFF_NAMES = {
    "lite": "Lite",
    "pro": "Pro",
    "premium": "Premium",
}

PERIOD_NAMES = {
    "daily": "Kunlik",
    "monthly": "Oylik",
}

# Binance spot narx oqimi uchun bazaviy manzil
BINANCE_WS_BASE = "wss://stream.binance.com:9443/stream?streams="

# Fon jarayonlarining tekshirish intervali (soniyalarda)
SUBSCRIPTION_CHECK_INTERVAL = 60 * 30  # har 30 daqiqada
