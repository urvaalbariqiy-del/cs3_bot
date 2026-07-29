from aiogram import Router, F, Bot
from aiogram.filters import CommandStart, Command
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from datetime import datetime

from bot import database as db
from bot import keyboards as kb
from bot.states import PaymentStates
from bot.config import ADMIN_IDS, TARIFF_ACCESS, TARIFF_NAMES, PERIOD_NAMES

router = Router()


def is_admin(telegram_id: int) -> bool:
    return telegram_id in ADMIN_IDS


@router.message(CommandStart())
async def cmd_start(message: Message):
    await db.get_or_create_user(
        message.from_user.id, message.from_user.username, message.from_user.full_name
    )
    if is_admin(message.from_user.id):
        await message.answer(
            "Salom, Admin! Boshqaruv uchun pastdagi tugmadan yoki /panel buyrug'idan foydalaning.",
            reply_markup=kb.admin_main_menu(),
        )
    else:
        await message.answer(
            "Assalomu alaykum! 👋\n\n"
            "Bu bot orqali kripto-spot yo'nalishidagi savdo signallari, video darsliklar "
            "va strategiyalarga obuna bo'lishingiz mumkin.\n\n"
            "Quyidagi menyudan foydalaning:",
            reply_markup=kb.user_main_menu(),
        )


@router.message(Command("menu"))
async def cmd_menu(message: Message):
    if is_admin(message.from_user.id):
        await message.answer("Admin menyu:", reply_markup=kb.admin_main_menu())
    else:
        await message.answer("Asosiy menyu:", reply_markup=kb.user_main_menu())


# ---------- OBUNA SOTIB OLISH ----------

@router.message(F.text == "💳 Obuna sotib olish")
async def buy_subscription(message: Message):
    await message.answer("Kerakli tarifni tanlang:", reply_markup=kb.tariff_choice_keyboard())


@router.callback_query(F.data.startswith("tariff:"))
async def choose_tariff(callback: CallbackQuery):
    tariff_code = callback.data.split(":")[1]
    await callback.message.edit_text(
        f"<b>{TARIFF_NAMES[tariff_code]}</b> tarifi tanlandi.\nObuna muddatini tanlang:",
        reply_markup=kb.period_choice_keyboard(tariff_code),
        parse_mode="HTML",
    )
    await callback.answer()


@router.callback_query(F.data == "back_to_tariffs")
async def back_to_tariffs(callback: CallbackQuery):
    await callback.message.edit_text("Kerakli tarifni tanlang:", reply_markup=kb.tariff_choice_keyboard())
    await callback.answer()


@router.callback_query(F.data.startswith("period:"))
async def choose_period(callback: CallbackQuery):
    _, tariff_code, period = callback.data.split(":")
    price_row = await db.get_price(tariff_code, period)
    if not price_row:
        await callback.answer("Narx topilmadi, admin bilan bog'laning.", show_alert=True)
        return

    text = (
        f"<b>{TARIFF_NAMES[tariff_code]} — {PERIOD_NAMES[period]}</b>\n\n"
        f"💵 Narx: {price_row['price']:.0f} {price_row['currency']}\n"
    )
    if price_row["payment_info"]:
        text += f"\n💳 To'lov usuli:\n{price_row['payment_info']}\n"
    text += "\nTo'lovni amalga oshirgach, chekni (skrinshotni) shu yerga rasm sifatida yuboring."

    await callback.message.edit_text(
        text, reply_markup=kb.confirm_payment_keyboard(tariff_code, period), parse_mode="HTML"
    )
    await callback.answer()


@router.callback_query(F.data.startswith("send_receipt:"))
async def ask_for_receipt(callback: CallbackQuery, state: FSMContext):
    _, tariff_code, period = callback.data.split(":")
    await state.update_data(tariff_code=tariff_code, period=period)
    await state.set_state(PaymentStates.waiting_screenshot)
    await callback.message.answer("📎 To'lov chekining skrinshotini rasm ko'rinishida yuboring.")
    await callback.answer()


@router.message(PaymentStates.waiting_screenshot, F.photo)
async def receive_receipt(message: Message, state: FSMContext, bot: Bot):
    data = await state.get_data()
    tariff_code = data["tariff_code"]
    period = data["period"]

    user = await db.get_user_by_telegram_id(message.from_user.id)
    file_id = message.photo[-1].file_id
    payment_id = await db.create_payment(user["id"], tariff_code, period, file_id)

    await message.answer(
        "✅ Chekingiz qabul qilindi va admin tekshiruvi uchun yuborildi. "
        "Tasdiqlangach obunangiz avtomatik faollashadi."
    )
    await state.clear()

    price_row = await db.get_price(tariff_code, period)
    caption = (
        f"🆕 <b>Yangi to'lov so'rovi</b>\n\n"
        f"👤 Foydalanuvchi: {message.from_user.full_name} (@{message.from_user.username})\n"
        f"🆔 ID: <code>{message.from_user.id}</code>\n"
        f"📦 Tarif: {TARIFF_NAMES[tariff_code]} — {PERIOD_NAMES[period]}\n"
        f"💵 Narx: {price_row['price']:.0f} {price_row['currency']}"
    )
    for admin_id in ADMIN_IDS:
        try:
            await bot.send_photo(
                admin_id, file_id, caption=caption,
                reply_markup=kb.payment_review_keyboard(payment_id), parse_mode="HTML",
            )
        except Exception:
            pass


