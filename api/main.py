"""Cryptospot 3 — sayt va ilova uchun API.

Bot bilan bitta bazani baham ko'radi: saytda ko'rinadigan signal, obuna va
tarif — botdagining aynan o'zi. Ikkinchi baza ham, ikkinchi haqiqat ham yo'q.

Alohida ishga tushirish:
    uvicorn api.main:app --host 0.0.0.0 --port 8000

Bot bilan birga (bitta jarayonda):
    python3 run_all.py
"""
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from bot.config import CORS_ORIGINS
from bot.database import init_db
from api.routes import router


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    yield


app = FastAPI(
    title="Cryptospot 3 API",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=False,   # Authorization sarlavhasi ishlatiladi, cookie emas
    allow_methods=["GET", "POST"],
    allow_headers=["Authorization", "Content-Type"],
)

app.include_router(router)


@app.get("/health")
async def health():
    return {"ok": True, "service": "cryptospot3-api"}
