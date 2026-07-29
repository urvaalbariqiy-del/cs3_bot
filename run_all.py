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


async def run_api():
    config = uvicorn.Config(
        "api.main:app",
        host=os.getenv("API_HOST", "0.0.0.0"),
        port=int(os.getenv("API_PORT", "8000")),
        log_level="info",
    )
    await uvicorn.Server(config).serve()


async def main():
    logger.info("Bot va API birgalikda ishga tushmoqda...")
    await asyncio.gather(run_bot(), run_api())


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("To'xtatildi.")
