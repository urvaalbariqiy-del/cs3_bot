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
import os
import uuid

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form

from bot import database as db
from bot import sections as sec
from bot.config import (
    ADMIN_IDS, TARIFF_NAMES, PERIOD_NAMES, MENTORLIK_TOTAL_SEATS,
    MEDIA_DIR, MAX_UPLOAD_BYTES,
)
from api.deps import admin_user

# Ruxsat etilgan fayl turlari (kengaytma -> tur)
_VIDEO_EXT = {".mp4", ".mov", ".webm", ".mkv", ".m4v"}
_IMAGE_EXT = {".jpg", ".jpeg", ".png", ".webp", ".gif"}
_AUDIO_EXT = {".mp3", ".m4a", ".ogg", ".oga", ".wav", ".aac"}


def _media_kind(name: str) -> str:
    ext = os.path.splitext(name or "")[1].lower()
    if ext in _IMAGE_EXT:
        return "image"
    if ext in _VIDEO_EXT:
        return "video"
    if ext in _AUDIO_EXT:
        return "audio"
    return ""


async def _save_upload(file: UploadFile, allowed_ext: set) -> str:
    """Yuklangan faylni MEDIA_DIR ga saqlaydi va fayl nomini qaytaradi."""
    ext = os.path.splitext(file.filename or "")[1].lower()
    if ext not in allowed_ext:
        raise HTTPException(status_code=400, detail="Fayl turi mos emas.")
    os.makedirs(MEDIA_DIR, exist_ok=True)
    name = uuid.uuid4().hex + ext
    dest = os.path.join(MEDIA_DIR, name)
    size = 0
    try:
        with open(dest, "wb") as out:
            while True:
                chunk = await file.read(1024 * 1024)
                if not chunk:
                    break
                size += len(chunk)
                if size > MAX_UPLOAD_BYTES:
                    raise HTTPException(status_code=413, detail="Fayl juda katta.")
                out.write(chunk)
    except HTTPException:
        if os.path.exists(dest):
            os.remove(dest)
        raise
    return name

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


async def _validate_signal(section, coin, entry, stop, tp1, tp2):
    """Signal maydonlarini tekshiradi va tozalangan qiymatlarni qaytaradi."""
    section = (section or "signals").strip()
    meta = await sec.by_code(section)
    if not meta or meta["kind"] != "signal":
        raise HTTPException(status_code=400, detail="Signal bo'limi topilmadi.")

    coin = (coin or "").strip().upper().replace("/", "").replace("-", "")
    if not coin.isalnum():
        raise HTTPException(status_code=400, detail="Coin nomi noto'g'ri. Masalan: BTCUSDT")

    try:
        entry = float(entry); stop = float(stop); tp1 = float(tp1); tp2 = float(tp2)
    except (KeyError, TypeError, ValueError):
        raise HTTPException(status_code=400, detail="Entry, Stop, TP1 va TP2 raqam bo'lishi kerak.")

    if not (stop < entry < tp1 < tp2):
        raise HTTPException(
            status_code=400,
            detail="Tartib noto'g'ri. Stop < Entry < TP1 < TP2 bo'lishi kerak.",
        )
    return section, coin, entry, stop, tp1, tp2


@router.post("/signals")
async def create_signal(payload: dict, admin=Depends(admin_user)):
    section, coin, entry, stop, tp1, tp2 = await _validate_signal(
        payload.get("section"), payload.get("coin"),
        payload.get("entry"), payload.get("stop"),
        payload.get("tp1"), payload.get("tp2"),
    )
    signal_id = await db.create_signal(
        coin, entry, stop, tp1, tp2,
        (payload.get("comment") or "").strip(), section=section,
    )
    return {"ok": True, "id": signal_id}


@router.post("/signals/upload")
async def create_signal_with_image(
    admin=Depends(admin_user),
    section: str = Form("signals"),
    coin: str = Form(...),
    entry: str = Form(...),
    stop: str = Form(...),
    tp1: str = Form(...),
    tp2: str = Form(...),
    comment: str = Form(""),
    file: UploadFile | None = File(None),
):
    """Signalni rasm bilan yaratadi (rasm ixtiyoriy)."""
    section, coin, entry, stop, tp1, tp2 = await _validate_signal(
        section, coin, entry, stop, tp1, tp2,
    )
    photo = None
    if file is not None and file.filename:
        photo = await _save_upload(file, _IMAGE_EXT)
    signal_id = await db.create_signal(
        coin, entry, stop, tp1, tp2,
        (comment or "").strip(), section=section, photo_id=photo,
    )
    return {"ok": True, "id": signal_id, "photo": photo}


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


@router.post("/videos/upload")
async def upload_video(
    admin=Depends(admin_user),
    title: str = Form(...),
    body: str = Form(""),
    file: UploadFile = File(...),
):
    """Tayyor video faylni yuklab, video dars sifatida saqlaydi."""
    title = (title or "").strip()
    if not title:
        raise HTTPException(status_code=400, detail="Sarlavha bo'sh bo'lmasin.")
    meta = await sec.by_code("videos")
    if not meta:
        raise HTTPException(status_code=400, detail="Video bo'limi topilmadi.")
    name = await _save_upload(file, _VIDEO_EXT)
    content_id = await db.add_content(
        "videos", title, name, (body or "").strip(), meta["min_tariff"],
    )
    return {"ok": True, "id": content_id, "file": name}


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


# ==================== KANAL (POSTS) ====================

@router.post("/posts")
async def create_post(
    admin=Depends(admin_user),
    title: str = Form(...),
    body: str = Form(""),
    link: str = Form(""),
    file: UploadFile | None = File(None),
):
    """Kanal maqolasini yaratadi: matn + ixtiyoriy media (rasm/video/audio) yoki havola."""
    title = (title or "").strip()
    if not title:
        raise HTTPException(status_code=400, detail="Sarlavha bo'sh bo'lmasin.")
    media = None
    kind = ""
    if file is not None and file.filename:
        media = await _save_upload(file, _IMAGE_EXT | _VIDEO_EXT | _AUDIO_EXT)
        kind = _media_kind(media)
    elif (link or "").strip():
        media = link.strip()
        kind = "link"
    post_id = await db.add_post(title, (body or "").strip(), media, kind)
    return {"ok": True, "id": post_id}


@router.delete("/posts/{post_id}")
async def remove_post(post_id: int, admin=Depends(admin_user)):
    if not await db.get_post(post_id):
        raise HTTPException(status_code=404, detail="Maqola topilmadi.")
    await db.delete_post(post_id)
    return {"ok": True}
