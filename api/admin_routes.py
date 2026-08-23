"""Veb admin panel uchun endpointlar.

XAVFSIZLIK — site4 dagi yondashuvdan farqi shu yerda:
oddiy "X-Admin-Id: 12345" sarlavhasi YETARLI EMAS. Telegram ID maxfiy
emas — uni bilgan har kim admin bo'lib qolardi.

Bu yerda har bir so'rov imzolangan sessiya tokeni bilan keladi. Token esa
faqat Telegram orqali haqiqiy kirishdan keyin beriladi, ya'ni:
  1. odam saytda "ulanish" bosadi
  2. o'z Telegram hisobida /start bosadi (buni faqat hisob egasi qila oladi)
  3. shundan keyingina token beriladi
  4. token ichidagi telegram_id ADMIN_IDS ro'yxatida bo'lsa - admin

ID ni bilish yetarli emas: o'sha hisobga kira olish kerak.
"""
from fastapi import APIRouter, Depends, HTTPException

from bot import database as db
from bot import sections as sec
from bot.config import ADMIN_IDS, TARIFF_NAMES, PERIOD_NAMES, MENTORLIK_TOTAL_SEATS
from api.deps import admin_user

router = APIRouter(prefix="/api/admin")


@router.get("/me")
async def who_am_i(admin=Depends(admin_user)):
    return {
        "telegram_id": admin["telegram_id"],
        "full_name": admin["full_name"],
        "is_admin": True,
    }


# ==================== SIGNALLAR ====================

@router.get("/signals")
async def list_signals(section: str | None = None, admin=Depends(admin_user)):
    rows = await db.get_recent_signals(limit=200, section=section)
    return [dict(r) for r in rows]


@router.post("/signals")
async def create_signal(payload: dict, admin=Depends(admin_user)):
    section = (payload.get("section") or "signals").strip()
    meta = await sec.by_code(section)
    if not meta or meta["kind"] != "signal":
        raise HTTPException(status_code=400, detail="Signal bo'limi topilmadi.")

    coin = (payload.get("coin") or "").strip().upper().replace("/", "").replace("-", "")
    if not coin.isalnum():
        raise HTTPException(status_code=400, detail="Coin nomi noto'g'ri. Masalan: BTCUSDT")

    try:
        entry = float(payload["entry"])
        stop = float(payload["stop"])
        tp1 = float(payload["tp1"])
        tp2 = float(payload["tp2"])
    except (KeyError, TypeError, ValueError):
        raise HTTPException(status_code=400, detail="Entry, Stop, TP1 va TP2 raqam bo'lishi kerak.")

    # Bot bilan bir xil qoida: spot/long signal
    if not (stop < entry < tp1 < tp2):
        raise HTTPException(
            status_code=400,
            detail="Tartib noto'g'ri. Stop < Entry < TP1 < TP2 bo'lishi kerak.",
        )

    signal_id = await db.create_signal(
        coin, entry, stop, tp1, tp2,
        (payload.get("comment") or "").strip(), section=section,
    )
    return {"ok": True, "id": signal_id}


@router.delete("/signals/{signal_id}")
async def close_signal(signal_id: int, admin=Depends(admin_user)):
    if not await db.get_signal(signal_id):
        raise HTTPException(status_code=404, detail="Signal topilmadi.")
    await db.update_signal_status(signal_id, "closed")
    return {"ok": True}


# ==================== KONTENT ====================

@router.get("/content/{section}")
async def list_content(section: str, admin=Depends(admin_user)):
    return [dict(r) for r in await db.get_content_by_type(section)]


@router.post("/content")
async def create_content(payload: dict, admin=Depends(admin_user)):
    section = (payload.get("section") or "").strip()
    meta = await sec.by_code(section)
    if not meta or meta["kind"] != "content":
        raise HTTPException(status_code=400, detail="Kontent bo'limi topilmadi.")

    title = (payload.get("title") or "").strip()
    if not title:
        raise HTTPException(status_code=400, detail="Sarlavha bo'sh bo'lmasin.")

    content_id = await db.add_content(
        section, title,
        (payload.get("file_id") or "").strip() or None,
        (payload.get("body") or "").strip(),
        meta["min_tariff"],
    )
    return {"ok": True, "id": content_id}


@router.delete("/content/{content_id}")
async def delete_content(content_id: int, admin=Depends(admin_user)):
    if not await db.get_content(content_id):
        raise HTTPException(status_code=404, detail="Material topilmadi.")
    await db.delete_content(content_id)
    return {"ok": True}


# ==================== BO'LIMLAR ====================

