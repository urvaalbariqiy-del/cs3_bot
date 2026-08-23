import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.types import (
    BotCommand, BotCommandScopeDefault, BotCommandScopeChat,
)

from bot.config import BOT_TOKEN, ADMIN_IDS
from bot.database import init_db
from bot.handlers import user, admin
from bot.services.price_watcher import run_price_watcher
from bot.services.subscription_checker import run_subscription_checker

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
logger = logging.getLogger(__name__)


# Yozish maydonidagi ☰ menyu. Tugmalarga aloqasi yo'q - bu tezkor yo'l.
USER_COMMANDS = [
    BotCommand(command="start", description="Boshlash / asosiy menyu"),
    BotCommand(command="obuna", description="Obuna olish"),
    BotCommand(command="obunam", description="Obuna muddatim"),
]

ADMIN_COMMANDS = [
    BotCommand(command="start", description="Boshlash / asosiy menyu"),
    BotCommand(command="joylash", description="Bo'limlarga joylash"),
    BotCommand(command="tolov", description="To'lov tizimi"),
    BotCommand(command="obunalar", description="Obunalarni boshqarish"),
    BotCommand(command="yangi_bolim", description="Foydalanuvchilarga yangi bo'lim qo'shish"),
    BotCommand(command="xabar", description="Hammaga umumiy xabar"),
    BotCommand(command="bekor", description="Joriy amalni bekor qilish"),
]


async def setup_commands(bot: Bot):
    await bot.set_my_commands(USER_COMMANDS, scope=BotCommandScopeDefault())
    for admin_id in ADMIN_IDS:
        try:
            await bot.set_my_commands(ADMIN_COMMANDS, scope=BotCommandScopeChat(chat_id=admin_id))
        except Exception as e:
            logger.warning(f"Admin {admin_id} uchun buyruqlar o'rnatilmadi: {e}")


# Dispatcher va routerlar modul darajasida, bir marta ulanadi.
# Bu muhim: bot uzilib qayta ko'tarilganda (run_all.py) routerni ikkinchi
# marta ulash "Router is already attached" xatosini berardi.
dp = Dispatcher()
dp.include_router(admin.router)   # admin avval — uning handlerlari ustun
dp.include_router(user.router)

_background_started = False


async def main():
    global _background_started

    if not BOT_TOKEN:
        raise RuntimeError("BOT_TOKEN .env faylida ko'rsatilmagan! .env.example'ga qarang.")

    bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))

    await init_db()
    logger.info("Ma'lumotlar bazasi tayyor.")

    # Fon jarayonlari faqat bir marta ishga tushadi — bot qayta ko'tarilganda
    # ular ikki nusxada ishlab, xabarni ikki marta yubormasligi uchun.
    if not _background_started:
        asyncio.create_task(run_price_watcher(bot))
        asyncio.create_task(run_subscription_checker(bot))
        _background_started = True
        logger.info("Narx kuzatish va obuna tekshirish xizmatlari ishga tushdi.")

    try:
        await bot.delete_webhook(drop_pending_updates=True)
        await setup_commands(bot)
        logger.info("Bot polling rejimida ishga tushdi.")
        await dp.start_polling(bot)
    finally:
        # Ulanish ochiq qolmasin — qayta urinishda yangisi ochiladi
        await bot.session.close()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Bot to'xtatildi.")