@router.message(PaymentStates.waiting_screenshot)
async def receipt_wrong_type(message: Message):
    await message.answer("Iltimos, to'lov chekini rasm (screenshot) ko'rinishida yuboring.")


# ---------- MENING OBUNAM ----------

@router.message(F.text == "📊 Mening obunam")
async def my_subscription(message: Message):
    user = await db.get_user_by_telegram_id(message.from_user.id)
    sub = await db.get_active_subscription(user["id"])
    if not sub:
        await message.answer(
            "Sizda hozircha faol obuna yo'q.\n\"💳 Obuna sotib olish\" orqali tarif tanlashingiz mumkin."
        )
        return
    end_date = datetime.fromisoformat(sub["end_date"])
    await message.answer(
        f"📦 Tarif: <b>{TARIFF_NAMES[sub['tariff_code']]}</b>\n"
        f"⏳ Amal qilish muddati: {end_date.strftime('%d.%m.%Y %H:%M')} gacha\n"
        f"✅ Holat: Faol",
        parse_mode="HTML",
    )


async def _check_access(message: Message, section: str) -> bool:
    """section: 'signals' | 'videos' | 'strategies'"""
    user = await db.get_user_by_telegram_id(message.from_user.id)
    sub = await db.get_active_subscription(user["id"])
    if not sub:
        await message.answer(
            "🔒 Bu bo'lim faqat obunachilar uchun.\n\"💳 Obuna sotib olish\" orqali tarif tanlang."
        )
        return False
    if not TARIFF_ACCESS[sub["tariff_code"]][section]:
        await message.answer(
            "🔒 Sizning tarifingiz bu bo'limga kirish huquqini bermaydi.\n"
            "Yuqoriroq tarifga o'tish uchun \"💳 Obuna sotib olish\" bo'limiga o'ting."
        )
        return False
    return True


# ---------- SIGNALLAR ----------

STATUS_LABELS = {
    "pending": "⏳ Kutilmoqda",
    "active": "✅ Faol",
    "tp1_hit": "🎯 TP1 olindi (faol davom etmoqda)",
    "tp2_hit": "🎯 TP2 olindi — Yopiq",
    "stopped": "🛑 Stop bo'ldi — Yopiq",
    "closed": "❌ Yopiq",
}
CLOSED_STATUSES = {"tp2_hit", "stopped", "closed"}


@router.message(F.text == "📈 Signallar")
async def view_signals(message: Message):
    if not await _check_access(message, "signals"):
        return
    signals = await db.get_recent_signals(limit=10)
    if not signals:
        await message.answer("Hozircha signal joylanmagan.")
        return
    for s in signals:
        active_note = "❌ Signal faol emas" if s["status"] in CLOSED_STATUSES else "✅ Signal faol"
        text = (
            f"💠 <b>{s['coin']}</b>\n"
            f"Holat: {STATUS_LABELS.get(s['status'], s['status'])}\n"
            f"({active_note})\n\n"
            f"🎯 Entry: {s['entry']}\n"
            f"🛑 Stop: {s['stop']}\n"
            f"🥇 TP1: {s['tp1']}\n"
            f"🥈 TP2: {s['tp2']}"
        )
        if s["comment"]:
            text += f"\n\n📝 {s['comment']}"
        await message.answer(text, parse_mode="HTML", protect_content=True)


# ---------- VIDEO / STRATEGIYA ----------

@router.message(F.text == "🎓 Video darsliklar")
async def view_videos(message: Message):
    if not await _check_access(message, "videos"):
        return
    items = await db.get_content_by_type("video")
    if not items:
        await message.answer("Hozircha video darslik joylanmagan.")
        return
    for item in items:
        await message.answer_video(
            item["file_id"], caption=f"🎓 {item['title']}\n\n{item['caption'] or ''}",
            protect_content=True,
        )


@router.message(F.text == "🧠 Strategiyalar")
async def view_strategies(message: Message):
    if not await _check_access(message, "strategies"):
        return
    items = await db.get_content_by_type("strategy")
    if not items:
        await message.answer("Hozircha strategiya joylanmagan.")
        return
    for item in items:
        if item["file_id"]:
            await message.answer_document(
                item["file_id"], caption=f"🧠 {item['title']}\n\n{item['caption'] or ''}",
                protect_content=True,
            )
        else:
            await message.answer(
                f"🧠 <b>{item['title']}</b>\n\n{item['caption'] or ''}",
                parse_mode="HTML", protect_content=True,
            )
