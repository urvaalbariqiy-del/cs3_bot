"""
Ma'lumotlar bazasi qatlami.
SQLite (aiosqlite) ishlatiladi - alohida server kerak emas, bitta fayl yetarli.
"""
import aiosqlite
from datetime import datetime, timedelta
from bot.config import DB_PATH

SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    telegram_id INTEGER UNIQUE NOT NULL,
    username TEXT,
    full_name TEXT,
    is_blocked INTEGER DEFAULT 0,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS prices (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    tariff_code TEXT NOT NULL,        -- lite / pro / premium
    period TEXT NOT NULL,             -- daily / monthly
    price REAL NOT NULL,
    currency TEXT NOT NULL DEFAULT 'UZS',
    payment_info TEXT,                -- to'lov usuli tavsifi (karta raqami va h.k.)
    UNIQUE(tariff_code, period)
);

CREATE TABLE IF NOT EXISTS subscriptions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    tariff_code TEXT NOT NULL,
    period TEXT NOT NULL,
    start_date TEXT NOT NULL,
    end_date TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'active',   -- active / expired / paused
    reminder_sent INTEGER DEFAULT 0,
    created_at TEXT NOT NULL,
    FOREIGN KEY(user_id) REFERENCES users(id)
);

CREATE TABLE IF NOT EXISTS payments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    tariff_code TEXT NOT NULL,
    period TEXT NOT NULL,
    file_id TEXT,                     -- to'lov skrinshoti (Telegram file_id)
    status TEXT NOT NULL DEFAULT 'pending',  -- pending / approved / rejected
    created_at TEXT NOT NULL,
    reviewed_at TEXT,
    FOREIGN KEY(user_id) REFERENCES users(id)
);

CREATE TABLE IF NOT EXISTS signals (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    section TEXT NOT NULL DEFAULT 'signals',  -- signals / scalping
    photo_id TEXT,                    -- signalga biriktirilgan rasm (Telegram file_id)
    coin TEXT NOT NULL,               -- masalan BTCUSDT
    entry REAL NOT NULL,
    stop REAL NOT NULL,
    tp1 REAL NOT NULL,
    tp2 REAL NOT NULL,
    status TEXT NOT NULL DEFAULT 'pending',  -- pending/active/tp1_hit/tp2_hit/stopped/closed
    comment TEXT,
    -- narx entry'ga qaysi tomondan yaqinlashayotgani: 'above' (yuqoridan tushmoqda)
    -- yoki 'below' (pastdan ko'tarilmoqda). Birinchi narx tickida aniqlanadi.
    entry_side TEXT,
    created_at TEXT NOT NULL,
    activated_at TEXT,
    closed_at TEXT
);

CREATE TABLE IF NOT EXISTS content (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    content_type TEXT NOT NULL,       -- video / strategy
    title TEXT NOT NULL,
    file_id TEXT,
    caption TEXT,
    required_tariff TEXT NOT NULL,    -- lite/pro/premium - minimal talab qilinadigan daraja
    created_at TEXT NOT NULL
);

-- Sayt uchun erkin sozlamalar: mentorlik o'rinlari, to'lov hamyoni va h.k.
CREATE TABLE IF NOT EXISTS settings (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

-- Saytga "Telegram orqali ulanish" uchun bir martalik havolalar.
-- Sayt token yaratadi, foydalanuvchi botda /start <token> bosadi, bot
-- uning telegram_id sini shu qatorga yozadi va sayt kirgizadi.
CREATE TABLE IF NOT EXISTS login_tokens (
    token TEXT PRIMARY KEY,
    telegram_id INTEGER,              -- /start bosilgach to'ldiriladi
    created_at TEXT NOT NULL,
    used INTEGER NOT NULL DEFAULT 0   -- bir marta ishlatiladi
);

-- To'lov usullari: karta, Click, Payme va h.k. Foydalanuvchi to'lov
-- paytida shulardan birini tanlaydi.
CREATE TABLE IF NOT EXISTS payment_methods (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,              -- ro'yxatda ko'rinadigan nom, masalan "Humo — Kapitalbank"
    details TEXT NOT NULL,            -- karta raqami / rekvizitlar
    created_at TEXT NOT NULL
);

-- Admin /yangi_bolim orqali qo'shgan qo'shimcha bo'limlar.
-- Ularning kontenti 'content' jadvalida content_type = sections.code bilan saqlanadi.
CREATE TABLE IF NOT EXISTS sections (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    code TEXT UNIQUE NOT NULL,
    title TEXT NOT NULL,
    min_tariff TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS violations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    note TEXT,
    created_at TEXT NOT NULL,
    FOREIGN KEY(user_id) REFERENCES users(id)
);

-- Ommaviy "Kanal" (maqolalar) bo'limi: matn + bitta media (rasm/video/audio)
CREATE TABLE IF NOT EXISTS posts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    body TEXT,
    media TEXT,               -- yuklangan fayl nomi yoki http havola
    media_kind TEXT,          -- image / video / audio / '' (matnli)
    created_at TEXT NOT NULL
);

-- Maqolalarga izohlar. Faqat botga /start bosgan (kirgan) foydalanuvchi yozadi.
CREATE TABLE IF NOT EXISTS post_comments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    post_id INTEGER NOT NULL,
    telegram_id INTEGER NOT NULL,
    full_name TEXT,
    text TEXT NOT NULL,
    created_at TEXT NOT NULL,
    FOREIGN KEY(post_id) REFERENCES posts(id)
);

