"""Bot va API'ni bitta jarayonda ishga tushiradi.

Serverda ikkita alohida xizmat saqlab o'tirmaslik uchun: bitta buyruq,
bitta baza fayli, bitta jurnal.

    python3 run_all.py

Faqat botni ishga tushirish uchun main.py, faqat API uchun
`uvicorn api.main:app` ishlatiladi.
"""
import asyncio
import logging
import os

import uvicorn

from main import main as run_bot

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
logger = logging.getLogger(__name__)


def api_port() -> int:
    """Qaysi portda tinglash kerakligini aniqlaydi.

    Railway, Render va shunga o'xshash xizmatlar portni PORT o'zgaruvchisi
    orqali beradi va boshqa portda tinglasak, xizmatni "o'lik" deb biladi.
    Shuning uchun avval PORT, keyin API_PORT, oxirida 8000.
    """
    for name in ("PORT", "API_PORT"):
        value = os.getenv(name)
        if value and value.strip().isdigit():
            return int(value.strip())
    return 8000


async def run_api():
    port = api_port()
    logger.info(f"API {port}-portda tinglaydi.")
    config = uvicorn.Config(
        "api.main:app",
        host=os.getenv("API_HOST", "0.0.0.0"),
        port=port,
        log_level="info",
        proxy_headers=True,          # xizmat oldida nginx/load balancer turadi
        forwarded_allow_ips="*",
    )
    await uvicorn.Server(config).serve()


async def run_bot_forever():
    """Botni kuzatib turadi va yiqilsa qayta ko'taradi.

    Muhim: bot Telegram'ga ulana olmasa ham SAYT ISHLAB TURISHI kerak.
    Aks holda Telegram tomonidagi bir daqiqalik uzilish butun saytni
    o'chirib qo'yardi.
    """
    delay = 5
    while True:
        try:
            await run_bot()
            logger.warning("Bot to'xtadi. Qayta ishga tushiriladi...")
        except asyncio.CancelledError:
            raise
        except Exception as e:
            logger.error(f"Bot xatosi: {type(e).__name__}: {e}")
            logger.info(f"{delay} soniyadan keyin qayta urinib ko'riladi. "
                        f"Sayt API'si ishlashda davom etmoqda.")
        await asyncio.sleep(delay)
        delay = min(delay * 2, 300)   # 5s, 10s, 20s ... 5 daqiqagacha


async def main():
    logger.info("Bot va API birgalikda ishga tushmoqda...")
    # return_exceptions bo'lmasa, bittasining xatosi ikkinchisini ham yiqitadi
    await asyncio.gather(run_bot_forever(), run_api(), return_exceptions=True)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("To'xtatildi.")
