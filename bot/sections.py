"""Bo'limlar bilan ishlash uchun umumiy yordamchi.

Ikki manba bor:
  1. config.SECTIONS  — kodda yozilgan asosiy 4 ta bo'lim
  2. bazadagi 'sections' jadvali — admin /yangi_bolim orqali qo'shganlari

Ikkalasini bir xil ko'rinishga keltirib beradi, shunda handler'lar
"bu asosiy bo'limmi yoki qo'shimchami" deb o'ylab o'tirmaydi.
"""
from bot import database as db
from bot.config import SECTIONS, TARIFF_LEVEL, TARIFF_NAMES, FREE_MODE


async def all_sections() -> dict:
    """{code: {"title", "min_tariff", "kind"}} — asosiy va qo'shimcha bo'limlar birga."""
    result = {code: dict(meta) for code, meta in SECTIONS.items()}
    for row in await db.get_custom_sections():
        result[row["code"]] = {
            "title": row["title"],
            "min_tariff": row["min_tariff"],
            "kind": "content",
        }
    return result


async def by_title(title: str):
    """Bosilgan tugma matni bo'yicha bo'limni topadi. -> (code, meta) yoki (None, None)"""
    for code, meta in (await all_sections()).items():
        if meta["title"] == title:
            return code, meta
    return None, None


async def by_code(code: str):
    return (await all_sections()).get(code)


def has_access(user_tariff: str | None, min_tariff: str) -> bool:
    """Foydalanuvchi tarifi bo'lim uchun yetarlimi.

    FREE_MODE yoqilgan bo'lsa hamma bo'lim hammaga ochiq - birinchi
    bosqichda maqsad auditoriya yig'ish. Tarif mantig'i esa joyida
    turibdi: FREE_MODE o'chirilishi bilan darhol kuchga kiradi.

    Aks holda yuqori daraja pastki darajalarning hamma bo'limini ochadi.
    """
    if FREE_MODE:
        return True
    if not user_tariff:
        return False
    return TARIFF_LEVEL.get(user_tariff, 0) >= TARIFF_LEVEL.get(min_tariff, 99)


def tariff_label(min_tariff: str) -> str:
    return TARIFF_NAMES.get(min_tariff, min_tariff)