-- Yopiq "Jamoa" — bir martalik kalitlar. Admin yaratadi, obunachi kiritadi.
CREATE TABLE IF NOT EXISTS community_keys (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    code TEXT UNIQUE NOT NULL,
    label TEXT,                 -- kim uchun (ixtiyoriy izoh)
    used_by INTEGER,            -- telegram_id (ishlatilgan bo'lsa)
    used_at TEXT,
    created_at TEXT NOT NULL
);

-- Jamoa ichidagi yozishmalar (faqat a'zolar ko'radi/yozadi).
CREATE TABLE IF NOT EXISTS community_messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    telegram_id INTEGER NOT NULL,
    full_name TEXT,
    text TEXT NOT NULL,
    created_at TEXT NOT NULL
);
"""

DEFAULT_PRICES = [
    ("lite", "daily", 10000),
    ("lite", "monthly", 150000),
    ("pro", "daily", 20000),
    ("pro", "monthly", 300000),
    ("premium", "daily", 30000),
    ("premium", "monthly", 450000),
]


async def init_db():
    async with aiosqlite.connect(DB_PATH) as db:
        await db.executescript(SCHEMA)
        await db.commit()

        # Migratsiya: eski bazalarda yangi ustunlar bo'lmaydi, ularni qo'shamiz.
        # (CREATE TABLE IF NOT EXISTS mavjud jadvalni yangilamaydi)
        cur = await db.execute("PRAGMA table_info(signals)")
        columns = {row[1] for row in await cur.fetchall()}
        for name, ddl in (
            ("entry_side", "ALTER TABLE signals ADD COLUMN entry_side TEXT"),
            ("photo_id", "ALTER TABLE signals ADD COLUMN photo_id TEXT"),
            ("section", "ALTER TABLE signals ADD COLUMN section TEXT NOT NULL DEFAULT 'signals'"),
        ):
            if name not in columns:
                await db.execute(ddl)
        await db.commit()

        # Migratsiya: users.avatar (profil rasmi) va community_messages.media (rasm)
        cur = await db.execute("PRAGMA table_info(users)")
        ucols = {row[1] for row in await cur.fetchall()}
        if "avatar" not in ucols:
            await db.execute("ALTER TABLE users ADD COLUMN avatar TEXT")
        cur = await db.execute("PRAGMA table_info(community_messages)")
        ccols = {row[1] for row in await cur.fetchall()}
        if "media" not in ccols:
            await db.execute("ALTER TABLE community_messages ADD COLUMN media TEXT")
        await db.commit()

        # Migratsiya: ilgari to'lov usuli bitta bo'lib prices.payment_info'da turardi.
        # Uni yo'qotmaslik uchun birinchi to'lov usuli qilib ko'chirib olamiz.
        cur = await db.execute("SELECT COUNT(*) FROM payment_methods")
        (methods_count,) = await cur.fetchone()
        if methods_count == 0:
            cur = await db.execute(
                "SELECT payment_info FROM prices "
                "WHERE payment_info IS NOT NULL AND TRIM(payment_info) != '' LIMIT 1"
            )
            row = await cur.fetchone()
            if row:
                await db.execute(
                    "INSERT INTO payment_methods (title, details, created_at) VALUES (?, ?, ?)",
                    ("To'lov ma'lumoti", row[0], now_str()),
                )
                await db.commit()

        # narxlarni faqat birinchi ishga tushirishda to'ldiramiz (admin keyin o'zgartiradi)
        cur = await db.execute("SELECT COUNT(*) FROM prices")
        (count,) = await cur.fetchone()
        if count == 0:
            for tariff, period, price in DEFAULT_PRICES:
                await db.execute(
                    "INSERT INTO prices (tariff_code, period, price, currency) VALUES (?, ?, ?, 'UZS')",
                    (tariff, period, price),
                )
            await db.commit()


def now_str():
    return datetime.utcnow().isoformat()


# ---------- USERS ----------

async def get_or_create_user(telegram_id: int, username: str, full_name: str) -> int:
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute("SELECT id FROM users WHERE telegram_id=?", (telegram_id,))
        row = await cur.fetchone()
        if row:
            await db.execute(
                "UPDATE users SET username=?, full_name=? WHERE telegram_id=?",
                (username, full_name, telegram_id),
            )
            await db.commit()
            return row[0]
        cur = await db.execute(
            "INSERT INTO users (telegram_id, username, full_name, created_at) VALUES (?, ?, ?, ?)",
            (telegram_id, username, full_name, now_str()),
        )
        await db.commit()
        return cur.lastrowid


async def get_user_by_telegram_id(telegram_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute("SELECT * FROM users WHERE telegram_id=?", (telegram_id,))
        return await cur.fetchone()


async def get_telegram_id_by_user_id(user_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute("SELECT telegram_id FROM users WHERE id=?", (user_id,))
        row = await cur.fetchone()
        return row[0] if row else None


async def get_all_user_telegram_ids():
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute("SELECT telegram_id FROM users WHERE is_blocked=0")
        rows = await cur.fetchall()
        return [r[0] for r in rows]


# ---------- PRICES ----------

async def get_all_prices():
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute("SELECT * FROM prices ORDER BY tariff_code, period")
        return await cur.fetchall()


async def get_price(tariff_code: str, period: str):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute(
            "SELECT * FROM prices WHERE tariff_code=? AND period=?", (tariff_code, period)
        )
        return await cur.fetchone()


async def set_price(tariff_code: str, period: str, price: float, payment_info: str = None):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            """INSERT INTO prices (tariff_code, period, price, payment_info)
               VALUES (?, ?, ?, ?)
               ON CONFLICT(tariff_code, period)
               DO UPDATE SET price=excluded.price,
                             payment_info=COALESCE(excluded.payment_info, prices.payment_info)""",
            (tariff_code, period, price, payment_info),
        )
        await db.commit()


# ---------- SOZLAMALAR (kalit-qiymat) ----------

async def get_setting(key: str, default: str = None):
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute("SELECT value FROM settings WHERE key=?", (key,))
        row = await cur.fetchone()
        return row[0] if row else default


async def set_setting(key: str, value: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            """INSERT INTO settings (key, value, updated_at) VALUES (?, ?, ?)
               ON CONFLICT(key) DO UPDATE SET value=excluded.value,
                                              updated_at=excluded.updated_at""",
            (key, value, now_str()),
        )
        await db.commit()


# ---------- SAYTGA ULANISH (bir martalik havola) ----------

async def create_login_token(token: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT INTO login_tokens (token, created_at) VALUES (?, ?)",
            (token, now_str()),
        )
        await db.commit()


async def bind_login_token(token: str, telegram_id: int) -> bool:
    """Bot /start bosilganda chaqiradi. Token topilib, hali bog'lanmagan
    bo'lsa True qaytaradi."""
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute(
            "UPDATE login_tokens SET telegram_id=? WHERE token=? AND telegram_id IS NULL",
            (telegram_id, token),
        )
        await db.commit()
        return cur.rowcount > 0


