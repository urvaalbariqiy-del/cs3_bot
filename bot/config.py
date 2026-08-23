import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN", "")

ADMIN_IDS = {
    int(x.strip()) for x in os.getenv("ADMIN_IDS", "").split(",") if x.strip()
}

DB_PATH = os.getenv("DB_PATH", "bot_database.db")

# Yuklangan fayllar (video darslar, signal rasmlari) shu papkada saqlanadi.
# Standart: baza yonidagi 'uploads' papka (Railway'da /data/uploads — disk saqlanadi).
MEDIA_DIR = os.getenv(
    "MEDIA_DIR",
    os.path.join(os.path.dirname(os.path.abspath(DB_PATH)) or ".", "uploads"),
)

# Yuklanadigan bitta faylning maksimal hajmi (baytlarda). Standart: 200 MB.
MAX_UPLOAD_BYTES = int(os.getenv("MAX_UPLOAD_MB", "200")) * 1024 * 1024

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
    "reminders": {
        "title": "🕌 Eslatmalar",
        "min_tariff": "lite",
        "kind": "content",
    },
}

# Mentorlik dasturi: jami o'rinlar soni (bandlari bazadagi settings'da).
MENTORLIK_TOTAL_SEATS = int(os.getenv("MENTORLIK_TOTAL_SEATS", "40"))

# ---------------------------------------------------------------------------
# BEPUL REJIM
# ---------------------------------------------------------------------------
# Birinchi bosqichda maqsad - odam yig'ish, pul emas. Shuning uchun barcha
# bo'limlar hammaga ochiq, to'lov qabul qilinmaydi, tariflar esa saytda
# "tez orada" deb ko'rsatiladi.
#
# Obunani yoqish uchun .env'ga FREE_MODE=false yozish kifoya - obuna, to'lov
# va tarif nazorati kodda saqlanib turibdi, qaytadan yozish kerak emas.
FREE_MODE = os.getenv("FREE_MODE", "true").strip().lower() in ("1", "true", "yes", "ha")

# ---------------------------------------------------------------------------
# API / SAYT
# ---------------------------------------------------------------------------
# Saytdan "Telegram orqali ulanish" bosilganda foydalanuvchi shu botga
# yo'naltiriladi va /start bosadi (@ belgisisiz).
BOT_USERNAME = os.getenv("BOT_USERNAME", "").lstrip("@")

# Saytga kirish havolasi shuncha soniyadan keyin kuchini yo'qotadi.
LOGIN_TOKEN_TTL_SECONDS = int(os.getenv("LOGIN_TOKEN_TTL_SECONDS", "300"))

# Sessiya tokenlarini imzolash uchun maxfiy kalit. Ishlab chiqarishda .env'ga
# uzun tasodifiy qiymat yozing - o'zgartirilsa hamma sessiya bekor bo'ladi.
API_SECRET = os.getenv("API_SECRET", "") or (BOT_TOKEN + "-cs3-api")

# Saytga qaysi manzillardan murojaat qilinishi mumkin (CORS).
# Vergul bilan: https://cryptospot3.uz,https://www.cryptospot3.uz
CORS_ORIGINS = [x.strip() for x in os.getenv("CORS_ORIGINS", "*").split(",") if x.strip()]

# Telegram bergan kirish ma'lumoti shuncha soniyadan keyin eskiradi.
AUTH_TTL_SECONDS = int(os.getenv("AUTH_TTL_SECONDS", str(24 * 3600)))

# Saytdagi sessiya shuncha soniya amal qiladi.
# Oddiy foydalanuvchi: 72 soat. Muddat tugagach qaytadan Telegram orqali kiradi.
TOKEN_TTL_SECONDS = int(os.getenv("TOKEN_TTL_SECONDS", str(72 * 3600)))

# Admin sessiyasi uzoqroq: 144 soat.
ADMIN_TOKEN_TTL_SECONDS = int(os.getenv("ADMIN_TOKEN_TTL_SECONDS", str(144 * 3600)))

# Binance spot narx oqimi uchun bazaviy manzil
BINANCE_WS_BASE = "wss://stream.binance.com:9443/stream?streams="

# Fon jarayonlarining tekshirish intervali (soniyalarda)
SUBSCRIPTION_CHECK_INTERVAL = 60 * 30  # har 30 daqiqada
