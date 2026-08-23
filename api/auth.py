"""Telegram orqali kirish va sessiya tokeni.

Ikki xil kirish yo'li qo'llab-quvvatlanadi — ikkalasi ham bir xil
foydalanuvchini beradi, ya'ni botdagi va saytdagi odam bitta hisobda:

  1. Telegram Login Widget  — oddiy brauzerdan (saytga kirish tugmasi)
  2. Telegram WebApp        — bot ichidagi mini-ilova (keyinchalik ilova uchun)

Parol yo'q, ro'yxatdan o'tish yo'q: shaxsni Telegram tasdiqlaydi, biz esa
imzoni tekshiramiz.
"""
import hashlib
import hmac
import json
import time
from base64 import urlsafe_b64encode, urlsafe_b64decode
from urllib.parse import parse_qsl

from bot.config import (
    BOT_TOKEN, API_SECRET, AUTH_TTL_SECONDS,
    TOKEN_TTL_SECONDS, ADMIN_TOKEN_TTL_SECONDS, ADMIN_IDS,
)


class AuthError(Exception):
    """Kirish ma'lumoti ishonchsiz yoki eskirgan."""


# --------------------------------------------------------------------------
# 1. Telegram Login Widget
# --------------------------------------------------------------------------

def verify_login_widget(data: dict) -> dict:
    """Telegram Login Widget qaytargan ma'lumotni tekshiradi.

    Telegram hamma maydonlarni "kalit=qiymat" ko'rinishida alifbo tartibida
    birlashtirib, SHA256(bot_token) kaliti bilan HMAC imzolaydi.
    """
    data = dict(data)
    received_hash = data.pop("hash", None)
    if not received_hash:
        raise AuthError("Imzo yo'q.")

    check_string = "\n".join(f"{k}={data[k]}" for k in sorted(data) if data[k] is not None)
    secret_key = hashlib.sha256(BOT_TOKEN.encode()).digest()
    expected = hmac.new(secret_key, check_string.encode(), hashlib.sha256).hexdigest()

    if not hmac.compare_digest(expected, received_hash):
        raise AuthError("Imzo to'g'ri kelmadi.")

    auth_date = int(data.get("auth_date", 0))
    if time.time() - auth_date > AUTH_TTL_SECONDS:
        raise AuthError("Kirish ma'lumoti eskirgan, qaytadan kiring.")

    return {
        "telegram_id": int(data["id"]),
        "username": data.get("username"),
        "full_name": " ".join(
            x for x in (data.get("first_name"), data.get("last_name")) if x
        ) or "Foydalanuvchi",
        "photo_url": data.get("photo_url"),
    }


# --------------------------------------------------------------------------
# 2. Telegram WebApp (mini-ilova)
# --------------------------------------------------------------------------

def verify_webapp_init_data(init_data: str) -> dict:
    """Bot ichidagi mini-ilova yuboradigan initData'ni tekshiradi.

    Bu yerda kalit boshqacha hisoblanadi: HMAC("WebAppData", bot_token).
    """
    pairs = dict(parse_qsl(init_data, keep_blank_values=True))
    received_hash = pairs.pop("hash", None)
    if not received_hash:
        raise AuthError("Imzo yo'q.")

    check_string = "\n".join(f"{k}={pairs[k]}" for k in sorted(pairs))
    secret_key = hmac.new(b"WebAppData", BOT_TOKEN.encode(), hashlib.sha256).digest()
    expected = hmac.new(secret_key, check_string.encode(), hashlib.sha256).hexdigest()

    if not hmac.compare_digest(expected, received_hash):
        raise AuthError("Imzo to'g'ri kelmadi.")

    auth_date = int(pairs.get("auth_date", 0))
    if time.time() - auth_date > AUTH_TTL_SECONDS:
        raise AuthError("Kirish ma'lumoti eskirgan, ilovani qayta oching.")

    try:
        user = json.loads(pairs["user"])
    except (KeyError, json.JSONDecodeError):
        raise AuthError("Foydalanuvchi ma'lumoti o'qilmadi.")

    return {
        "telegram_id": int(user["id"]),
        "username": user.get("username"),
        "full_name": " ".join(
            x for x in (user.get("first_name"), user.get("last_name")) if x
        ) or "Foydalanuvchi",
        "photo_url": user.get("photo_url"),
    }


# --------------------------------------------------------------------------
# 3. Sessiya tokeni
# --------------------------------------------------------------------------
# Qo'shimcha kutubxonasiz: JSON + HMAC imzo. Token ichida faqat telegram_id
# va muddat turadi, maxfiy narsa yo'q.

def _b64e(raw: bytes) -> str:
    return urlsafe_b64encode(raw).decode().rstrip("=")


def _b64d(text: str) -> bytes:
    return urlsafe_b64decode(text + "=" * (-len(text) % 4))


def issue_token(telegram_id: int) -> str:
    # Admin sessiyasi uzoqroq (144 soat), oddiy foydalanuvchi 72 soat.
    ttl = ADMIN_TOKEN_TTL_SECONDS if int(telegram_id) in ADMIN_IDS else TOKEN_TTL_SECONDS
    payload = {"sub": int(telegram_id), "exp": int(time.time()) + ttl}
    body = _b64e(json.dumps(payload, separators=(",", ":")).encode())
    sig = hmac.new(API_SECRET.encode(), body.encode(), hashlib.sha256).digest()
    return f"{body}.{_b64e(sig)}"


def read_token(token: str) -> int:
    """Tokendan telegram_id ni qaytaradi. Yaroqsiz bo'lsa AuthError."""
    try:
        body, sig = token.split(".", 1)
    except ValueError:
        raise AuthError("Token buzuq.")

    expected = hmac.new(API_SECRET.encode(), body.encode(), hashlib.sha256).digest()
    if not hmac.compare_digest(_b64e(expected), sig):
        raise AuthError("Token imzosi noto'g'ri.")

    try:
        payload = json.loads(_b64d(body))
    except (ValueError, json.JSONDecodeError):
        raise AuthError("Token o'qilmadi.")

    if payload.get("exp", 0) < time.time():
        raise AuthError("Sessiya muddati tugagan, qaytadan kiring.")

    return int(payload["sub"])
