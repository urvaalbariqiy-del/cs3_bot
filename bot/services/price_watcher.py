"""
Narx kuzatish xizmati.
Binance'ning ochiq (public, kalitsiz) WebSocket oqimiga ulanadi va barcha
faol/kutilayotgan signallar coinlarining narxini real vaqtda kuzatib boradi.

Mantiq (faqat spot / long signal uchun):
- pending -> active   : narx entry darajasini KESIB o'tganda. Signal uchun birinchi narx
                         kelganda uning entry'dan qaysi tomonda ekanini aniqlab, bazaga
                         yozib qo'yamiz ('above' yoki 'below'). Keyin faqat teskari
                         tomonga o'tish faollashtiradi:
                           above (narx entry'dan yuqorida boshlandi) -> price <= entry
                           below (narx entry'dan pastda boshlandi)   -> price >= entry
                         Shu sababli entry joriy narxdan pastga qo'yilganda signal
                         darhol "faol" bo'lib qolmaydi.
- active -> tp1_hit   : narx TP1 darajasiga yetganda (signal hali "faol" hisoblanadi, TP2 kutilmoqda)
- tp1_hit -> tp2_hit  : narx TP2 darajasiga yetganda (signal to'liq yopiladi)
- active/tp1_hit -> stopped : narx Stop darajasiga tushib ketganda (signal yopiladi)

Eslatma: bu soddalashtirilgan mantiq. Real loyihada tick-by-tick tarixni
saqlab, TP1/TP2/Stop qaysi birinchi urilganini aniqroq hisoblash tavsiya etiladi.
"""
import asyncio
import json
import logging

import websockets
from aiogram import Bot

from bot import database as db
from bot.config import BINANCE_WS_BASE

logger = logging.getLogger(__name__)

STATUS_TEXT = {
    "active": "✅ Signal faollashdi! Narx kirish nuqtasiga yetdi.",
    "tp1_hit": "🎯 TP1 (birinchi profit) olindi!",
    "tp2_hit": "🎯🎯 TP2 (ikkinchi profit) olindi! Signal to'liq yopildi.",
    "stopped": "🛑 Stop ishga tushdi. Signal yopildi.",
}


async def notify_all(bot: Bot, coin: str, status_key: str):
    text = f"💠 <b>{coin}</b>\n{STATUS_TEXT[status_key]}"
    user_ids = await db.get_all_user_telegram_ids()
    for tid in user_ids:
        try:
            await bot.send_message(tid, text, parse_mode="HTML", protect_content=True)
        except Exception:
            pass


async def evaluate_signal(bot: Bot, signal, current_price: float):
    sid = signal["id"]
    status = signal["status"]

    if status == "pending":
        entry = signal["entry"]
        side = signal["entry_side"]

        if side is None:
            # Bu signal uchun birinchi narx: entry'ga qaysi tomondan yaqinlashayotganini aniqlaymiz
            if current_price == entry:
                # narx aynan entry darajasida - darhol faollashtiramiz
                await db.update_signal_status(sid, "active")
                await notify_all(bot, signal["coin"], "active")
                return
            side = "above" if current_price > entry else "below"
            await db.set_signal_entry_side(sid, side)
            return

        reached = current_price <= entry if side == "above" else current_price >= entry
        if reached:
            await db.update_signal_status(sid, "active")
            await notify_all(bot, signal["coin"], "active")
        return

    if status in ("active", "tp1_hit"):
        # avval stopni tekshiramiz (xavfsizlik ustuvor)
        if current_price <= signal["stop"]:
            await db.update_signal_status(sid, "stopped")
            await notify_all(bot, signal["coin"], "stopped")
            return

        if status == "active" and current_price >= signal["tp1"]:
            await db.update_signal_status(sid, "tp1_hit")
            await notify_all(bot, signal["coin"], "tp1_hit")
            status = "tp1_hit"

        if status == "tp1_hit" and current_price >= signal["tp2"]:
            await db.update_signal_status(sid, "tp2_hit")
            await notify_all(bot, signal["coin"], "tp2_hit")


async def run_price_watcher(bot: Bot):
    """Asosiy sikl: har 15 soniyada kuzatilishi kerak bo'lgan signallar ro'yxatini
    yangilaydi va WebSocket ulanishini shunga moslab qayta quradi."""
    current_symbols = set()
    ws_task = None

    async def stream_handler(symbols: set):
        streams = "/".join(f"{s.lower()}@trade" for s in symbols)
        url = BINANCE_WS_BASE + streams
        try:
            async with websockets.connect(url, ping_interval=20) as ws:
                logger.info(f"Binance WS ulandi: {symbols}")
                async for raw in ws:
                    data = json.loads(raw)
                    payload = data.get("data", {})
                    symbol = payload.get("s")
                    price = payload.get("p")
                    if not symbol or price is None:
                        continue
                    price = float(price)

                    signals = await db.get_watchable_signals()
                    for s in signals:
                        if s["coin"] == symbol:
                            await evaluate_signal(bot, s, price)
        except Exception as e:
            logger.warning(f"WebSocket xatosi: {e}. 5 soniyadan keyin qayta ulanadi.")
            await asyncio.sleep(5)

    while True:
        signals = await db.get_watchable_signals()
        symbols = {s["coin"] for s in signals}

        if symbols and symbols != current_symbols:
            if ws_task and not ws_task.done():
                ws_task.cancel()
            current_symbols = symbols
            ws_task = asyncio.create_task(stream_handler(symbols))
        elif not symbols and ws_task and not ws_task.done():
            ws_task.cancel()
            current_symbols = set()

        await asyncio.sleep(15)