async def take_login_token(token: str, max_age_seconds: int):
    """Sayt so'raydi: kimdir /start bosdimi? Bosgan bo'lsa telegram_id ni
    qaytaradi va tokenni ishlatilgan deb belgilaydi (bir martalik)."""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute(
            "SELECT * FROM login_tokens WHERE token=? AND used=0", (token,)
        )
        row = await cur.fetchone()
        if not row or row["telegram_id"] is None:
            return None

        age = (datetime.utcnow() - datetime.fromisoformat(row["created_at"])).total_seconds()
        if age > max_age_seconds:
            return None

        await db.execute("UPDATE login_tokens SET used=1 WHERE token=?", (token,))
        await db.commit()
        return row["telegram_id"]


async def cleanup_login_tokens(max_age_seconds: int):
    """Eskirgan havolalarni tozalaydi - jadval cheksiz o'smasligi uchun."""
    threshold = (datetime.utcnow() - timedelta(seconds=max_age_seconds)).isoformat()
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("DELETE FROM login_tokens WHERE created_at < ?", (threshold,))
        await db.commit()


# ---------- TO'LOV USULLARI ----------

async def add_payment_method(title: str, details: str) -> int:
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute(
            "INSERT INTO payment_methods (title, details, created_at) VALUES (?, ?, ?)",
            (title, details, now_str()),
        )
        await db.commit()
        return cur.lastrowid


