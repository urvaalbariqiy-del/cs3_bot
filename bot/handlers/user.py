from aiogram import Router, F, Bot
from aiogram.filters import CommandStart, Command, StateFilter
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from datetime import datetime

from bot import database as db
from bot import keyboards as kb
from bot import sections as sec
from bot.states import PaymentStates
from bot.config import ADMIN_IDS, TARIFF_NAMES, PERIOD_NAMES

router = Router()


def is_admin(telegram_id: int) -> bool:
    return telegram_id in ADMIN_IDS


async def _ensure_user(message: Message) -> int:
    """Foydalanuvchi bazada borligini kafolatlaydi va uning ichki id'sini qaytaradi.

    /start bosilmagan holatda (masalan eski chatdagi tugma orqali kelganda) ham
    xato bermasligi uchun barcha bo'limlarda shu funksiyadan foydalanamiz.
    """
    return await db.get_or_create_user(
        message.from_user.id, message.from_user.username, message.from_user.full_name
    )


async def _user_tariff(user_id: int):
    sub = await db.get_active_subscription(user_id)
    return sub["tariff_code"] if sub else None


async def user_menu():
    return kb.user_main_menu(await db.get_custom_sections())


# ---------- START / MENU ----------

@router.message(CommandStart())
async def cmd_start(message: Message):
    await _ensure_user(message)
    if is_admin(message.from_user.id):
        await message.answer(
            "Salom, Admin! 👋\n\n"
            "Pastdagi uchta tugma orqali boshqarasiz. Tezkor buyruqlar esa "
            "yozish maydonidagi ☰ menyuda.",
            reply_markup=kb.admin_main_menu(),
        )
    else:
        await message.answer(
            "Assalomu alaykum! 👋\n\n"
            "Bu yerda kripto bozori bo'yicha savdo signallari, skalping, "
            "video darsliklar va strategiyalar jamlangan.\n\n"
            "Qiziqqan bo'limingizni tanlang:",
            reply_markup=await user_menu(),
        )


@router.message(Command("menu"))
async def cmd_menu(message: Message):
    if is_admin(message.from_user.id):
        await message.answer("Admin menyu:", reply_markup=kb.admin_main_menu())
    else:
        await message.answer("Asosiy menyu:", reply_markup=await user_menu())


# ---------- BO'LIMLAR ----------

STATUS_LABELS = {
    "pending": "⏳ Kutilmoqda",
    "active": "✅ Faol",
    "tp1_hit": "🎯 TP1 olindi (faol davom etmoqda)",
    "tp2_hit": "🎯 TP2 olindi — Yopiq",
    "stopped": "🛑 Stop bo'ldi — Yopiq",
    "closed": "❌ Yopiq",
}
CLOSED_STATUSES = {"tp2_hit", "stopped", "closed"}


def signal_text(s) -> str:
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
    return text


# StateFilter(None) muhim: foydalanuvchi biror jarayon o'rtasida bo'lsa
# (masalan to'lov cheki kutilayotgan bo'lsa) bu handler aralashmasligi kerak.
@router.message(StateFilter(None), F.text.func(lambda t: t and not t.startswith("/")))
async def open_section(message: Message):
    """Asosiy tugmalardan biri bosilganda ishlaydi.

    Bo'lim ochiq bo'lsa — ichidagi ro'yxat tugmalar ko'rinishida chiqadi;
    yopiq bo'lsa — qaysi obuna kerakligi aytiladi.
    """
    code, meta = await sec.by_title(message.text)
    if not code:
        return  # boshqa matnlarga aralashmaymiz

    user_id = await _ensure_user(message)
    tariff = await _user_tariff(user_id)

    if not sec.has_access(tariff, meta["min_tariff"]):
        await message.answer(
            f"🔒 <b>{meta['title']}</b> bo'limi "
            f"<b>{sec.tariff_label(meta['min_tariff'])}</b> obunasi uchun.\n\n"
            f"Obuna ochsangiz, bu bo'lim va undan pastki darajadagi barcha "
            f"bo'limlar siz uchun ochiladi.",
            parse_mode="HTML",
            reply_markup=kb.subscribe_prompt_keyboard(),
        )
        return

    if meta["kind"] == "signal":
        items = await db.get_recent_signals(limit=10, section=code)
        if not items:
            await message.answer(f"{meta['title']} — hozircha bo'sh.")
            return
        await message.answer(
            f"{meta['title']}\n\nKo'rmoqchi bo'lganingizni tanlang:",
            reply_markup=kb.section_items_keyboard(code, items, is_signal=True),
        )
    else:
        items = await db.get_content_by_type(code)
        if not items:
            await message.answer(f"{meta['title']} — hozircha bo'sh.")
            return
        await message.answer(
            f"{meta['title']}\n\nKo'rmoqchi bo'lganingizni tanlang:",
            reply_markup=kb.section_items_keyboard(code, items, is_signal=False),
        )


