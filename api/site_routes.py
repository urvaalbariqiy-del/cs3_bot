"""Sayt sahifalari to'g'ridan-to'g'ri chaqiradigan ochiq endpointlar.

Sahifalar (signal.html, video-darslar.html, eslatmalar.html, kurs.html)
oldindan yozilgan va ma'lum javob shaklini kutadi. Shu shaklni saqlaymiz,
lekin ma'lumot bizning yagona bazamizdan keladi.

Bepul rejimda hamma narsa ochiq. FREE_MODE o'chirilsa, yopiq bo'lim
mazmuni bu yerdan ham chiqmaydi - tekshiruv bitta joyda (sections.has_access).
"""
from fastapi import APIRouter, Depends

from bot import database as db
from bot import sections as sec
from bot.config import MENTORLIK_TOTAL_SEATS
from api.deps import optional_user, user_tariff

router = APIRouter(prefix="/api")

STATUS_LABELS = {
    "pending": "Kutilmoqda",
    "active": "Faol",
    "tp1_hit": "TP1 olindi",
    "tp2_hit": "TP2 olindi — yopiq",
    "stopped": "Stop — yopiq",
    "closed": "Yopiq",
}
OPEN_STATUSES = ("pending", "active", "tp1_hit")


async def _can_see(section_code: str, user) -> bool:
    meta = await sec.by_code(section_code)
    if not meta:
        return False
    return sec.has_access(await user_tariff(user), meta["min_tariff"])


@router.get("/signals")
async def public_signals(user=Depends(optional_user)):
    """signal.html uchun. Bizning signal narx bo'yicha jonli kuzatiladi,
    shuning uchun holat (status) ham qo'shib beriladi."""
    if not await _can_see("signals", user):
        return {"signals": [], "locked": True}

    rows = await db.get_recent_signals(limit=50, section="signals")
    return {
        "locked": False,
        "signals": [{
            "id": s["id"],
            "symbol": s["coin"],
            "direction": "LONG",          # hozircha faqat spot/long
            "entry": _fmt(s["entry"]),
            "tp": f"{_fmt(s['tp1'])} / {_fmt(s['tp2'])}",
            "sl": _fmt(s["stop"]),
            "note": s["comment"] or "",
            "status": s["status"],
            "status_label": STATUS_LABELS.get(s["status"], s["status"]),
            "active": 1 if s["status"] in OPEN_STATUSES else 0,
            "created_at": s["created_at"],
        } for s in rows],
    }


@router.get("/scalping-signals")
async def public_scalping(user=Depends(optional_user)):
    if not await _can_see("scalping", user):
        return {"signals": [], "locked": True}
    rows = await db.get_recent_signals(limit=50, section="scalping")
    return {
        "locked": False,
        "signals": [{
            "id": s["id"], "symbol": s["coin"], "direction": "LONG",
            "entry": _fmt(s["entry"]), "tp": f"{_fmt(s['tp1'])} / {_fmt(s['tp2'])}",
            "sl": _fmt(s["stop"]), "note": s["comment"] or "",
            "status": s["status"],
            "status_label": STATUS_LABELS.get(s["status"], s["status"]),
            "active": 1 if s["status"] in OPEN_STATUSES else 0,
            "created_at": s["created_at"],
        } for s in rows],
    }


@router.get("/video-lessons")
async def public_lessons(user=Depends(optional_user)):
    """video-darslar.html uchun."""
    if not await _can_see("videos", user):
        return {"lessons": [], "locked": True}
    rows = await db.get_content_by_type("videos")
    return {
        "locked": False,
        "lessons": [{
            "id": c["id"],
            "title": c["title"],
            "description": c["caption"] or "",
            "url": "",                      # fayl botda ochiladi
            "has_file": bool(c["file_id"]),
            "created_at": c["created_at"],
        } for c in rows],
    }


@router.get("/reminders")
async def public_reminders(user=Depends(optional_user)):
    """eslatmalar.html uchun."""
    if not await _can_see("reminders", user):
        return {"reminders": [], "locked": True}
    rows = await db.get_content_by_type("reminders")
    return {
        "locked": False,
        "reminders": [{
            "id": c["id"],
            "title": c["title"],
            "text": c["caption"] or "",
            "source": "",
            "created_at": c["created_at"],
        } for c in rows],
    }


@router.get("/strategies")
async def public_strategies(user=Depends(optional_user)):
    if not await _can_see("strategies", user):
        return {"strategies": [], "locked": True}
    rows = await db.get_content_by_type("strategies")
    return {
        "locked": False,
        "strategies": [{
            "id": c["id"], "title": c["title"], "text": c["caption"] or "",
            "has_file": bool(c["file_id"]), "created_at": c["created_at"],
        } for c in rows],
    }


@router.get("/mentorlik-seats")
async def mentorlik_seats():
    """kurs.html dagi o'rinlar hisoblagichi."""
    taken = int(await db.get_setting("mentorlik_taken", "0") or 0)
    total = int(await db.get_setting("mentorlik_total", str(MENTORLIK_TOTAL_SEATS)) or MENTORLIK_TOTAL_SEATS)
    taken = max(0, min(taken, total))
    return {"total": total, "taken": taken, "remaining": total - taken}


@router.get("/wallet")
async def public_wallet():
    """To'lov hamyoni — hozircha ko'rsatiladi, to'lov qabul qilinmaydi."""
    return {
        "address": await db.get_setting("wallet_address", "") or "",
        "network": await db.get_setting("wallet_network", "TRC20") or "TRC20",
    }


def _fmt(v) -> str:
    """Raqamni ortiqcha nollarsiz matnga aylantiradi: 65000.0 -> "65000"."""
    if v is None:
        return ""
    f = float(v)
    return str(int(f)) if f == int(f) else f"{f:g}"