async def get_payment_methods():
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute("SELECT * FROM payment_methods ORDER BY id")
        return await cur.fetchall()


async def get_payment_method(method_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute("SELECT * FROM payment_methods WHERE id=?", (method_id,))
        return await cur.fetchone()


async def delete_payment_method(method_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("DELETE FROM payment_methods WHERE id=?", (method_id,))
        await db.commit()


# ---------- SUBSCRIPTIONS ----------

async def get_active_subscription(user_id: int):
    """Foydalanuvchining hozirgi eng yuqori faol obunasini qaytaradi (agar bo'lsa)."""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute(
            """SELECT * FROM subscriptions
               WHERE user_id=? AND status='active' AND end_date > ?
               ORDER BY end_date DESC LIMIT 1""",
            (user_id, now_str()),
        )
        return await cur.fetchone()


async def create_or_extend_subscription(user_id: int, tariff_code: str, period: str):
    """To'lov tasdiqlangach chaqiriladi. Agar faol obuna bo'lsa, muddatini uzaytiradi."""
    days = 1 if period == "daily" else 30
    existing = await get_active_subscription(user_id)
    async with aiosqlite.connect(DB_PATH) as db:
        if existing and existing["tariff_code"] == tariff_code:
            new_end = datetime.fromisoformat(existing["end_date"]) + timedelta(days=days)
            await db.execute(
                "UPDATE subscriptions SET end_date=?, reminder_sent=0 WHERE id=?",
                (new_end.isoformat(), existing["id"]),
            )
        else:
            start = datetime.utcnow()
            end = start + timedelta(days=days)
            await db.execute(
                """INSERT INTO subscriptions
                   (user_id, tariff_code, period, start_date, end_date, status, created_at)
                   VALUES (?, ?, ?, ?, ?, 'active', ?)""",
                (user_id, tariff_code, period, start.isoformat(), end.isoformat(), now_str()),
            )
        await db.commit()


async def pause_subscription(user_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE subscriptions SET status='paused' WHERE user_id=? AND status='active'",
            (user_id,),
        )
        await db.commit()


async def get_expiring_subscriptions(hours_before: int):
    threshold = (datetime.utcnow() + timedelta(hours=hours_before)).isoformat()
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute(
            """SELECT s.*, u.telegram_id FROM subscriptions s
               JOIN users u ON u.id = s.user_id
               WHERE s.status='active' AND s.end_date <= ? AND s.end_date > ? AND s.reminder_sent=0""",
            (threshold, now_str()),
        )
        return await cur.fetchall()


async def mark_reminder_sent(subscription_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE subscriptions SET reminder_sent=1 WHERE id=?", (subscription_id,)
        )
        await db.commit()


async def get_newly_expired_subscriptions():
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute(
            """SELECT s.*, u.telegram_id FROM subscriptions s
               JOIN users u ON u.id = s.user_id
               WHERE s.status='active' AND s.end_date <= ?""",
            (now_str(),),
        )
        return await cur.fetchall()


async def expire_subscription(subscription_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE subscriptions SET status='expired' WHERE id=?", (subscription_id,)
        )
        await db.commit()


# ---------- PAYMENTS ----------

async def create_payment(user_id: int, tariff_code: str, period: str, file_id: str) -> int:
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute(
            """INSERT INTO payments (user_id, tariff_code, period, file_id, created_at)
               VALUES (?, ?, ?, ?, ?)""",
            (user_id, tariff_code, period, file_id, now_str()),
        )
        await db.commit()
        return cur.lastrowid


async def get_payment(payment_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute("SELECT * FROM payments WHERE id=?", (payment_id,))
        return await cur.fetchone()


async def update_payment_status(payment_id: int, status: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE payments SET status=?, reviewed_at=? WHERE id=?",
            (status, now_str(), payment_id),
        )
        await db.commit()


# ---------- SIGNALS ----------

async def create_signal(coin: str, entry: float, stop: float, tp1: float, tp2: float,
                        comment: str = "", section: str = "signals", photo_id: str = None):
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute(
            """INSERT INTO signals (section, photo_id, coin, entry, stop, tp1, tp2, comment, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (section, photo_id, coin.upper(), entry, stop, tp1, tp2, comment, now_str()),
        )
        await db.commit()
        return cur.lastrowid


async def get_signal(signal_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute("SELECT * FROM signals WHERE id=?", (signal_id,))
        return await cur.fetchone()


async def get_watchable_signals():
    """Hali yopilmagan (pending yoki active) barcha signallar - narx kuzatish uchun."""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute(
            "SELECT * FROM signals WHERE status IN ('pending','active','tp1_hit')"
        )
        return await cur.fetchall()


async def set_signal_entry_side(signal_id: int, side: str):
    """Narx entry darajasiga qaysi tomondan yaqinlashayotganini yozib qo'yadi
    ('above' — yuqoridan tushmoqda, 'below' — pastdan ko'tarilmoqda)."""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE signals SET entry_side=? WHERE id=? AND entry_side IS NULL",
            (side, signal_id),
        )
        await db.commit()


async def update_signal_status(signal_id: int, status: str):
    async with aiosqlite.connect(DB_PATH) as db:
        if status in ("tp2_hit", "stopped", "closed"):
            await db.execute(
                "UPDATE signals SET status=?, closed_at=? WHERE id=?",
                (status, now_str(), signal_id),
            )
        elif status == "active":
            await db.execute(
                "UPDATE signals SET status=?, activated_at=? WHERE id=?",
                (status, now_str(), signal_id),
            )
        else:
            await db.execute("UPDATE signals SET status=? WHERE id=?", (status, signal_id))
        await db.commit()


async def get_recent_signals(limit: int = 15, section: str = None):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        if section:
            cur = await db.execute(
                "SELECT * FROM signals WHERE section=? ORDER BY created_at DESC LIMIT ?",
                (section, limit),
            )
        else:
            cur = await db.execute(
                "SELECT * FROM signals ORDER BY created_at DESC LIMIT ?", (limit,)
            )
        return await cur.fetchall()


# ---------- CONTENT ----------

async def add_content(content_type: str, title: str, file_id: str, caption: str, required_tariff: str):
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute(
            """INSERT INTO content (content_type, title, file_id, caption, required_tariff, created_at)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (content_type, title, file_id, caption, required_tariff, now_str()),
        )
        await db.commit()
        return cur.lastrowid


async def get_content_by_type(content_type: str):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute(
            "SELECT * FROM content WHERE content_type=? ORDER BY created_at DESC",
            (content_type,),
        )
        return await cur.fetchall()


async def delete_content(content_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("DELETE FROM content WHERE id=?", (content_id,))
        await db.commit()


async def get_content(content_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute("SELECT * FROM content WHERE id=?", (content_id,))
        return await cur.fetchone()


# ---------- QO'SHIMCHA BO'LIMLAR ----------

async def add_section(code: str, title: str, min_tariff: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT INTO sections (code, title, min_tariff, created_at) VALUES (?, ?, ?, ?)",
            (code, title, min_tariff, now_str()),
        )
        await db.commit()


async def get_custom_sections():
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute("SELECT * FROM sections ORDER BY id")
        return await cur.fetchall()


async def section_code_exists(code: str) -> bool:
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute("SELECT 1 FROM sections WHERE code=?", (code,))
        return await cur.fetchone() is not None


# ---------- KIRISH HUQUQI BO'YICHA AJRATISH ----------

async def get_users_with_tariff():
    """Har bir bloklanmagan foydalanuvchi uchun (telegram_id, faol tarif kodi yoki None).

    Xabar yuborishda kimga to'liq ma'lumot, kimga faqat qisqa eslatma
    yuborishni shu ro'yxat asosida hal qilamiz.
    """
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute(
            """SELECT u.telegram_id,
                      (SELECT s.tariff_code FROM subscriptions s
                        WHERE s.user_id = u.id AND s.status='active' AND s.end_date > ?
                        ORDER BY s.end_date DESC LIMIT 1)
               FROM users u
               WHERE u.is_blocked = 0""",
            (now_str(),),
        )
        return await cur.fetchall()


# ---------- VIOLATIONS ----------

async def add_violation(user_id: int, note: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT INTO violations (user_id, note, created_at) VALUES (?, ?, ?)",
            (user_id, note, now_str()),
        )
        await db.commit()


# ---------- KANAL (POSTS) ----------

async def add_post(title: str, body: str, media: str = None, media_kind: str = "") -> int:
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute(
            "INSERT INTO posts (title, body, media, media_kind, created_at) "
            "VALUES (?, ?, ?, ?, ?)",
            (title, body, media, media_kind, now_str()),
        )
        await db.commit()
        return cur.lastrowid


async def get_posts(limit: int = 50):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute(
            "SELECT * FROM posts ORDER BY created_at DESC, id DESC LIMIT ?", (limit,)
        )
        return await cur.fetchall()


async def get_post(post_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute("SELECT * FROM posts WHERE id = ?", (post_id,))
        return await cur.fetchone()


async def delete_post(post_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("DELETE FROM post_comments WHERE post_id = ?", (post_id,))
        await db.execute("DELETE FROM posts WHERE id = ?", (post_id,))
        await db.commit()


async def add_comment(post_id: int, telegram_id: int, full_name: str, text: str) -> int:
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute(
            "INSERT INTO post_comments (post_id, telegram_id, full_name, text, created_at) "
            "VALUES (?, ?, ?, ?, ?)",
            (post_id, telegram_id, full_name, text, now_str()),
        )
        await db.commit()
        return cur.lastrowid


async def get_comments(post_id: int, limit: int = 200):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute(
            "SELECT * FROM post_comments WHERE post_id = ? ORDER BY created_at ASC, id ASC LIMIT ?",
            (post_id, limit),
        )
        return await cur.fetchall()


async def count_comments(post_id: int) -> int:
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute(
            "SELECT COUNT(*) FROM post_comments WHERE post_id = ?", (post_id,)
        )
        (n,) = await cur.fetchone()
        return n


# ---------- JAMOA (COMMUNITY) ----------

async def add_community_keys(codes, label: str = None):
    async with aiosqlite.connect(DB_PATH) as db:
        for code in codes:
            await db.execute(
                "INSERT OR IGNORE INTO community_keys (code, label, created_at) VALUES (?, ?, ?)",
                (code, label, now_str()),
            )
        await db.commit()


async def get_community_keys(limit: int = 300):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute(
            "SELECT * FROM community_keys ORDER BY (used_by IS NOT NULL), created_at DESC, id DESC LIMIT ?",
            (limit,),
        )
        return await cur.fetchall()


async def delete_community_key(key_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("DELETE FROM community_keys WHERE id = ?", (key_id,))
        await db.commit()


async def redeem_community_key(code: str, telegram_id: int) -> str:
    """Kalitni ishlatadi. Natija: 'ok' | 'not_found' | 'used'.

    Bir martalik: agar allaqachon ishlatilgan bo'lsa, boshqa hech kim
    ishlatolmaydi. Foydalanuvchi allaqachon a'zo bo'lsa ham 'ok'.
    """
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute(
            "SELECT id, used_by FROM community_keys WHERE code = ?", (code,)
        )
        row = await cur.fetchone()
        if not row:
            return "not_found"
        key_id, used_by = row[0], row[1]
        if used_by is not None:
            return "ok" if int(used_by) == int(telegram_id) else "used"
        # Atomar: faqat hali ishlatilmagan bo'lsa biriktiramiz.
        await db.execute(
            "UPDATE community_keys SET used_by = ?, used_at = ? WHERE id = ? AND used_by IS NULL",
            (int(telegram_id), now_str(), key_id),
        )
        await db.commit()
        return "ok"


async def is_community_member(telegram_id: int) -> bool:
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute(
            "SELECT 1 FROM community_keys WHERE used_by = ? LIMIT 1", (int(telegram_id),)
        )
        return await cur.fetchone() is not None


async def add_community_message(telegram_id: int, full_name: str, text: str, media: str = None) -> int:
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute(
            "INSERT INTO community_messages (telegram_id, full_name, text, media, created_at) "
            "VALUES (?, ?, ?, ?, ?)",
            (int(telegram_id), full_name, text, media, now_str()),
        )
        await db.commit()
        return cur.lastrowid


async def get_community_messages(limit: int = 200):
    """Xabarlar + yuboruvchining profil rasmi (avatar) birga."""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute(
            "SELECT m.*, u.avatar AS avatar FROM community_messages m "
            "LEFT JOIN users u ON u.telegram_id = m.telegram_id "
            "ORDER BY m.created_at ASC, m.id ASC LIMIT ?", (limit,)
        )
        return await cur.fetchall()


async def set_user_avatar(telegram_id: int, avatar: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE users SET avatar = ? WHERE telegram_id = ?", (avatar, int(telegram_id))
        )
        await db.commit()


async def delete_community_message(msg_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("DELETE FROM community_messages WHERE id = ?", (msg_id,))
        await db.commit()
