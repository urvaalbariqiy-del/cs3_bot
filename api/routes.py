"""Sayt va ilova uchun API endpointlari.

Muhim qoida: yopiq bo'lim mazmuni hech qachon javobga tushmaydi. Mehmon
signalning coin nomini ham, narxlarini ham ko'rmaydi — faqat "shuncha
material bor, obuna kerak" degan ma'lumot boradi.
"""
import secrets
from datetime import datetime

import httpx
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form

from bot import database as db
from bot import sections as sec
from bot.config import (
    ADMIN_IDS, BOT_TOKEN, BOT_USERNAME, TARIFF_NAMES, PERIOD_NAMES, TARIFF_LEVEL,
    FREE_MODE, LOGIN_TOKEN_TTL_SECONDS,
)
from api.auth import (
    verify_login_widget, verify_webapp_init_data, issue_token, AuthError,
)
from api.deps import optional_user, current_user, user_tariff

router = APIRouter(prefix="/api")

TELEGRAM_API = f"https://api.telegram.org/bot{BOT_TOKEN}"


# ==================== KIRISH ====================

@router.post("/auth/telegram")
async def auth_telegram(payload: dict):
    """Telegram Login Widget orqali kirish."""
    try:
        info = verify_login_widget(payload)
    except AuthError as e:
        raise HTTPException(status_code=401, detail=str(e))
    return await _login(info)


@router.post("/auth/start")
async def auth_start():
    """«Telegram orqali ulanish» bosilganda chaqiriladi.

    Bir martalik havola yaratadi. Foydalanuvchi shu havola bilan botni
    ochib /start bosadi — boshqa hech narsa qilmaydi.
    """
    if not BOT_USERNAME:
        raise HTTPException(
            status_code=503,
            detail="Bot nomi sozlanmagan (.env ichida BOT_USERNAME).",
        )
    token = secrets.token_urlsafe(24)
    await db.create_login_token(token)
    await db.cleanup_login_tokens(LOGIN_TOKEN_TTL_SECONDS * 12)
    return {
        "login_token": token,
        "bot_url": f"https://t.me/{BOT_USERNAME}?start={token}",
        "expires_in": LOGIN_TOKEN_TTL_SECONDS,
    }


@router.get("/auth/poll/{login_token}")
async def auth_poll(login_token: str):
    """Sayt shu manzilni so'rab turadi: /start bosildimi?

    Bosilgan bo'lsa sessiya tokenini beradi. Havola bir martalik.
    """
    telegram_id = await db.take_login_token(login_token, LOGIN_TOKEN_TTL_SECONDS)
    if telegram_id is None:
        return {"ready": False}

    row = await db.get_user_by_telegram_id(telegram_id)
    full_name = row["full_name"] if row else "Foydalanuvchi"
    username = row["username"] if row else None

    return {
        "ready": True,
        **await _login({
            "telegram_id": telegram_id,
            "username": username,
            "full_name": full_name,
        }),
    }


@router.post("/auth/webapp")
async def auth_webapp(payload: dict):
    """Bot ichidagi mini-ilova orqali kirish."""
    try:
        info = verify_webapp_init_data(payload.get("init_data", ""))
    except AuthError as e:
        raise HTTPException(status_code=401, detail=str(e))
    return await _login(info)


async def _login(info: dict):
    await db.get_or_create_user(info["telegram_id"], info["username"], info["full_name"])
    return {
        "token": issue_token(info["telegram_id"]),
        "user": {
            "telegram_id": info["telegram_id"],
            "username": info["username"],
            "full_name": info["full_name"],
            "photo_url": info.get("photo_url"),
            "is_admin": info["telegram_id"] in ADMIN_IDS,
        },
    }


# ==================== MEN ====================

@router.get("/me")
async def me(user=Depends(current_user)):
    sub = await db.get_active_subscription(user["id"])
    all_sections = await sec.all_sections()
    tariff = sub["tariff_code"] if sub else None

    subscription = None
    if sub:
        end = datetime.fromisoformat(sub["end_date"])
        left = end - datetime.utcnow()
        subscription = {
            "tariff": sub["tariff_code"],
            "tariff_name": TARIFF_NAMES.get(sub["tariff_code"], sub["tariff_code"]),
            "period": sub["period"],
            "ends_at": sub["end_date"],
            "days_left": max(left.days, 0),
            "status": sub["status"],
        }

    return {
        "user": {
            "telegram_id": user["telegram_id"],
            "username": user["username"],
            "full_name": user["full_name"],
            "is_admin": user["telegram_id"] in ADMIN_IDS,
        },
        # Har tashrifda sessiyani uzaytiramiz (rolling): yangi token beramiz.
        "token": issue_token(user["telegram_id"]),
        "subscription": subscription,
        "open_sections": [
            code for code, meta in all_sections.items()
            if sec.has_access(tariff, meta["min_tariff"])
        ],
    }


