"""So'rovdan foydalanuvchini aniqlash."""
from fastapi import Header, HTTPException

from bot import database as db
from api.auth import read_token, AuthError


async def _user_from_header(authorization: str | None):
    if not authorization or not authorization.lower().startswith("bearer "):
        return None
    try:
        telegram_id = read_token(authorization.split(" ", 1)[1].strip())
    except AuthError:
        return None
    row = await db.get_user_by_telegram_id(telegram_id)
    return dict(row) if row else None


async def optional_user(authorization: str | None = Header(default=None)):
    """Kirgan bo'lsa foydalanuvchi, kirmagan bo'lsa None.

    Ochiq sahifalar uchun: mehmon ham ko'ra oladi, lekin obunaga bog'liq
    qismlar yopiq bo'ladi.
    """
    return await _user_from_header(authorization)


async def current_user(authorization: str | None = Header(default=None)):
    """Majburiy kirish talab qiladigan endpointlar uchun."""
    user = await _user_from_header(authorization)
    if not user:
        raise HTTPException(status_code=401, detail="Avval Telegram orqali kiring.")
    return user


async def admin_user(authorization: str | None = Header(default=None)):
    from bot.config import ADMIN_IDS
    user = await _user_from_header(authorization)
    if not user or user["telegram_id"] not in ADMIN_IDS:
        raise HTTPException(status_code=403, detail="Bu bo'lim faqat admin uchun.")
    return user


async def user_tariff(user) -> str | None:
    """Foydalanuvchining hozirgi faol tarifi (yo'q bo'lsa None)."""
    if not user:
        return None
    sub = await db.get_active_subscription(user["id"])
    return sub["tariff_code"] if sub else None
