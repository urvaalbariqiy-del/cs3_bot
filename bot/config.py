import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN", "")

ADMIN_IDS = {
    int(x.strip()) for x in os.getenv("ADMIN_IDS", "").split(",") if x.strip()
}

DB_PATH = os.getenv("DB_PATH", "bot_database.db")

REMINDER_HOURS_BEFORE = int(os.getenv("REMINDER_HOURS_BEFORE", "24"))

# Tarif darajalari. Yuqori daraja pastki darajalarning hamma bo'limini ochadi.
TARIFF_LEVEL = {
    "lite": 1,
    "pro": 2,
    "premium": 3,
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

# ---------------------------------------------------------------------------
# BO'LIMLAR
#
# Har bir bo'lim foydalanuvchidagi bitta asosiy tugma.
#   kind = "signal"   -> Entry/Stop/TP kiritiladi, bot narxni Binance'dan kuzatadi
#   kind = "content"  -> video/fayl/matn joylanadi
#
# Admin /yangi_bolim buyrug'i orqali bularning ustiga yangi bo'lim qo'sha oladi;
# ular bazadagi 'sections' jadvalida saqlanadi va kind="content" bo'ladi.
# ---------------------------------------------------------------------------
SECTIONS = {
    "signals": {
        "title": "📈 Savdo signallari",
        "min_tariff": "lite",
        "kind": "signal",
    },
    "scalping": {
        "title": "⚡️ Skalping",
        "min_tariff": "pro",
        "kind": "signal",
    },
    "videos": {
        "title": "🎓 Video darsliklar",
        "min_tariff": "pro",
        "kind": "content",
    },
    "strategies": {
        "title": "🧠 Strategiyalar",
        "min_tariff": "premium",
        "kind": "content",
    },
}

# Binance spot narx oqimi uchun bazaviy manzil
BINANCE_WS_BASE = "wss://stream.binance.com:9443/stream?streams="

# Fon jarayonlarining tekshirish intervali (soniyalarda)
SUBSCRIPTION_CHECK_INTERVAL = 60 * 30  # har 30 daqiqada