@router.callback_query(F.data.startswith("open:"))
async def open_item(callback: CallbackQuery):
    _, code, item_id = callback.data.split(":")
    meta = await sec.by_code(code)
    if not meta:
        await callback.answer("Bo'lim topilmadi.", show_alert=True)
        return

    user_id = await db.get_or_create_user(
        callback.from_user.id, callback.from_user.username, callback.from_user.full_name
    )
    tariff = await _user_tariff(user_id)
    if not sec.has_access(tariff, meta["min_tariff"]):
        await callback.answer("Bu bo'lim sizning tarifingizda ochilmagan.", show_alert=True)
        return

    if meta["kind"] == "signal":
        s = await db.get_signal(int(item_id))
        if not s:
            await callback.answer("Topilmadi.", show_alert=True)
            return
        if s["photo_id"]:
            await callback.message.answer_photo(
                s["photo_id"], caption=signal_text(s), parse_mode="HTML", protect_content=True
            )
        else:
            await callback.message.answer(
                signal_text(s), parse_mode="HTML", protect_content=True
            )
    else:
        item = await db.get_content(int(item_id))
        if not item:
            await callback.answer("Topilmadi.", show_alert=True)
            return
        caption = f"<b>{item['title']}</b>"
        if item["caption"]:
            caption += f"\n\n{item['caption']}"
        if item["file_id"] and code == "videos":
            await callback.message.answer_video(
                item["file_id"], caption=caption, parse_mode="HTML", protect_content=True
            )
        elif item["file_id"]:
            await callback.message.answer_document(
                item["file_id"], caption=caption, parse_mode="HTML", protect_content=True
            )
        else:
            await callback.message.answer(
                caption, parse_mode="HTML", protect_content=True
            )
    await callback.answer()


# ---------- OBUNA ----------

@router.callback_query(F.data == "buy:open")
async def buy_from_lock(callback: CallbackQuery):
    await callback.message.answer(
        "Kerakli tarifni tanlang:", reply_markup=kb.tariff_choice_keyboard()
    )
    await callback.answer()


@router.message(Command("obuna"))
async def cmd_buy(message: Message):
    await _ensure_user(message)
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
    await callback.message.edit_text(
        "Kerakli tarifni tanlang:", reply_markup=kb.tariff_choice_keyboard()
    )
    await callback.answer()


def _price_header(tariff_code: str, period: str, price_row) -> str:
    return (
        f"<b>{TARIFF_NAMES[tariff_code]} — {PERIOD_NAMES[period]}</b>\n\n"
        f"💵 Narx: {price_row['price']:.0f} {price_row['currency']}\n"
    )


@router.callback_query(F.data.startswith("period:"))
async def choose_period(callback: CallbackQuery):
    _, tariff_code, period = callback.data.split(":")
    price_row = await db.get_price(tariff_code, period)
    if not price_row:
        await callback.answer("Narx topilmadi, admin bilan bog'laning.", show_alert=True)
        return

    methods = await db.get_payment_methods()
    if not methods:
        await callback.message.edit_text(
            _price_header(tariff_code, period, price_row) +
            "\n⚠️ To'lov usullari hali kiritilmagan. Iltimos, admin bilan bog'laning.",
            parse_mode="HTML",
        )
        await callback.answer()
        return

    # Usul bitta bo'lsa ortiqcha qadam qilmaymiz - to'g'ridan-to'g'ri ko'rsatamiz.
    if len(methods) == 1:
        await _show_payment_details(callback, tariff_code, period, methods[0], price_row)
        return

    await callback.message.edit_text(
        _price_header(tariff_code, period, price_row) + "\nQaysi usul bilan to'laysiz?",
        reply_markup=kb.payment_method_choice_keyboard(tariff_code, period, methods),
        parse_mode="HTML",
    )
    await callback.answer()


