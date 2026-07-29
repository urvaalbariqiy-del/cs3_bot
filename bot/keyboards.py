from aiogram.types import (
    ReplyKeyboardMarkup, KeyboardButton,
    InlineKeyboardMarkup, InlineKeyboardButton,
)
from bot.config import TARIFF_NAMES, PERIOD_NAMES, SECTIONS


def _rows(buttons, per_row=2):
    """Tugmalar ro'yxatini qatorlarga bo'ladi."""
    return [buttons[i:i + per_row] for i in range(0, len(buttons), per_row)]


# ---------- USER SIDE ----------

def user_main_menu(custom_sections=()) -> ReplyKeyboardMarkup:
    """Foydalanuvchining asosiy menyusi.

    Bu yerda ataylab "obuna sotib olish" tugmasi yo'q — bot pullik ekani
    faqat yopiq bo'lim bosilganda ma'lum bo'ladi. is_persistent tugmalarni
    doim ko'rinib turadigan qiladi.
    """
    titles = [s["title"] for s in SECTIONS.values()]
    titles += [row["title"] for row in custom_sections]
    return ReplyKeyboardMarkup(
        keyboard=_rows([KeyboardButton(text=t) for t in titles], per_row=2),
        resize_keyboard=True,
        is_persistent=True,
    )


def subscribe_prompt_keyboard() -> InlineKeyboardMarkup:
    """Yopiq bo'lim bosilganda chiqadigan yagona tugma."""
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="💳 Obuna olish", callback_data="buy:open")
    ]])


def section_items_keyboard(section_code: str, items, is_signal: bool) -> InlineKeyboardMarkup:
    """Bo'lim ichidagi ro'yxat — har bir element alohida tugma.

    Foydalanuvchi tugmani bosgandagina to'liq ma'lumot ochiladi.
    """
    rows = []
    for it in items:
        if is_signal:
            label = f"💠 {it['coin']}"
        else:
            label = it["title"]
        rows.append([InlineKeyboardButton(
            text=label[:60], callback_data=f"open:{section_code}:{it['id']}"
        )])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def tariff_choice_keyboard() -> InlineKeyboardMarkup:
    rows = []
    for code, name in TARIFF_NAMES.items():
        rows.append([InlineKeyboardButton(text=name, callback_data=f"tariff:{code}")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def period_choice_keyboard(tariff_code: str) -> InlineKeyboardMarkup:
    rows = []
    for code, name in PERIOD_NAMES.items():
        rows.append([InlineKeyboardButton(
            text=name, callback_data=f"period:{tariff_code}:{code}"
        )])
    rows.append([InlineKeyboardButton(text="⬅️ Orqaga", callback_data="back_to_tariffs")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def confirm_payment_keyboard(tariff_code: str, period: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(
            text="✅ To'lov chekini yuborish",
            callback_data=f"send_receipt:{tariff_code}:{period}",
        )
    ]])


# ---------- ADMIN SIDE ----------

# Admin pastki menyusi — uchta bo'lim, boshqa hech narsa.
ADMIN_POST = "📤 Bo'limlarga joylash"
ADMIN_PAYMENT = "💳 To'lov tizimi"
ADMIN_SUBS = "🎫 Obunalar"


def admin_main_menu() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=ADMIN_POST)],
            [KeyboardButton(text=ADMIN_PAYMENT), KeyboardButton(text=ADMIN_SUBS)],
        ],
        resize_keyboard=True,
        is_persistent=True,
    )


def admin_post_sections_keyboard(custom_sections=()) -> InlineKeyboardMarkup:
    """1-bo'lim: qaysi foydalanuvchi bo'limiga narsa joylash."""
    rows = [[InlineKeyboardButton(text=s["title"], callback_data=f"post:{code}")]
            for code, s in SECTIONS.items()]
    rows += [[InlineKeyboardButton(text=row["title"], callback_data=f"post:{row['code']}")]
             for row in custom_sections]
    return InlineKeyboardMarkup(inline_keyboard=rows)


def admin_payment_keyboard() -> InlineKeyboardMarkup:
    """2-bo'lim: narx va to'lov usuli."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💵 Narxlarni o'zgartirish", callback_data="pay:prices")],
        [InlineKeyboardButton(text="💳 To'lov usulini kiritish", callback_data="pay:info")],
    ])


def admin_subs_keyboard() -> InlineKeyboardMarkup:
    """3-bo'lim: obuna darajasi va muddati."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⏳ Kutilayotgan to'lovlar", callback_data="sub:pending")],
        [InlineKeyboardButton(text="➕ Qo'lda obuna berish", callback_data="sub:grant")],
        [InlineKeyboardButton(text="🔍 Foydalanuvchi obunasi", callback_data="sub:check")],
        [InlineKeyboardButton(text="🚫 Qoidabuzarlik", callback_data="sub:violation")],
    ])


def payment_review_keyboard(payment_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="✅ Tasdiqlash", callback_data=f"pay_approve:{payment_id}"),
        InlineKeyboardButton(text="❌ Rad etish", callback_data=f"pay_reject:{payment_id}"),
    ]])


def signal_preview_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="✅ Tasdiqlash va joylash", callback_data="signal_confirm"),
        InlineKeyboardButton(text="❌ Bekor qilish", callback_data="signal_cancel"),
    ]])


def tariff_pick_keyboard(prefix: str, label: str = "Minimal daraja") -> InlineKeyboardMarkup:
    """Tarif tanlash. prefix callback'ni ajratib turadi (content_tariff / section_tariff / grant)."""
    rows = []
    for code, name in TARIFF_NAMES.items():
        rows.append([InlineKeyboardButton(
            text=f"{label}: {name}", callback_data=f"{prefix}:{code}"
        )])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def grant_period_keyboard(tariff_code: str) -> InlineKeyboardMarkup:
    rows = [[InlineKeyboardButton(text=name, callback_data=f"grantperiod:{tariff_code}:{code}")]
            for code, name in PERIOD_NAMES.items()]
    return InlineKeyboardMarkup(inline_keyboard=rows)


def prices_edit_keyboard() -> InlineKeyboardMarkup:
    rows = []
    for tcode, tname in TARIFF_NAMES.items():
        for pcode, pname in PERIOD_NAMES.items():
            rows.append([InlineKeyboardButton(
                text=f"{tname} — {pname}", callback_data=f"editprice:{tcode}:{pcode}"
            )])
    return InlineKeyboardMarkup(inline_keyboard=rows)