@router.get("/sections")
async def list_sections(admin=Depends(admin_user)):
    return [
        {"code": code, **meta, "custom": code not in ("signals", "scalping", "videos", "strategies")}
        for code, meta in (await sec.all_sections()).items()
    ]


@router.post("/sections")
async def create_section(payload: dict, admin=Depends(admin_user)):
    import time
    title = (payload.get("title") or "").strip()
    min_tariff = (payload.get("min_tariff") or "lite").strip()

    if not title:
        raise HTTPException(status_code=400, detail="Bo'lim nomi bo'sh bo'lmasin.")
    if min_tariff not in TARIFF_NAMES:
        raise HTTPException(status_code=400, detail="Tarif noto'g'ri.")
    if any(m["title"] == title for m in (await sec.all_sections()).values()):
        raise HTTPException(status_code=400, detail="Bunday nomli bo'lim allaqachon bor.")

    code = f"custom{int(time.time())}"
    await db.add_section(code, title, min_tariff)
    return {"ok": True, "code": code}


# ==================== MENTORLIK O'RINLARI ====================

@router.get("/seats")
async def get_seats(admin=Depends(admin_user)):
    taken = int(await db.get_setting("mentorlik_taken", "0") or 0)
    total = int(await db.get_setting("mentorlik_total", str(MENTORLIK_TOTAL_SEATS)) or MENTORLIK_TOTAL_SEATS)
    return {"total": total, "taken": taken, "remaining": max(0, total - taken)}


@router.post("/seats")
async def set_seats(payload: dict, admin=Depends(admin_user)):
    try:
        taken = int(payload.get("taken", 0))
        total = int(payload.get("total", await db.get_setting(
            "mentorlik_total", str(MENTORLIK_TOTAL_SEATS))))
    except (TypeError, ValueError):
        raise HTTPException(status_code=400, detail="O'rinlar soni raqam bo'lishi kerak.")

    if total < 1:
        raise HTTPException(status_code=400, detail="Jami o'rinlar 1 dan kam bo'lmasin.")
    if not 0 <= taken <= total:
        raise HTTPException(
            status_code=400,
            detail=f"Band o'rinlar 0 va {total} orasida bo'lishi kerak.",
        )

    await db.set_setting("mentorlik_taken", str(taken))
    await db.set_setting("mentorlik_total", str(total))
    return {"ok": True, "total": total, "taken": taken, "remaining": total - taken}


# ==================== TO'LOV HAMYONI ====================

@router.get("/wallet")
async def get_wallet(admin=Depends(admin_user)):
    return {
        "address": await db.get_setting("wallet_address", "") or "",
        "network": await db.get_setting("wallet_network", "TRC20") or "TRC20",
    }


@router.post("/wallet")
async def set_wallet(payload: dict, admin=Depends(admin_user)):
    address = (payload.get("address") or "").strip()
    network = (payload.get("network") or "TRC20").strip()
    if not address:
        raise HTTPException(status_code=400, detail="Hamyon manzili bo'sh bo'lmasin.")
    await db.set_setting("wallet_address", address)
    await db.set_setting("wallet_network", network)
    return {"ok": True}


# ==================== FOYDALANUVCHILAR ====================

@router.get("/users")
async def list_users(admin=Depends(admin_user)):
    """Ro'yxatdan o'tganlar va ularning holati.

    Birinchi bosqichda asosiy o'lchov shu: nechta odam yig'ildi.
    """
    rows = await db.get_users_with_tariff()
    return {
        "total": len(rows),
        "with_subscription": sum(1 for _, t in rows if t),
        "users": [{"telegram_id": tid, "tariff": t} for tid, t in rows],
    }


@router.post("/subscriptions")
async def grant_subscription(payload: dict, admin=Depends(admin_user)):
    """Qo'lda obuna berish — to'lov tashqarida bo'lganda kerak bo'ladi."""
    try:
        telegram_id = int(payload["telegram_id"])
    except (KeyError, TypeError, ValueError):
        raise HTTPException(status_code=400, detail="Telegram ID raqam bo'lishi kerak.")

    tariff = (payload.get("tariff") or "").strip()
    period = (payload.get("period") or "monthly").strip()
    if tariff not in TARIFF_NAMES or period not in PERIOD_NAMES:
        raise HTTPException(status_code=400, detail="Tarif yoki muddat noto'g'ri.")

    user = await db.get_user_by_telegram_id(telegram_id)
    if not user:
        raise HTTPException(
            status_code=404,
            detail="Bunday foydalanuvchi yo'q — u avval saytga ulanishi kerak.",
        )

    await db.create_or_extend_subscription(user["id"], tariff, period)
    return {"ok": True}