async def _show_payment_details(callback: CallbackQuery, tariff_code: str, period: str,
                                method, price_row=None):
    price_row = price_row or await db.get_price(tariff_code, period)
    text = (
        _price_header(tariff_code, period, price_row) +
        f"\n💳 <b>{method['title']}</b>\n{method['details']}\n\n"
        f"To'lovni amalga oshirgach, chekni (skrinshotni) shu yerga rasm sifatida yuboring."
    )
    await callback.message.edit_text(
        text,
        reply_markup=kb.confirm_payment_keyboard(tariff_code, period, method["id"]),
        parse_mode="HTML",
    )
    await callback.answer()


@router.callback_query(F.data.startswith("paymethod:"))
async def choose_payment_method(callback: CallbackQuery):
    _, tariff_code, period, method_id = callback.data.split(":")
    method = await db.get_payment_method(int(method_id))
    if not method:
        await callback.answer("Bu usul o'chirilgan. Boshqasini tanlang.", show_alert=True)
        return
    await _show_payment_details(callback, tariff_code, period, method)


@router.callback_query(F.data.startswith("send_receipt:"))
async def ask_for_receipt(callback: CallbackQuery, state: FSMContext):
    # Eski xabarlardagi tugmalarda to'lov usuli ko'rsatilmagan bo'lishi mumkin -
    # shuning uchun uzunligini qat'iy talab qilmaymiz.
    parts = callback.data.split(":")
    tariff_code, period = parts[1], parts[2]
    method_id = int(parts[3]) if len(parts) > 3 else None
    await state.update_data(tariff_code=tariff_code, period=period, method_id=method_id)
    await state.set_state(PaymentStates.waiting_screenshot)
    await callback.message.answer("📎 To'lov chekining skrinshotini rasm ko'rinishida yuboring.")
    await callback.answer()


@router.message(PaymentStates.waiting_screenshot, F.photo)
async def receive_receipt(message: Message, state: FSMContext, bot: Bot):
    data = await state.get_data()
    tariff_code = data["tariff_code"]
    period = data["period"]

    user_id = await _ensure_user(message)
    file_id = message.photo[-1].file_id
    payment_id = await db.create_payment(user_id, tariff_code, period, file_id)

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
    if data.get("method_id"):
        method = await db.get_payment_method(data["method_id"])
        if method:
            caption += f"\n💳 Usul: {method['title']}"
    for admin_id in ADMIN_IDS:
        try:
            await bot.send_photo(
                admin_id, file_id, caption=caption,
                reply_markup=kb.payment_review_keyboard(payment_id), parse_mode="HTML",
            )
        except Exception:
            pass


# Buyruqlarni bu handler ushlamasligi kerak: chek kutilayotganda ham
# /obunam, /obuna kabi buyruqlar ishlashi lozim.
@router.message(PaymentStates.waiting_screenshot,
                F.text.func(lambda t: not (t or "").startswith("/")))
async def receipt_wrong_type(message: Message):
    await message.answer("Iltimos, to'lov chekini rasm (screenshot) ko'rinishida yuboring.")


@router.message(Command("bekor"))
async def cmd_cancel(message: Message, state: FSMContext):
    if await state.get_state() is None:
        await message.answer("Bekor qiladigan amal yo'q.")
        return
    await state.clear()
    await message.answer("Bekor qilindi.", reply_markup=await user_menu())


# ---------- MENING OBUNAM ----------

@router.message(Command("obunam"))
async def my_subscription(message: Message):
    user_id = await _ensure_user(message)
    sub = await db.get_active_subscription(user_id)
    if not sub:
        await message.answer(
            "Sizda hozircha faol obuna yo'q.\n"
            "/obuna buyrug'i orqali tarif tanlashingiz mumkin."
        )
        return

    end_date = datetime.fromisoformat(sub["end_date"])
    left = end_date - datetime.utcnow()
    days, hours = left.days, left.seconds // 3600

    opened = [m["title"] for m in (await sec.all_sections()).values()
              if sec.has_access(sub["tariff_code"], m["min_tariff"])]

    await message.answer(
        f"📦 Tarif: <b>{TARIFF_NAMES[sub['tariff_code']]}</b>\n"
        f"⏳ Tugash sanasi: {end_date.strftime('%d.%m.%Y %H:%M')}\n"
        f"🕒 Qolgan muddat: {days} kun {hours} soat\n"
        f"✅ Holat: Faol\n\n"
        f"🔓 Sizga ochiq bo'limlar:\n" + "\n".join(f"• {t}" for t in opened),
        parse_mode="HTML",
    )
