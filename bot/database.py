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
    coin TEXT NOT NULL,               -- masalan BTCUSDT
    entry REAL NOT NULL,
    stop REAL NOT NULL,
    tp1 REAL NOT NULL,
    tp2 REAL NOT NULL,
    status TEXT NOT NULL DEFAULT 'pending',  -- pending/active/tp1_hit/tp2_hit/stopped/closed
    comment TEXT,
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

CREATE TABLE IF NOT EXISTS violations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    note TEXT,
    created_at TEXT NOT NULL,
    FOREIGN KEY(user_id) REFERENCES users(id)
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

async def create_signal(coin: str, entry: float, stop: float, tp1: float, tp2: float, comment: str = ""):
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute(
            """INSERT INTO signals (coin, entry, stop, tp1, tp2, comment, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (coin.upper(), entry, stop, tp1, tp2, comment, now_str()),
        )
        await db.commit()
        return cur.lastrowid


async def get_watchable_signals():
    """Hali yopilmagan (pending yoki active) barcha signallar - narx kuzatish uchun."""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute(
            "SELECT * FROM signals WHERE status IN ('pending','active','tp1_hit')"
        )
        return await cur.fetchall()


async def update_signal_status(signal_id: int, status: str):
    async with aiosqlite.connect(DB_PATH) as db:
        field = "activated_at" if status == "active" else None
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


async def get_recent_signals(limit: int = 15):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
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


# ---------- VIOLATIONS ----------

async def add_violation(user_id: int, note: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT INTO violations (user_id, note, created_at) VALUES (?, ?, ?)",
            (user_id, note, now_str()),
        )
        await db.commit()
