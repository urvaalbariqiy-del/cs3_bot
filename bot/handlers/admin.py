from aiogram import Router, F, Bot
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext

from bot import database as db
from bot import keyboards as kb
from bot.states import (
    SignalStates, ContentStates, PriceEditStates, BroadcastStates, ViolationStates,
)
from bot.config import ADMIN_IDS, TARIFF_NAMES, PERIOD_NAMES

router = Router()

# Ushbu routerdagi BARCHA handlerlar faqat ADMIN_IDS ichidagi foydalanuvchilar uchun ishlaydi.
# Bu aiogram'ning o'zining rasmiy filtr mexanizmi - har bir handlerni alohida
# himoyalash shart emas, chunki filtr butun routerga bir marta qo'llaniladi.
router.message.filter(F.from_user.id.in_(ADMIN_IDS))
router.callback_query.filter(F.from_user.id.in_(ADMIN_IDS))


@router.message(Command("panel"))
async def cmd_panel(message: Message):
    await message.answer("⚙️ Admin panel:", reply_markup=kb.admin_panel_keyboard())


@router.message(F.text == "⚙️ Admin panel")
async def open_panel(message: Message):
    await message.answer("⚙️ Admin panel:", reply_markup=kb.admin_panel_keyboard())


# ================= SIGNAL YARATISH =================

@router.callback_query(F.data == "admin:new_signal")
async def new_signal_start(callback: CallbackQuery, state: FSMContext):
    await state.set_state(SignalStates.coin)
    await callback.message.answer(
        "🟢 Yangi signal yaratish.\n\nCoin nomini kiriting (masalan: <code>BTCUSDT</code>):",
        parse_mode="HTML",
    )
    await callback.answer()


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
    data = await state.get_data()

    preview = (
        f"📋 <b>Signal ko'rinishi (preview):</b>\n\n"
        f"💠 <b>{data['coin']}</b>\n"
        f"🎯 Entry: {data['entry']}\n"
        f"🛑 Stop: {data['stop']}\n"
        f"🥇 TP1: {data['tp1']}\n"
        f"🥈 TP2: {data['tp2']}\n"
    )
    if comment:
        preview += f"\n📝 {comment}"

    await state.set_state(SignalStates.confirm)
    await message.answer(preview, reply_markup=kb.signal_preview_keyboard(), parse_mode="HTML")


@router.callback_query(SignalStates.confirm, F.data == "signal_confirm")
async def signal_confirm(callback: CallbackQuery, state: FSMContext, bot: Bot):
    data = await state.get_data()
    await db.create_signal(
        data["coin"], data["entry"], data["stop"], data["tp1"], data["tp2"], data.get("comment", "")
    )
    await state.clear()
    await callback.message.edit_text("✅ Signal muvaffaqiyatli joylandi va kuzatuv boshlandi.")
    await callback.answer()

    # Barcha faol obunachilarga signal haqida xabar (signalga kirish huquqi bo'lganlarga)
    text = (
        f"🆕 <b>Yangi signal joylandi!</b>\n\n"
        f"💠 {data['coin']}\n"
        f"Holat: ⏳ Kutilmoqda (narx entry nuqtasiga yetganda faollashadi)\n\n"
        f"\"📈 Signallar\" bo'limidan to'liq ma'lumotni ko'ring."
    )
    user_ids = await db.get_all_user_telegram_ids()
    for tid in user_ids:
        try:
            await bot.send_message(tid, text, parse_mode="HTML", protect_content=True)
        except Exception:
            pass