# ==================== BO'LIMLAR ====================

@router.get("/sections")
async def list_sections(user=Depends(optional_user)):
    tariff = await user_tariff(user)
    result = []
    for code, meta in (await sec.all_sections()).items():
        unlocked = sec.has_access(tariff, meta["min_tariff"])
        count = (len(await db.get_recent_signals(limit=1000, section=code))
                 if meta["kind"] == "signal"
                 else len(await db.get_content_by_type(code)))
        result.append({
            "code": code,
            "title": meta["title"],
            "kind": meta["kind"],
            "min_tariff": meta["min_tariff"],
            "min_tariff_name": TARIFF_NAMES.get(meta["min_tariff"], meta["min_tariff"]),
            "locked": not unlocked,
            "count": count,
        })
    return result


@router.get("/sections/{code}")
async def section_items(code: str, user=Depends(optional_user)):
    meta = await sec.by_code(code)
    if not meta:
        raise HTTPException(status_code=404, detail="Bunday bo'lim yo'q.")

    tariff = await user_tariff(user)
    is_signal = meta["kind"] == "signal"
    items = (await db.get_recent_signals(limit=50, section=code) if is_signal
             else await db.get_content_by_type(code))

    base = {
        "code": code,
        "title": meta["title"],
        "kind": meta["kind"],
        "min_tariff": meta["min_tariff"],
        "min_tariff_name": TARIFF_NAMES.get(meta["min_tariff"], meta["min_tariff"]),
        "count": len(items),
    }

    # Yopiq bo'lim: mazmun umuman yuborilmaydi.
    if not sec.has_access(tariff, meta["min_tariff"]):
        return {**base, "locked": True, "items": []}

    if is_signal:
        listed = [_signal_brief(s) for s in items]
    else:
        listed = [{"id": c["id"], "title": c["title"], "has_file": bool(c["file_id"]),
                   "created_at": c["created_at"]} for c in items]
    return {**base, "locked": False, "items": listed}


def _signal_brief(s) -> dict:
    return {
        "id": s["id"],
        "coin": s["coin"],
        "status": s["status"],
        "is_open": s["status"] not in ("tp2_hit", "stopped", "closed"),
        "created_at": s["created_at"],
    }


@router.get("/signals/{signal_id}")
async def signal_detail(signal_id: int, user=Depends(optional_user)):
    s = await db.get_signal(signal_id)
    if not s:
        raise HTTPException(status_code=404, detail="Signal topilmadi.")
    meta = await sec.by_code(s["section"]) or {"min_tariff": "lite"}
    if not sec.has_access(await user_tariff(user), meta["min_tariff"]):
        raise HTTPException(status_code=403, detail="Bu signal sizning tarifingizda ochilmagan.")
    return {
        **_signal_brief(s),
        "entry": s["entry"], "stop": s["stop"], "tp1": s["tp1"], "tp2": s["tp2"],
        "comment": s["comment"] or "",
        "section": s["section"],
        "activated_at": s["activated_at"],
        "closed_at": s["closed_at"],
    }


@router.get("/content/{content_id}")
async def content_detail(content_id: int, user=Depends(optional_user)):
    item = await db.get_content(content_id)
    if not item:
        raise HTTPException(status_code=404, detail="Material topilmadi.")
    meta = await sec.by_code(item["content_type"]) or {"min_tariff": item["required_tariff"]}
    if not sec.has_access(await user_tariff(user), meta["min_tariff"]):
        raise HTTPException(status_code=403, detail="Bu material sizning tarifingizda ochilmagan.")
    return {
        "id": item["id"], "title": item["title"], "caption": item["caption"] or "",
        "section": item["content_type"], "created_at": item["created_at"],
        # Fayl saytga to'g'ridan-to'g'ri berilmaydi: Telegram file_id faqat bot
        # orqali ochiladi. Sayt foydalanuvchini botga yo'naltiradi.
        "has_file": bool(item["file_id"]),
    }


# ==================== TARIF VA TO'LOV ====================

@router.get("/config")
async def public_config():
    """Sayt ishga tushganda o'qiydi: hozir qaysi rejimda ishlayapmiz."""
    return {
        "free_mode": FREE_MODE,
        "payments_enabled": not FREE_MODE,
        "bot_username": BOT_USERNAME,
    }


