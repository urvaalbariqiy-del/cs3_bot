import time
from html import escape

from aiogram import Router, F, Bot
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext

from bot import database as db
from bot import keyboards as kb
from bot import sections as sec
from bot.states import (
    SignalStates, ContentStates, PriceEditStates, PaymentMethodStates,
    BroadcastStates, ViolationStates, NewSectionStates, GrantSubStates,
)
from bot.config import ADMIN_IDS, TARIFF_NAMES, PERIOD_NAMES

router = Router()

# Ushbu routerdagi BARCHA handlerlar faqat ADMIN_IDS ichidagi foydalanuvchilar uchun ishlaydi.
router.message.filter(F.from_user.id.in_(ADMIN_IDS))
router.callback_query.filter(F.from_user.id.in_(ADMIN_IDS))


# =====================================================================
# UCHTA ASOSIY BO'LIM
# =====================================================================

POST_TEXT = "📤 <b>Bo'limlarga joylash</b>\n\nQaysi bo'limga joylaysiz?"
PAY_TEXT = "💳 <b>To'lov tizimi</b>\n\nNimani o'zgartiramiz?"
SUBS_TEXT = "🎫 <b>Obunalar</b>\n\nNima qilamiz?"
MENU_TEXT = "⚙️ <b>Admin menyu</b>\n\nBo'limni tanlang:"


async def _post_markup():
    return kb.admin_post_sections_keyboard(await db.get_custom_sections())


async def _edit(callback: CallbackQuery, text: str, markup=None):
    try:
        await callback.message.edit_text(text, reply_markup=markup, parse_mode="HTML")
    except Exception:
        await callback.message.answer(text, reply_markup=markup, parse_mode="HTML")


# --- buyruqlar (☰ menyu) ---

@router.message(Command("joylash"))
async def cmd_post(message: Message, state: FSMContext):
    await state.clear()
    await message.answer(POST_TEXT, reply_markup=await _post_markup(), parse_mode="HTML")


@router.message(Command("tolov"))
async def cmd_pay(message: Message, state: FSMContext):
    await state.clear()
    await message.answer(PAY_TEXT, reply_markup=kb.admin_payment_keyboard(), parse_mode="HTML")


@router.message(Command("obunalar"))
async def cmd_subs(message: Message, state: FSMContext):
    await state.clear()
    await message.answer(SUBS_TEXT, reply_markup=kb.admin_subs_keyboard(), parse_mode="HTML")


# --- admin menyusidagi tugmalar ---

