"""
Obuna muddatlarini kuzatuvchi fon jarayoni.
Belgilangan intervalda ishga tushib:
1. Tugashi yaqinlashgan obunalarga eslatma yuboradi
2. Muddati tugagan obunalarni avtomatik 'expired' holatiga o'tkazadi
"""
import asyncio
import logging

from aiogram import Bot

from bot import database as db
from bot.config import REMINDER_HOURS_BEFORE, SUBSCRIPTION_CHECK_INTERVAL, TARIFF_NAMES

logger = logging.getLogger(__name__)


async def run_subscription_checker(bot: Bot):
    while True:
        try:
            # 1) Tugashi yaqinlashganlarga eslatma
            expiring = await db.get_expiring_subscriptions(REMINDER_HOURS_BEFORE)
            for sub in expiring:
                try:
                    await bot.send_message(
                        sub["telegram_id"],
                        f"⏰ Eslatma: sizning <b>{TARIFF_NAMES[sub['tariff_code']]}</b> obunangiz "
                        f"tez orada tugaydi.\n\n"
                        f"Uzaytirish uchun to'lovni amalga oshirib, chekni botga yuboring.",
                        parse_mode="HTML",
                    )
                except Exception:
                    pass
                await db.mark_reminder_sent(sub["id"])

            # 2) Muddati tugaganlarni yopish
            expired = await db.get_newly_expired_subscriptions()
            for sub in expired:
                await db.expire_subscription(sub["id"])
                try:
                    await bot.send_message(
                        sub["telegram_id"],
                        f"❌ Sizning <b>{TARIFF_NAMES[sub['tariff_code']]}</b> obunangiz muddati tugadi.\n"
                        f"To'lov amalga oshmagani sababli kirish huquqi to'xtatildi.\n\n"
                        f"Davom ettirish uchun \"💳 Obuna sotib olish\" bo'limidan foydalaning.",
                        parse_mode="HTML",
                    )
                except Exception:
                    pass

        except Exception as e:
            logger.warning(f"Obuna tekshiruvida xato: {e}")

        await asyncio.sleep(SUBSCRIPTION_CHECK_INTERVAL)