@router.get("/tariffs")
async def tariffs():
    rows = await db.get_all_prices()
    all_sections = await sec.all_sections()
    out = {}
    for r in rows:
        code = r["tariff_code"]
        out.setdefault(code, {
            "code": code,
            "name": TARIFF_NAMES.get(code, code),
            "level": TARIFF_LEVEL.get(code, 0),
            "sections": [m["title"] for m in all_sections.values()
                         if sec.has_access(code, m["min_tariff"])],
            "periods": [],
        })
        out[code]["periods"].append({
            "period": r["period"],
            "name": PERIOD_NAMES.get(r["period"], r["period"]),
            "price": r["price"],
            "currency": r["currency"],
        })

    result = sorted(out.values(), key=lambda t: t["level"])
    # Bepul rejimda tariflar ko'rsatiladi, lekin sotilmaydi - sayt ularni
    # "tez orada" deb chizadi.
    for t in result:
        t["coming_soon"] = FREE_MODE
    return result


@router.get("/payment-methods")
async def payment_methods():
    return [{"id": m["id"], "title": m["title"], "details": m["details"]}
            for m in await db.get_payment_methods()]


@router.post("/payments")
async def submit_payment(
    tariff: str = Form(...),
    period: str = Form(...),
    method_id: int | None = Form(default=None),
    receipt: UploadFile = File(...),
    user=Depends(current_user),
):
    """Saytdan to'lov chekini yuborish. Bot orqali yuborilgani bilan bir xil
    oqimga tushadi: admin tasdiqlaydi, obuna faollashadi."""
    if FREE_MODE:
        raise HTTPException(
            status_code=503,
            detail="Hozircha barcha bo'limlar bepul. Obuna tez orada ochiladi.",
        )
    if tariff not in TARIFF_NAMES or period not in PERIOD_NAMES:
        raise HTTPException(status_code=400, detail="Tarif yoki muddat noto'g'ri.")

    content = await receipt.read()
    if not content:
        raise HTTPException(status_code=400, detail="Chek fayli bo'sh.")
    if len(content) > 10 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="Fayl juda katta (10 MB gacha).")

    price_row = await db.get_price(tariff, period)
    method = await db.get_payment_method(method_id) if method_id else None

    caption = (
        f"🆕 <b>Yangi to'lov so'rovi (sayt orqali)</b>\n\n"
        f"👤 {user['full_name']} (@{user['username'] or '—'})\n"
        f"🆔 <code>{user['telegram_id']}</code>\n"
        f"📦 {TARIFF_NAMES[tariff]} — {PERIOD_NAMES[period]}"
    )
    if price_row:
        caption += f"\n💵 {price_row['price']:.0f} {price_row['currency']}"
    if method:
        caption += f"\n💳 Usul: {method['title']}"

    file_id = await _notify_admins_with_photo(content, receipt.filename or "chek.jpg", caption)
    payment_id = await db.create_payment(user["id"], tariff, period, file_id)

    return {"ok": True, "payment_id": payment_id,
            "message": "Chekingiz qabul qilindi. Admin tasdiqlagach obunangiz faollashadi."}


async def _notify_admins_with_photo(content: bytes, filename: str, caption: str) -> str | None:
    """Chekni adminlarga yuboradi va Telegram bergan file_id ni qaytaradi.

    Birinchi admin uchun fayl yuklanadi, qolganlariga o'sha file_id qayta
    ishlatiladi — shu bilan bir xil rasm ikki marta yuklanmaydi.
    """
    file_id = None
    async with httpx.AsyncClient(timeout=30) as client:
        for admin_id in ADMIN_IDS:
            try:
                if file_id is None:
                    resp = await client.post(
                        f"{TELEGRAM_API}/sendPhoto",
                        data={"chat_id": admin_id, "caption": caption, "parse_mode": "HTML"},
                        files={"photo": (filename, content)},
                    )
                else:
                    resp = await client.post(
                        f"{TELEGRAM_API}/sendPhoto",
                        data={"chat_id": admin_id, "photo": file_id,
                              "caption": caption, "parse_mode": "HTML"},
                    )
                data = resp.json()
                if data.get("ok") and file_id is None:
                    photos = data["result"].get("photo") or []
                    if photos:
                        file_id = photos[-1]["file_id"]
            except Exception:
                # Bitta admin qo'lga kirmasa ham to'lov yozib qo'yiladi
                pass
    return file_id