@router.callback_query(SignalStates.confirm, F.data == "signal_cancel")
async def signal_cancel(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.edit_text("❌ Signal bekor qilindi.")
    await callback.answer()


@router.callback_query(F.data == "admin:list_signals")
async def list_signals(callback: CallbackQuery):
    from bot.handlers.user import STATUS_LABELS
    signals = await db.get_recent_signals(limit=10)
    if not signals:
        await callback.message.answer("Hozircha signal yo'q.")
        await callback.answer()
        return
    for s in signals:
        await callback.message.answer(
            f"💠 {s['coin']} — {STATUS_LABELS.get(s['status'], s['status'])}\n"
            f"Entry: {s['entry']} | Stop: {s['stop']} | TP1: {s['tp1']} | TP2: {s['tp2']}"
        )
    await callback.answer()


# ================= TO'LOVLARNI TASDIQLASH =================

@router.callback_query(F.data == "admin:pending_payments")
async def pending_payments(callback: CallbackQuery):
    await callback.message.answer(
        "Yangi to'lovlar kelganda avtomatik shu yerga xabar va tugmalar bilan yuboriladi."
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
    await db.create_or_extend_subscription(payment["user_id"], payment["tariff_code"], payment["period"])

    telegram_id = await db.get_telegram_id_by_user_id(payment["user_id"])

    await callback.message.edit_caption(
        caption=callback.message.caption + "\n\n✅ TASDIQLANDI",
    )
    await callback.answer("Tasdiqlandi ✅")

    if telegram_id:
        try:
            await bot.send_message(
                telegram_id,
                f"✅ To'lovingiz tasdiqlandi!\n"
                f"Tarif: {TARIFF_NAMES[payment['tariff_code']]} — {PERIOD_NAMES[payment['period']]}\n"
                f"Obunangiz faollashtirildi."
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


# ================= NARXLARNI SOZLASH =================

@router.callback_query(F.data == "admin:prices")
async def show_prices_menu(callback: CallbackQuery):
    await callback.message.answer(
        "O'zgartirmoqchi bo'lgan tarif/muddatni tanlang:", reply_markup=kb.prices_edit_keyboard()
    )
    await callback.answer()


@router.callback_query(F.data.startswith("editprice:"))
async def edit_price_start(callback: CallbackQuery, state: FSMContext):
    _, tariff_code, period = callback.data.split(":")
    await state.update_data(tariff_code=tariff_code, period=period)
    await state.set_state(PriceEditStates.waiting_value)
    await callback.message.answer(
        f"{TARIFF_NAMES[tariff_code]} — {PERIOD_NAMES[period]} uchun yangi narxni kiriting "
        f"(faqat raqam, masalan 150000). Xohlasangiz to'lov usuli tavsifini ham qo'shimcha "
        f"qatorda yozing (masalan karta raqami)."
    )
    await callback.answer()


@router.message(PriceEditStates.waiting_value)
async def edit_price_save(message: Message, state: FSMContext):
    lines = message.text.strip().split("\n", 1)
    try:
        price = float(lines[0].replace(",", "."))
    except ValueError:
        await message.answer("Narxni raqam ko'rinishida kiriting. Masalan: 150000")
        return
    payment_info = lines[1].strip() if len(lines) > 1 else None

    data = await state.get_data()
    await db.set_price(data["tariff_code"], data["period"], price, payment_info)
    await state.clear()
    await message.answer("✅ Narx yangilandi.")


# ================= KONTENT QO'SHISH =================

@router.callback_query(F.data == "admin:add_content")
async def add_content_start(callback: CallbackQuery, state: FSMContext):
    await state.set_state(ContentStates.choosing_type)
    await callback.message.answer("Kontent turini tanlang:", reply_markup=kb.content_type_keyboard())
    await callback.answer()


@router.callback_query(ContentStates.choosing_type, F.data.startswith("content_type:"))
async def add_content_type_chosen(callback: CallbackQuery, state: FSMContext):
    content_type = callback.data.split(":")[1]
    await state.update_data(content_type=content_type)
    await state.set_state(ContentStates.title)
    await callback.message.answer("Sarlavha (nomi)ni kiriting:")
    await callback.answer()


@router.message(ContentStates.title)
async def add_content_title(message: Message, state: FSMContext):
    await state.update_data(title=message.text.strip())
    await state.set_state(ContentStates.file)
    data = await state.get_data()
    if data["content_type"] == "video":
        await message.answer("Video faylni yuboring:")
    else:
        await message.answer("Fayl yuboring (PDF/dokument) yoki matn ko'rinishida yozib yuboring:")


@router.message(ContentStates.file, F.video)
async def add_content_video(message: Message, state: FSMContext):
    await state.update_data(file_id=message.video.file_id)
    await state.set_state(ContentStates.caption)
    await message.answer("Qisqacha tavsif (caption) kiriting (bo'lmasa \"-\" yuboring):")


@router.message(ContentStates.file, F.document)
async def add_content_document(message: Message, state: FSMContext):
    await state.update_data(file_id=message.document.file_id)
    await state.set_state(ContentStates.caption)
    await message.answer("Qisqacha tavsif (caption) kiriting (bo'lmasa \"-\" yuboring):")


@router.message(ContentStates.file)
async def add_content_text(message: Message, state: FSMContext):
    # strategiya matn ko'rinishida ham bo'lishi mumkin
    await state.update_data(file_id=None, caption_text=message.text)
    await state.set_state(ContentStates.caption)
    await message.answer("Qisqacha tavsif (caption) kiriting (bo'lmasa \"-\" yuboring):")


@router.message(ContentStates.caption)
async def add_content_caption(message: Message, state: FSMContext):
    caption = "" if message.text.strip() == "-" else message.text.strip()
    data = await state.get_data()
    if data.get("file_id") is None and data.get("caption_text"):
        caption = data["caption_text"] + ("\n\n" + caption if caption else "")
    await state.update_data(caption=caption)
    await state.set_state(ContentStates.tariff)
    await message.answer(
        "Bu kontentga kirish uchun minimal talab qilinadigan tarifni tanlang:",
        reply_markup=kb.content_tariff_keyboard(),
    )


@router.callback_query(ContentStates.tariff, F.data.startswith("content_tariff:"))
async def add_content_finish(callback: CallbackQuery, state: FSMContext):
    tariff_code = callback.data.split(":")[1]
    data = await state.get_data()
    await db.add_content(
        data["content_type"], data["title"], data.get("file_id"), data.get("caption", ""), tariff_code
    )
    await state.clear()
    await callback.message.edit_text("✅ Kontent muvaffaqiyatli qo'shildi.")
    await callback.answer()


# ================= BROADCAST =================

@router.callback_query(F.data == "admin:broadcast")
async def broadcast_start(callback: CallbackQuery, state: FSMContext):
    await state.set_state(BroadcastStates.waiting_message)
    await callback.message.answer("Barcha foydalanuvchilarga yuboriladigan xabar matnini kiriting:")
    await callback.answer()


@router.message(BroadcastStates.waiting_message)
async def broadcast_send(message: Message, state: FSMContext, bot: Bot):
    await state.clear()
    user_ids = await db.get_all_user_telegram_ids()
    sent, failed = 0, 0
    for tid in user_ids:
        try:
            await bot.send_message(tid, message.text)
            sent += 1
        except Exception:
            failed += 1
    await message.answer(f"📢 Xabar yuborildi.\n✅ Yetkazildi: {sent}\n❌ Xato: {failed}")


# ================= QOIDABUZARLIK =================

@router.callback_query(F.data == "admin:violation")
async def violation_start(callback: CallbackQuery, state: FSMContext):
    await state.set_state(ViolationStates.waiting_user_id)
    await callback.message.answer(
        "Qoidabuzar foydalanuvchining Telegram ID raqamini kiriting:"
    )
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

    await message.answer("✅ Qoidabuzarlik qayd etildi va tarif vaqtincha to'xtatildi.")

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