@router.callback_query(F.data == "adm:menu")
async def adm_menu(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await _edit(callback, MENU_TEXT, kb.admin_main_menu())
    await callback.answer()


@router.callback_query(F.data == "adm:post")
async def adm_post(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await _edit(callback, POST_TEXT, await _post_markup())
    await callback.answer()


@router.callback_query(F.data == "adm:pay")
async def adm_pay(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await _edit(callback, PAY_TEXT, kb.admin_payment_keyboard())
    await callback.answer()


@router.callback_query(F.data == "adm:subs")
async def adm_subs(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await _edit(callback, SUBS_TEXT, kb.admin_subs_keyboard())
    await callback.answer()


@router.message(Command("bekor"))
async def cancel_any(message: Message, state: FSMContext):
    await state.clear()
    await message.answer("Bekor qilindi.", reply_markup=kb.admin_main_menu())


# =====================================================================
# 1-BO'LIM: BO'LIMLARGA JOYLASH
# =====================================================================

@router.callback_query(F.data.startswith("post:"))
async def post_to_section(callback: CallbackQuery, state: FSMContext):
    code = callback.data.split(":")[1]
    meta = await sec.by_code(code)
    if not meta:
        await callback.answer("Bo'lim topilmadi.", show_alert=True)
        return

    await state.update_data(section=code)

    if meta["kind"] == "signal":
        await state.set_state(SignalStates.coin)
        await callback.message.answer(
            f"{meta['title']} — yangi signal.\n\n"
            f"Coin nomini kiriting (masalan: <code>BTCUSDT</code>):",
            parse_mode="HTML",
        )
    else:
        await state.set_state(ContentStates.title)
        await callback.message.answer(f"{meta['title']} — sarlavhani kiriting:")
    await callback.answer()


# ---------- signal yaratish ----------

@router.message(SignalStates.coin)
async def signal_get_coin(message: Message, state: FSMContext):
    coin = message.text.strip().upper().replace("/", "").replace("-", "")
    if not coin.isalnum():
        await message.answer("Noto'g'ri format. Masalan: BTCUSDT. Qaytadan kiriting:")
        return
    await state.update_data(coin=coin)
    await state.set_state(SignalStates.entry)
    await message.answer("Kirish narxini (Entry) kiriting:")


@router.message(SignalStates.entry)
async def signal_get_entry(message: Message, state: FSMContext):
    try:
        entry = float(message.text.replace(",", "."))
    except ValueError:
        await message.answer("Raqam kiriting. Masalan: 65000")
        return
    await state.update_data(entry=entry)
    await state.set_state(SignalStates.stop)
    await message.answer("Stop narxini kiriting (Entry'dan past bo'lishi kerak):")


@router.message(SignalStates.stop)
async def signal_get_stop(message: Message, state: FSMContext):
    try:
        stop = float(message.text.replace(",", "."))
    except ValueError:
        await message.answer("Raqam kiriting.")
        return
    data = await state.get_data()
    if stop >= data["entry"]:
        await message.answer(
            "⚠️ Xato: Stop narxi Entry narxidan past bo'lishi kerak (spot/long signal uchun). "
            "Qaytadan kiriting:"
        )
        return
    await state.update_data(stop=stop)
    await state.set_state(SignalStates.tp1)
    await message.answer("TP1 (birinchi profit) narxini kiriting (Entry'dan yuqori bo'lishi kerak):")


@router.message(SignalStates.tp1)
async def signal_get_tp1(message: Message, state: FSMContext):
    try:
        tp1 = float(message.text.replace(",", "."))
    except ValueError:
        await message.answer("Raqam kiriting.")
        return
    data = await state.get_data()
    if tp1 <= data["entry"]:
        await message.answer("⚠️ Xato: TP1 Entry narxidan yuqori bo'lishi kerak. Qaytadan kiriting:")
        return
    await state.update_data(tp1=tp1)
    await state.set_state(SignalStates.tp2)
    await message.answer("TP2 (ikkinchi profit) narxini kiriting (TP1'dan yuqori bo'lishi kerak):")


@router.message(SignalStates.tp2)
async def signal_get_tp2(message: Message, state: FSMContext):
    try:
        tp2 = float(message.text.replace(",", "."))
    except ValueError:
        await message.answer("Raqam kiriting.")
        return
    data = await state.get_data()
    if tp2 <= data["tp1"]:
        await message.answer("⚠️ Xato: TP2 TP1 narxidan yuqori bo'lishi kerak. Qaytadan kiriting:")
        return
    await state.update_data(tp2=tp2)
    await state.set_state(SignalStates.comment)
    await message.answer("Qo'shimcha izoh kiriting (bo'lmasa \"-\" deb yuboring):")


@router.message(SignalStates.comment)
async def signal_get_comment(message: Message, state: FSMContext):
    comment = "" if message.text.strip() == "-" else message.text.strip()
    await state.update_data(comment=comment)
    await state.set_state(SignalStates.photo)
    await message.answer(
        "📷 Signal uchun rasm (grafik skrinshoti) yuboring.\n"
        "Rasm kerak bo'lmasa \"-\" deb yozing."
    )


async def _signal_preview(message: Message, state: FSMContext):
    data = await state.get_data()
    meta = await sec.by_code(data["section"])
    preview = (
        f"📋 <b>Ko'rinishi ({meta['title']}):</b>\n\n"
        f"💠 <b>{data['coin']}</b>\n"
        f"🎯 Entry: {data['entry']}\n"
        f"🛑 Stop: {data['stop']}\n"
        f"🥇 TP1: {data['tp1']}\n"
        f"🥈 TP2: {data['tp2']}"
    )
    if data.get("comment"):
        preview += f"\n\n📝 {data['comment']}"

    await state.set_state(SignalStates.confirm)
    if data.get("photo_id"):
        await message.answer_photo(
            data["photo_id"], caption=preview,
            reply_markup=kb.signal_preview_keyboard(), parse_mode="HTML",
        )
    else:
        await message.answer(
            preview, reply_markup=kb.signal_preview_keyboard(), parse_mode="HTML"
        )


@router.message(SignalStates.photo, F.photo)
async def signal_get_photo(message: Message, state: FSMContext):
    await state.update_data(photo_id=message.photo[-1].file_id)
    await _signal_preview(message, state)


@router.message(SignalStates.photo)
async def signal_skip_photo(message: Message, state: FSMContext):
    if message.text and message.text.strip() == "-":
        await state.update_data(photo_id=None)
        await _signal_preview(message, state)
    else:
        await message.answer("Rasm yuboring yoki \"-\" deb yozing.")


@router.callback_query(SignalStates.confirm, F.data == "signal_confirm")
async def signal_confirm(callback: CallbackQuery, state: FSMContext, bot: Bot):
    data = await state.get_data()
    code = data["section"]
    meta = await sec.by_code(code)

    await db.create_signal(
        data["coin"], data["entry"], data["stop"], data["tp1"], data["tp2"],
        data.get("comment", ""), section=code, photo_id=data.get("photo_id"),
    )
    await state.clear()
    await callback.message.answer("✅ Joylandi va narx kuzatuvi boshlandi.")
    await callback.answer()

    await notify_new_item(
        bot,
        min_tariff=meta["min_tariff"],
        full_text=(
            f"🆕 <b>Yangi signal: {meta['title']}</b>\n\n"
            f"💠 {data['coin']}\n"
            f"Holat: ⏳ Kutilmoqda (narx entry nuqtasiga yetganda faollashadi)\n\n"
            f"To'liq ma'lumot uchun \"{meta['title']}\" bo'limiga kiring."
        ),
        teaser_text=(
            f"🔔 <b>{meta['title']}</b> bo'limiga yangi signal qo'shildi.\n\n"
            f"Signal tafsilotlari (coin, kirish narxi, stop va profit darajalari) "
            f"faqat obunachilarga ko'rinadi."
        ),
    )


@router.callback_query(SignalStates.confirm, F.data == "signal_cancel")
async def signal_cancel(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.answer("❌ Bekor qilindi.")
    await callback.answer()


# ---------- kontent qo'shish ----------

@router.message(ContentStates.title)
async def content_get_title(message: Message, state: FSMContext):
    await state.update_data(title=message.text.strip())
    await state.set_state(ContentStates.file)
    data = await state.get_data()
    if data["section"] == "videos":
        await message.answer("Video faylni yuboring:")
    else:
        await message.answer(
            "Fayl (PDF/dokument), video yoki oddiy matn yuboring:"
        )


@router.message(ContentStates.file, F.video)
async def content_get_video(message: Message, state: FSMContext):
    await state.update_data(file_id=message.video.file_id)
    await state.set_state(ContentStates.caption)
    await message.answer("Qisqacha tavsif kiriting (bo'lmasa \"-\" yuboring):")


@router.message(ContentStates.file, F.document)
async def content_get_document(message: Message, state: FSMContext):
    await state.update_data(file_id=message.document.file_id)
    await state.set_state(ContentStates.caption)
    await message.answer("Qisqacha tavsif kiriting (bo'lmasa \"-\" yuboring):")


@router.message(ContentStates.file)
async def content_get_text(message: Message, state: FSMContext):
    await state.update_data(file_id=None, body_text=message.text or "")
    await state.set_state(ContentStates.caption)
    await message.answer("Qisqacha tavsif kiriting (bo'lmasa \"-\" yuboring):")


@router.message(ContentStates.caption)
async def content_finish(message: Message, state: FSMContext, bot: Bot):
    caption = "" if message.text.strip() == "-" else message.text.strip()
    data = await state.get_data()
    if data.get("file_id") is None and data.get("body_text"):
        caption = data["body_text"] + ("\n\n" + caption if caption else "")

    code = data["section"]
    meta = await sec.by_code(code)
    await db.add_content(code, data["title"], data.get("file_id"), caption, meta["min_tariff"])
    await state.clear()
    await message.answer("✅ Qo'shildi.", reply_markup=kb.admin_main_menu())

    await notify_new_item(
        bot,
        min_tariff=meta["min_tariff"],
        full_text=(
            f"🆕 <b>{meta['title']}</b> bo'limiga yangi material qo'shildi:\n\n"
            f"<b>{data['title']}</b>\n\n"
            f"Ko'rish uchun \"{meta['title']}\" bo'limiga kiring."
        ),
        teaser_text=(
            f"🔔 <b>{meta['title']}</b> bo'limiga yangi material qo'shildi:\n\n"
            f"<b>{data['title']}</b>\n\n"
            f"Materialning o'zi faqat obunachilarga ochiladi."
        ),
    )


async def notify_new_item(bot: Bot, min_tariff: str, full_text: str, teaser_text: str):
    """Kirish huquqi borlarga to'liq xabar, qolganlarga faqat qisqa eslatma.

    Obunasi yo'q foydalanuvchi ham botda nima bo'layotganini bilib turadi,
    lekin materialning o'zi va signal raqamlari unga ko'rinmaydi.
    """
    for telegram_id, tariff in await db.get_users_with_tariff():
        text = full_text if sec.has_access(tariff, min_tariff) else teaser_text
        try:
            await bot.send_message(telegram_id, text, parse_mode="HTML", protect_content=True)
        except Exception:
            pass


# =====================================================================
# 2-BO'LIM: TO'LOV TIZIMI
# =====================================================================

@router.callback_query(F.data == "pay:prices")
async def show_prices_menu(callback: CallbackQuery):
    rows = await db.get_all_prices()
    current = "\n".join(
        f"• {TARIFF_NAMES.get(r['tariff_code'], r['tariff_code'])} "
        f"{PERIOD_NAMES.get(r['period'], r['period'])}: {r['price']:.0f} {r['currency']}"
        for r in rows
    )
    await callback.message.answer(
        f"Hozirgi narxlar:\n{current}\n\nO'zgartirmoqchi bo'lganingizni tanlang:",
        reply_markup=kb.prices_edit_keyboard(),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("editprice:"))
async def edit_price_start(callback: CallbackQuery, state: FSMContext):
    _, tariff_code, period = callback.data.split(":")
    await state.update_data(tariff_code=tariff_code, period=period)
    await state.set_state(PriceEditStates.waiting_value)
    await callback.message.answer(
        f"{TARIFF_NAMES[tariff_code]} — {PERIOD_NAMES[period]} uchun yangi narxni kiriting "
        f"(faqat raqam, masalan 150000):"
    )
    await callback.answer()


@router.message(PriceEditStates.waiting_value)
async def edit_price_save(message: Message, state: FSMContext):
    try:
        price = float(message.text.strip().replace(" ", "").replace(",", "."))
    except ValueError:
        await message.answer("Narxni raqam ko'rinishida kiriting. Masalan: 150000")
        return
    data = await state.get_data()
    await db.set_price(data["tariff_code"], data["period"], price)
    await state.clear()
    await message.answer("✅ Narx yangilandi.", reply_markup=kb.admin_main_menu())


async def _show_methods(target):
    methods = await db.get_payment_methods()
    if methods:
        text = "💳 <b>To'lov usullari</b>\n\nFoydalanuvchi to'lov paytida shulardan birini tanlaydi."
    else:
        text = (
            "💳 <b>To'lov usullari</b>\n\n"
            "Hozircha birorta usul qo'shilmagan. Kamida bittasini qo'shing — "
            "aks holda foydalanuvchi to'lov qila olmaydi."
        )
    await target.answer(
        text, reply_markup=kb.payment_methods_admin_keyboard(methods), parse_mode="HTML"
    )


@router.callback_query(F.data == "pay:methods")
async def payment_methods_menu(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await _show_methods(callback.message)
    await callback.answer()


@router.callback_query(F.data.startswith("paymshow:"))
async def payment_method_show(callback: CallbackQuery):
    m = await db.get_payment_method(int(callback.data.split(":")[1]))
    if not m:
        await callback.answer("Topilmadi.", show_alert=True)
        return
    await callback.message.answer(
        f"💳 <b>{escape(m['title'])}</b>\n\n<code>{escape(m['details'])}</code>",
        parse_mode="HTML",
    )
    await callback.answer()


@router.callback_query(F.data.startswith("paymdel:"))
async def payment_method_delete(callback: CallbackQuery):
    m = await db.get_payment_method(int(callback.data.split(":")[1]))
    if not m:
        await callback.answer("Allaqachon o'chirilgan.", show_alert=True)
        return
    await db.delete_payment_method(m["id"])
    await callback.answer(f"«{m['title']}» o'chirildi")
    await callback.message.edit_reply_markup(
        reply_markup=kb.payment_methods_admin_keyboard(await db.get_payment_methods())
    )


@router.callback_query(F.data == "paymadd")
async def payment_method_add(callback: CallbackQuery, state: FSMContext):
    await state.set_state(PaymentMethodStates.title)
    await callback.message.answer(
        "Usul nomini yozing — foydalanuvchi ro'yxatda shuni ko'radi.\n\n"
        "Masalan:\n"
        "• <code>Humo — Kapitalbank</code>\n"
        "• <code>Click</code>\n"
        "• <code>USDT (TRC20)</code>\n\n"
        "Bekor qilish: /bekor",
        parse_mode="HTML",
    )
    await callback.answer()


@router.message(PaymentMethodStates.title)
async def payment_method_title(message: Message, state: FSMContext):
    await state.update_data(title=message.text.strip())
    await state.set_state(PaymentMethodStates.details)
    await message.answer(
        "Endi rekvizitni yozing — foydalanuvchi to'lash uchun aynan shuni ko'radi "
        "va ustiga bosib nusxalaydi.\n\n"
        "Karta uchun:\n<code>8600 1234 5678 9012\nDiyorbek D.</code>\n\n"
        "Kripto uchun faqat hamyon manzilini yozing:\n"
        "<code>TXYZa1b2c3d4e5f6g7h8i9j0klmnopqrs</code>",
        parse_mode="HTML",
    )


@router.message(PaymentMethodStates.details)
async def payment_method_details(message: Message, state: FSMContext):
    data = await state.get_data()
    await db.add_payment_method(data["title"], message.text.strip())
    await state.clear()
    await message.answer(f"✅ «{data['title']}» qo'shildi.")
    await _show_methods(message)


# =====================================================================
# 3-BO'LIM: OBUNALAR
# =====================================================================

@router.callback_query(F.data == "sub:pending")
async def pending_payments(callback: CallbackQuery):
    await callback.message.answer(
        "Yangi to'lov cheki kelganda avtomatik shu yerga tasdiqlash tugmalari bilan tushadi."
    )
    await callback.answer()


@router.callback_query(F.data.startswith("pay_approve:"))
async def approve_payment(callback: CallbackQuery, bot: Bot):
    payment_id = int(callback.data.split(":")[1])
    payment = await db.get_payment(payment_id)
    if not payment or payment["status"] != "pending":
        await callback.answer("Bu so'rov allaqachon ko'rib chiqilgan.", show_alert=True)
        return

    await db.update_payment_status(payment_id, "approved")
    await db.create_or_extend_subscription(
        payment["user_id"], payment["tariff_code"], payment["period"]
    )
    telegram_id = await db.get_telegram_id_by_user_id(payment["user_id"])

    await callback.message.edit_caption(caption=callback.message.caption + "\n\n✅ TASDIQLANDI")
    await callback.answer("Tasdiqlandi ✅")

    if telegram_id:
        try:
            await bot.send_message(
                telegram_id,
                f"✅ To'lovingiz tasdiqlandi!\n"
                f"Tarif: {TARIFF_NAMES[payment['tariff_code']]} — "
                f"{PERIOD_NAMES[payment['period']]}\n"
                f"Obunangiz faollashtirildi. /obunam"
            )
        except Exception:
            pass


@router.callback_query(F.data.startswith("pay_reject:"))
async def reject_payment(callback: CallbackQuery, bot: Bot):
    payment_id = int(callback.data.split(":")[1])
    payment = await db.get_payment(payment_id)
    if not payment or payment["status"] != "pending":
        await callback.answer("Bu so'rov allaqachon ko'rib chiqilgan.", show_alert=True)
        return

    await db.update_payment_status(payment_id, "rejected")
    telegram_id = await db.get_telegram_id_by_user_id(payment["user_id"])

    await callback.message.edit_caption(caption=callback.message.caption + "\n\n❌ RAD ETILDI")
    await callback.answer("Rad etildi")

    if telegram_id:
        try:
            await bot.send_message(
                telegram_id,
                "❌ To'lov chekingiz tasdiqlanmadi. Iltimos, admin bilan bog'laning."
            )
        except Exception:
            pass


# ---------- qo'lda obuna berish ----------

@router.callback_query(F.data == "sub:grant")
async def grant_start(callback: CallbackQuery, state: FSMContext):
    await state.update_data(mode="grant")
    await state.set_state(GrantSubStates.waiting_user_id)
    await callback.message.answer("Foydalanuvchining Telegram ID raqamini kiriting:")
    await callback.answer()


@router.callback_query(F.data == "sub:check")
async def check_start(callback: CallbackQuery, state: FSMContext):
    await state.update_data(mode="check")
    await state.set_state(GrantSubStates.waiting_user_id)
    await callback.message.answer("Tekshiriladigan foydalanuvchining Telegram ID raqamini kiriting:")
    await callback.answer()


@router.message(GrantSubStates.waiting_user_id)
async def grant_get_user(message: Message, state: FSMContext):
    try:
        telegram_id = int(message.text.strip())
    except ValueError:
        await message.answer("ID faqat raqamlardan iborat bo'lishi kerak.")
        return
    user = await db.get_user_by_telegram_id(telegram_id)
    if not user:
        await message.answer("Bunday foydalanuvchi topilmadi (u hali /start bosmagan).")
        return

    data = await state.get_data()
    if data.get("mode") == "check":
        sub = await db.get_active_subscription(user["id"])
        await state.clear()
        if not sub:
            await message.answer(
                f"👤 {user['full_name']}\nObuna: yo'q", reply_markup=kb.admin_main_menu()
            )
        else:
            await message.answer(
                f"👤 {user['full_name']}\n"
                f"📦 Tarif: {TARIFF_NAMES.get(sub['tariff_code'], sub['tariff_code'])}\n"
                f"⏳ Tugash: {sub['end_date'][:16].replace('T', ' ')}\n"
                f"Holat: {sub['status']}",
                reply_markup=kb.admin_main_menu(),
            )
        return

    await state.update_data(user_id=user["id"], telegram_id=telegram_id)
    await state.set_state(GrantSubStates.waiting_tariff)
    await message.answer(
        f"👤 {user['full_name']}\n\nQaysi tarifni beramiz?",
        reply_markup=kb.tariff_pick_keyboard("granttariff", "Tarif"),
    )


@router.callback_query(GrantSubStates.waiting_tariff, F.data.startswith("granttariff:"))
async def grant_pick_period(callback: CallbackQuery, state: FSMContext):
    tariff_code = callback.data.split(":")[1]
    await callback.message.edit_text(
        f"{TARIFF_NAMES[tariff_code]} — muddatni tanlang:",
        reply_markup=kb.grant_period_keyboard(tariff_code),
    )
    await callback.answer()


@router.callback_query(GrantSubStates.waiting_tariff, F.data.startswith("grantperiod:"))
async def grant_finish(callback: CallbackQuery, state: FSMContext, bot: Bot):
    _, tariff_code, period = callback.data.split(":")
    data = await state.get_data()
    await db.create_or_extend_subscription(data["user_id"], tariff_code, period)
    await state.clear()

    await callback.message.edit_text(
        f"✅ Obuna berildi: {TARIFF_NAMES[tariff_code]} — {PERIOD_NAMES[period]}"
    )
    await callback.answer()
    try:
        await bot.send_message(
            data["telegram_id"],
            f"🎁 Sizga obuna faollashtirildi!\n"
            f"Tarif: {TARIFF_NAMES[tariff_code]} — {PERIOD_NAMES[period]}\n/obunam"
        )
    except Exception:
        pass


# ---------- qoidabuzarlik ----------

@router.callback_query(F.data == "sub:violation")
async def violation_start(callback: CallbackQuery, state: FSMContext):
    await state.set_state(ViolationStates.waiting_user_id)
    await callback.message.answer("Qoidabuzar foydalanuvchining Telegram ID raqamini kiriting:")
    await callback.answer()


@router.message(ViolationStates.waiting_user_id)
async def violation_get_id(message: Message, state: FSMContext):
    try:
        telegram_id = int(message.text.strip())
    except ValueError:
        await message.answer("ID raqam bo'lishi kerak.")
        return
    user = await db.get_user_by_telegram_id(telegram_id)
    if not user:
        await message.answer("Bunday foydalanuvchi topilmadi.")
        return
    await state.update_data(telegram_id=telegram_id, user_id=user["id"])
    await state.set_state(ViolationStates.waiting_note)
    await message.answer("Qoidabuzarlik sababini qisqacha yozing (masalan: kontent tarqatgan):")


@router.message(ViolationStates.waiting_note)
async def violation_finish(message: Message, state: FSMContext, bot: Bot):
    data = await state.get_data()
    await db.add_violation(data["user_id"], message.text.strip())
    await db.pause_subscription(data["user_id"])
    await state.clear()

    await message.answer(
        "✅ Qoidabuzarlik qayd etildi va obuna vaqtincha to'xtatildi.",
        reply_markup=kb.admin_main_menu(),
    )
    try:
        await bot.send_message(
            data["telegram_id"],
            "❗️❗️ <b>Diqqat!</b> ❗️❗️\n\n"
            "Siz bizning qoidalarimizni buzmoqdasiz. "
            "Shu sababli tarifingizdagi obuna vaqtincha to'xtatildi.",
            parse_mode="HTML",
        )
    except Exception:
        pass


# =====================================================================
# FAQAT BUYRUQ ORQALI: YANGI BO'LIM QO'SHISH
# (ataylab tugma qilinmagan — kundalik ish emas)
# =====================================================================

@router.message(Command("yangi_bolim"))
async def new_section_start(message: Message, state: FSMContext):
    await state.clear()
    await state.set_state(NewSectionStates.title)
    await message.answer(
        "🆕 Foydalanuvchilarga yangi bo'lim qo'shamiz.\n\n"
        "Bo'lim nomini kiriting — u foydalanuvchida tugma bo'lib chiqadi.\n"
        "Masalan: <code>📊 Bozor tahlili</code>\n\n"
        "Bekor qilish: /bekor",
        parse_mode="HTML",
    )


@router.message(NewSectionStates.title)
async def new_section_title(message: Message, state: FSMContext):
    title = message.text.strip()
    existing = await sec.all_sections()
    if any(m["title"] == title for m in existing.values()):
        await message.answer("Bunday nomli bo'lim allaqachon bor. Boshqa nom kiriting:")
        return
    await state.update_data(title=title)
    await state.set_state(NewSectionStates.tariff)
    await message.answer(
        f"«{title}» bo'limi qaysi tarifdan boshlab ochilsin?",
        reply_markup=kb.tariff_pick_keyboard("sectiontariff", "Minimal daraja"),
    )


@router.callback_query(NewSectionStates.tariff, F.data.startswith("sectiontariff:"))
async def new_section_finish(callback: CallbackQuery, state: FSMContext):
    min_tariff = callback.data.split(":")[1]
    data = await state.get_data()

    code = f"custom{int(time.time())}"
    await db.add_section(code, data["title"], min_tariff)
    await state.clear()

    await callback.message.edit_text(
        f"✅ «{data['title']}» bo'limi qo'shildi.\n"
        f"Minimal daraja: {TARIFF_NAMES[min_tariff]}\n\n"
        f"Endi u foydalanuvchilarda tugma bo'lib chiqadi. Unga narsa joylash uchun "
        f"«{kb.ADMIN_POST}» bo'limiga kiring."
    )
    await callback.answer()


# =====================================================================
# FAQAT BUYRUQ ORQALI: UMUMIY XABAR
# =====================================================================

@router.message(Command("xabar"))
async def broadcast_start(message: Message, state: FSMContext):
    await state.clear()
    await state.set_state(BroadcastStates.waiting_message)
    await message.answer(
        "Barcha foydalanuvchilarga yuboriladigan xabarni yozing.\nBekor qilish: /bekor"
    )


@router.message(BroadcastStates.waiting_message)
async def broadcast_send(message: Message, state: FSMContext, bot: Bot):
    await state.clear()
    sent, failed = 0, 0
    for tid in await db.get_all_user_telegram_ids():
        try:
            await bot.send_message(tid, message.text)
            sent += 1
        except Exception:
            failed += 1
    await message.answer(
        f"📢 Yuborildi.\n✅ Yetkazildi: {sent}\n❌ Xato: {failed}",
        reply_markup=kb.admin_main_menu(),
    )
