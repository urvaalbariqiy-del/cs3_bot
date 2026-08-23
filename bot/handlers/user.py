from aiogram import Router, F, Bot
from aiogram.filters import CommandStart, Command, StateFilter, CommandObject
from aiogram.types import Message, CallbackQuery, ReplyKeyboardRemove
from aiogram.fsm.context import FSMContext
from datetime import datetime
from html import escape

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


WELCOME = (
    "Assalomu alaykum! 👋\n\n"
    "Bu yerda kripto bozori bo'yicha savdo signallari, skalping, "
    "video darsliklar va strategiyalar jamlangan.\n\n"
    "Qiziqqan bo'limingizni tanlang:"
)


async def _drop_old_keyboard(message: Message):
    """Eskirgan pastki klaviaturani chatdan olib tashlaydi.

    Ilgari menyu yozish maydonining pastida edi; endi tugmalar xabar bilan
    birga chiqadi. Eski klaviatura foydalanuvchida osilib qolmasligi uchun
    uni bir marta yo'q qilib, xizmatchi xabarni o'chirib yuboramiz.
    """
    try:
        tmp = await message.answer("…", reply_markup=ReplyKeyboardRemove())
        # message.bot ishlatamiz: qaytgan obyekt botga bog'langaniga tayanmaymiz
        await message.bot.delete_message(chat_id=tmp.chat.id, message_id=tmp.message_id)
    except Exception:
        pass


# ---------- START / MENU ----------

@router.message(CommandStart(deep_link=True))
async def cmd_start_deeplink(message: Message, command: CommandObject):
    """Saytdan kelgan ulanish havolasi: /start <token>.

    Foydalanuvchi saytda "Telegram orqali ulanish" bosadi, bot ochiladi,
    /start bosadi — va sayt o'zi kirgizadi. Boshqa hech narsa qilmaydi.
    """
    token = (command.args or "").strip()
    await _ensure_user(message)

    if token and await db.bind_login_token(token, message.from_user.id):
        await message.answer(
            "✅ <b>Tayyor!</b>\n\n"
            "Saytga qaytishingiz mumkin — u sizni o'zi tanidi.\n"
            "Bu oynani yopsangiz ham bo'ladi.",
            parse_mode="HTML",
        )
        return

    if token:
        await message.answer(
            "⏳ Bu havolaning muddati tugagan yoki allaqachon ishlatilgan.\n\n"
            "Saytga qaytib, \"Telegram orqali ulanish\" tugmasini qaytadan bosing."
        )
        return

    await cmd_start(message)


@router.message(CommandStart())
async def cmd_start(message: Message):
    await _ensure_user(message)
    await _drop_old_keyboard(message)
    if is_admin(message.from_user.id):
        await message.answer(
            "Salom, Admin! 👋\n\nQuyidagi bo'limlardan birini tanlang. "
            "Tezkor buyruqlar esa yozish maydonidagi ☰ menyuda.",
            reply_markup=kb.admin_main_menu(),
        )
    else:
        await message.answer(WELCOME, reply_markup=await user_menu())


@router.message(Command("menu"))
async def cmd_menu(message: Message):
    await _drop_old_keyboard(message)
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


async def _edit(callback: CallbackQuery, text: str, markup=None):
    """Xabarni joyida yangilaydi. Bir xil matn qayta yuborilsa Telegram
    xato beradi — uni e'tiborsiz qoldiramiz."""
    try:
        await callback.message.edit_text(text, reply_markup=markup, parse_mode="HTML")
    except Exception:
        await callback.message.answer(text, reply_markup=markup, parse_mode="HTML")


@router.callback_query(F.data.startswith("sec:"))
async def open_section(callback: CallbackQuery):
    """Asosiy menyudagi bo'lim tugmasi bosilganda.

    Bo'lim ochiq bo'lsa — ichidagi ro'yxat shu xabarning o'zida chiqadi;
    yopiq bo'lsa — qaysi obuna kerakligi aytiladi.
    """
    code = callback.data.split(":")[1]
    user_id = await db.get_or_create_user(
        callback.from_user.id, callback.from_user.username, callback.from_user.full_name
    )

    if code == "menu":
        await _edit(callback, WELCOME, await user_menu())
        await callback.answer()
        return

    meta = await sec.by_code(code)
    if not meta:
        await callback.answer("Bu bo'lim endi mavjud emas.", show_alert=True)
        return

    tariff = await _user_tariff(user_id)
    if not sec.has_access(tariff, meta["min_tariff"]):
        await _edit(
            callback,
            f"🔒 <b>{meta['title']}</b> bo'limi "
            f"<b>{sec.tariff_label(meta['min_tariff'])}</b> obunasi uchun.\n\n"
            f"Obuna ochsangiz, bu bo'lim va undan pastki darajadagi barcha "
            f"bo'limlar siz uchun ochiladi.",
            kb.subscribe_prompt_keyboard(),
        )
        await callback.answer()
        return

    is_signal = meta["kind"] == "signal"
    items = (await db.get_recent_signals(limit=10, section=code) if is_signal
             else await db.get_content_by_type(code))

    if not items:
        await _edit(callback, f"{meta['title']}\n\nHozircha bo'sh.", kb.back_to_menu_keyboard())
    else:
        await _edit(
            callback,
            f"<b>{meta['title']}</b>\n\nKo'rmoqchi bo'lganingizni tanlang:",
            kb.section_items_keyboard(code, items, is_signal),
        )
    await callback.answer()


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
    # Rekvizit <code> ichida beriladi: Telegram'da ustiga bosilsa nusxalanadi.
    # Karta raqami va kripto hamyon manzilini qo'lda ko'chirishda xato bo'lmasligi uchun.
    text = (
        _price_header(tariff_code, period, price_row) +
        f"\n💳 <b>{escape(method['title'])}</b>\n"
        f"<code>{escape(method['details'])}</code>\n\n"
        f"👆 Rekvizit ustiga bossangiz nusxalanadi.\n\n"
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
        reply_markup=await user_menu(),
    )


# ---------- TANILMAGAN XABAR ----------
# Pastda doimiy klaviatura yo'q, shuning uchun foydalanuvchi nima yozsa ham
# menyuni qaytarib beramiz - u hech qachon "yo'qolib" qolmasin.
# Eng oxirida ro'yxatdan o'tadi, ya'ni qolgan handlerlar birinchi navbatda ishlaydi.

@router.message(StateFilter(None))
async def fallback_to_menu(message: Message):
    await _ensure_user(message)
    if is_admin(message.from_user.id):
        await message.answer("⚙️ Admin menyu:", reply_markup=kb.admin_main_menu())
    else:
        await message.answer("Quyidagi bo'limlardan tanlang:", reply_markup=await user_menu())
