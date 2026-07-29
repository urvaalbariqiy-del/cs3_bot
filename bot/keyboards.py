from aiogram.types import (
    ReplyKeyboardMarkup, KeyboardButton,
    InlineKeyboardMarkup, InlineKeyboardButton,
)
from bot.config import TARIFF_NAMES, PERIOD_NAMES


# ---------- USER SIDE ----------

def user_main_menu() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="💳 Obuna sotib olish"), KeyboardButton(text="📊 Mening obunam")],
            [KeyboardButton(text="📈 Signallar"), KeyboardButton(text="🎓 Video darsliklar")],
            [KeyboardButton(text="🧠 Strategiyalar")],
        ],
        resize_keyboard=True,
    )


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

def admin_main_menu() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="⚙️ Admin panel")],
        ],
        resize_keyboard=True,
    )


def admin_panel_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🟢 Yangi signal", callback_data="admin:new_signal")],
        [InlineKeyboardButton(text="📋 So'nggi signallar", callback_data="admin:list_signals")],
        [InlineKeyboardButton(text="💰 Narxlarni sozlash", callback_data="admin:prices")],
        [InlineKeyboardButton(text="🎓 Kontent qo'shish", callback_data="admin:add_content")],
        [InlineKeyboardButton(text="⏳ Kutilayotgan to'lovlar", callback_data="admin:pending_payments")],
        [InlineKeyboardButton(text="📢 Umumiy xabar (broadcast)", callback_data="admin:broadcast")],
        [InlineKeyboardButton(text="🚫 Qoidabuzarlik / ogohlantirish", callback_data="admin:violation")],
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


def content_type_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🎓 Video darslik", callback_data="content_type:video")],
        [InlineKeyboardButton(text="🧠 Strategiya", callback_data="content_type:strategy")],
    ])


def content_tariff_keyboard() -> InlineKeyboardMarkup:
    rows = []
    for code, name in TARIFF_NAMES.items():
        rows.append([InlineKeyboardButton(
            text=f"Minimal daraja: {name}", callback_data=f"content_tariff:{code}"
        )])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def prices_edit_keyboard() -> InlineKeyboardMarkup:
    rows = []
    for tcode, tname in TARIFF_NAMES.items():
        for pcode, pname in PERIOD_NAMES.items():
            rows.append([InlineKeyboardButton(
                text=f"{tname} — {pname}", callback_data=f"editprice:{tcode}:{pcode}"
            )])
    return InlineKeyboardMarkup(inline_keyboard=rows)
