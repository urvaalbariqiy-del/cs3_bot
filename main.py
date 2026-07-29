import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

from bot.config import BOT_TOKEN
from bot.database import init_db
from bot.handlers import user, admin
from bot.services.price_watcher import run_price_watcher
from bot.services.subscription_checker import run_subscription_checker

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
logger = logging.getLogger(__name__)


async def main():
    if not BOT_TOKEN:
        raise RuntimeError("BOT_TOKEN .env faylida ko'rsatilmagan! .env.example'ga qarang.")

    bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    dp = Dispatcher()

    # admin.py handlerlari user.py'dagi umumiy matnlar bilan to'qnashmasligi uchun
    # avval admin, keyin user routerini ulaymiz
    dp.include_router(admin.router)
    dp.include_router(user.router)

    await init_db()
    logger.info("Ma'lumotlar bazasi tayyor.")

    # Fon jarayonlarini alohida task sifatida ishga tushiramiz
    asyncio.create_task(run_price_watcher(bot))
    asyncio.create_task(run_subscription_checker(bot))
    logger.info("Narx kuzatish va obuna tekshirish xizmatlari ishga tushdi.")

    await bot.delete_webhook(drop_pending_updates=True)
    logger.info("Bot polling rejimida ishga tushdi.")
    await dp.start_polling(bot)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Bot to'xtatildi.")
