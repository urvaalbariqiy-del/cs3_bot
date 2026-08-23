# Cryptospot 3% — bot, sayt va API

Bitta loyiha, bitta baza. Uch qismdan iborat:

```
cs3_bot/
├── bot/        Telegram bot (aiogram)
├── api/        Sayt va ilova uchun API (FastAPI)
├── web/        Landing sahifa + shaxsiy kabinet (statik HTML/CSS/JS)
├── main.py     faqat botni ishga tushiradi
└── run_all.py  bot + API birgalikda (server uchun)
```

**Asosiy tamoyil:** signal, kontent va foydalanuvchi faqat bitta joyda —
`bot_database.db` faylida — saqlanadi. Bot ham, sayt ham, kelajakdagi ilova
ham o'shani o'qiydi. Ikkinchi baza ham, ikkinchi haqiqat ham yo'q.

### Hozirgi bosqich: bepul, odam yig'ish

`.env` da `FREE_MODE=true` (standart holat):

- barcha bo'limlar **hammaga ochiq**, obuna talab qilinmaydi
- to'lov qabul qilinmaydi, tariflar saytda **"tez orada"** deb ko'rsatiladi
- botning yagona vazifasi — saytga ulanish uchun `/start`

Obunani yoqish uchun `FREE_MODE=false` yozish kifoya. Obuna, to'lov, tarif
nazorati va narx kuzatuvi kodda saqlanib turibdi — qaytadan yozish kerak emas.

### Saytga ulanish

Parol yo'q, ro'yxatdan o'tish yo'q:

```
Saytda "Telegram orqali ulanish" bosadi
  → bot ochiladi, /start bosadi
  → sayt uni o'zi tanidi
```

Havola bir martalik va 5 daqiqada kuchini yo'qotadi. Foydalanuvchi bot bilan
yozishmaydi — bot bu yerda faqat shaxsni tasdiqlaydi.

### Admin panel — xavfsizlik haqida

Admin API'ga kirish uchun **Telegram ID ni bilish yetarli emas**. Har bir
so'rov imzolangan sessiya tokeni bilan keladi, token esa faqat haqiqiy
Telegram hisobiga kirgandan keyin beriladi. Ya'ni admin bo'lish uchun
o'sha hisobning **egasi** bo'lish kerak.

### Ishga tushirish

| Nima kerak | Buyruq |
|---|---|
| Faqat bot (kompyuterda sinash) | `start.bat` yoki `python3 main.py` |
| Bot + sayt API (serverda) | `python3 run_all.py` |
| Faqat API | `uvicorn api.main:app --port 8000` |

Saytni ishlatish uchun `web/assets/js/config.js` ichidagi `apiBaseUrl` ni
API manziliga moslang. Kabinetga kirish ishlashi uchun @BotFather'da
`/setdomain` orqali sayt domenini ko'rsating.

---

## ENG SODDA YO'L — o'z kompyuteringizda (terminalsiz, bepul)

Server ijaraga olmasdan, faqat sichqoncha bilan ishga tushirish. Bot kompyuteringiz
yoniq turganda ishlaydi, kompyuterni o'chirsangiz bot ham to'xtaydi.

**1-qadam. Python o'rnating** (bir marta)

- https://www.python.org/downloads/ ga kiring, sariq **Download Python** tugmasini bosing
- Yuklangan faylni oching
- ⚠️ **"Add Python to PATH"** katagiga belgi qo'ying, keyin **Install Now** bosing

**2-qadam. Kodni yuklab oling**

- https://github.com/urvaalbariqiy-del/cs3_bot ga kiring
- Yashil **Code** tugmasi → **Download ZIP**
- Yuklangan ZIP faylni oching va papkani ish stoliga chiqarib oling (extract)

**3-qadam. Ishga tushiring**

- Papka ichidagi **`start.bat`** faylini ikki marta bosing (Mac'da — `start.sh`)
- Birinchi safar ikkita savol beradi:
  - *BotFather'dan olingan token* — @BotFather dan olgan tokeningizni qo'ying
  - *Admin Telegram ID* — o'z ID raqamingiz (@userinfobot dan bilib olasiz)
- Keyin o'zi hamma kerakli dasturni o'rnatadi (1-2 daqiqa) va botni ishga tushiradi

`Bot polling rejimida ishga tushdi` degan yozuv chiqsa — tayyor. Telegram'da botga
`/start` yozing.

**Keyingi safar** — shunchaki `start.bat` ni bosasiz, savol berilmaydi.

⚠️ Qora oynani yopsangiz bot to'xtaydi. Bot ishlashi uchun oyna ochiq turishi kerak.

> Doimiy 24/7 ishlashi uchun server kerak bo'ladi — pastdagi bo'limga qarang.

---

## BOT TUZILMASI

### Foydalanuvchi ko'radigan narsa

Xabar bilan birga chiqadigan 4 ta tugma (`bot/config.py` → `SECTIONS`).
Yozish maydonining pastidagi klaviatura ishlatilmaydi — barcha menyular
xabarning o'ziga yopishgan (inline) holda chiqadi va bosilganda o'sha
xabarning ichida yangilanadi:

| Bo'lim | Minimal tarif | Turi |
|---|---|---|
| 📈 Savdo signallari | Lite | signal (narx kuzatiladi) |
| ⚡️ Skalping | Pro | signal (narx kuzatiladi) |
| 🎓 Video darsliklar | Pro | kontent |
| 🧠 Strategiyalar | Premium | kontent |

Yuqori tarif pastki darajalarning hamma bo'limini ochadi (Premium → hammasi).

Menyuda ataylab "obuna sotib olish" tugmasi yo'q — bot pullik ekani faqat
yopiq bo'lim bosilganda ma'lum bo'ladi va o'sha yerda qaysi tarif kerakligi
aytiladi. Bo'lim ochiq bo'lsa, ichidagi ro'yxat tugmalar bo'lib chiqadi;
to'liq ma'lumot tugma bosilgandagina ochiladi.

**Obunasizlar ham xabardor bo'ladi:** yangi signal yoki material qo'shilganda
ularga ham xabar boradi, lekin signal raqamlari va materialning o'zi
ko'rinmaydi — faqat "bo'limga yangi narsa qo'shildi" deb turadi.

☰ menyudagi buyruqlar: `/start`, `/obuna`, `/obunam`

### Admin ko'radigan narsa

Xabar bilan birga 3 ta tugma:

1. **📤 Bo'limlarga joylash** — yuqoridagi bo'limlarning istalganiga signal
   yoki material joylash (signalga rasm ham biriktirish mumkin)
2. **💳 To'lov tizimi** — tarif narxlari va to'lov usullari. Usullarni
   xohlagancha qo'shish mumkin (Humo, Uzcard, Click, Payme...): har biriga nom
   va rekvizit yoziladi. Foydalanuvchi to'lov paytida qaysi biri bilan
   to'lashni o'zi tanlaydi; usul bitta bo'lsa tanlash bosqichi o'tkazib
   yuboriladi. Adminga keladigan chek xabarida qaysi usul ishlatilgani ko'rinadi.
3. **🎫 Obunalar** — kutilayotgan to'lovlar, qo'lda obuna berish,
   foydalanuvchi obunasini tekshirish, qoidabuzarlik

☰ menyudagi buyruqlar: `/joylash`, `/tolov`, `/obunalar`, `/yangi_bolim`,
`/xabar`, `/bekor`

`/yangi_bolim` ataylab tugma qilinmagan — kundalik ish emas. U orqali
foydalanuvchilarga butunlay yangi bo'lim (5-, 6-tugma) qo'shiladi: nomi va
minimal tarifi so'raladi, bo'lim bazada saqlanadi va darhol menyuda paydo
bo'ladi.

---

## SERVERDA ISHGA TUSHIRISH (24/7 uchun)

## 1. Loyihani serverga joylash

```bash
# Python 3.11+ o'rnatilgan bo'lishi kerak
sudo apt update && sudo apt install -y python3-pip python3-venv

# loyihani serverga yuklang, so'ng:
git clone https://github.com/urvaalbariqiy-del/cs3_bot.git
cd cs3_bot
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

## 2. Sozlash

```bash
cp .env.example .env
nano .env
```

`.env` faylida quyidagilarni to'ldiring:
- `BOT_TOKEN` — @BotFather'dan `/newbot` orqali olingan token
- `ADMIN_IDS` — o'zingizning Telegram ID raqamingiz (@userinfobot orqali bilib olasiz), bir nechta admin bo'lsa vergul bilan ajrating

## 3. Ishga tushirish (test uchun)

```bash
python3 main.py
```

Agar hammasi to'g'ri bo'lsa, konsolda "Bot polling rejimida ishga tushdi" degan xabarni ko'rasiz.

## 4. Doimiy ishlashi uchun (systemd)

`/etc/systemd/system/cryptobot.service` faylini yarating:

```ini
[Unit]
Description=Crypto Signal Telegram Bot
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/root/cs3_bot
ExecStart=/root/cs3_bot/venv/bin/python3 main.py
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

So'ng:

```bash
sudo systemctl daemon-reload
sudo systemctl enable cryptobot
sudo systemctl start cryptobot

# loglarni ko'rish uchun:
sudo journalctl -u cryptobot -f
```

Bu bot server qayta ishga tushganda (reboot) yoki xato bo'lib to'xtab qolganda ham
avtomatik qayta ishga tushishini ta'minlaydi.

## 5. Birinchi ishga tushirishdan keyin

1. Telegram'da botga `/start` yozing — agar sizning ID'ingiz `.env`dagi
   `ADMIN_IDS` ichida bo'lsa, admin menyu ochiladi.
   (☰ menyudagi buyruqlar bot ishga tushganda avtomatik o'rnatiladi —
   @BotFather'da `/setcommands` qilish shart emas.)
2. **💳 To'lov tizimi → 💵 Narxlarni o'zgartirish** — tariflar narxini qo'ying
   (boshlang'ich standart narxlar avtomatik qo'yilgan, ularni o'zgartirish shart).
3. **💳 To'lov tizimi → 💳 To'lov usullari** — kamida bitta usul qo'shing
   (karta, Click, USDT va h.k.). Aks holda foydalanuvchi to'lov qila olmaydi.
4. **📤 Bo'limlarga joylash → 📈 Savdo signallari** orqali birinchi signalni
   sinab ko'ring. Signal darhol faollashishini ko'rish uchun Entry'ni coin'ning
   hozirgi narxiga juda yaqin qo'ying.

## Loyiha tuzilmasi

```
cs3_bot/
├── main.py                        # Ishga tushirish nuqtasi
├── bot/
│   ├── config.py                  # Sozlamalar (.env dan o'qiydi)
│   ├── database.py                # SQLite bilan ishlash (jadval va funksiyalar)
│   ├── states.py                  # FSM holatlar (bosqichma-bosqich suhbatlar)
│   ├── keyboards.py                # Barcha tugmalar (admin va user)
│   ├── handlers/
│   │   ├── user.py                # Foydalanuvchi buyruqlari
│   │   └── admin.py               # Admin buyruqlari
│   └── services/
│       ├── price_watcher.py       # Binance WebSocket orqali signal kuzatish
│       └── subscription_checker.py # Obuna eslatma/tugash tekshiruvi
├── requirements.txt
└── .env.example
```

## Muhim eslatmalar

- **Ma'lumotlar bazasi** — SQLite (`bot_database.db` fayli avtomatik yaratiladi), alohida server kerak emas. Foydalanuvchilar ko'payib, yuklama oshsa, kelajakda PostgreSQL'ga o'tish mumkin (bu holatda faqat `database.py` qayta yozilishi kerak, qolgan kod o'zgarmaydi).
- **Narx kuzatish** — Binance'ning ochiq (kalitsiz) WebSocket xizmatidan foydalanadi. Agar Binance sizning server joylashgan mamlakatda cheklangan bo'lsa, Bybit yoki OKX'ning WebSocket manziliga almashtirish kerak bo'ladi (`bot/config.py` dagi `BINANCE_WS_BASE`).
- **Kontentni himoyalash** — barcha signal/video/strategiya xabarlari `protect_content=True` bilan yuboriladi (forward va saqlashni cheklaydi). Lekin avvalgi suhbatimizda aytganimdek, ekran skrinshoti yoki video yozib olishning oldini 100% olib bo'lmaydi — bu OS darajasidagi cheklov.
- **Signal mantig'i** — hozirgi holatda faqat spot/long signallar uchun mo'ljallangan (Stop < Entry < TP1 < TP2).
  Signal `pending` holatidan `active` holatiga narx entry darajasini **kesib o'tganda** o'tadi: birinchi narx
  kelganda uning entry'dan qaysi tomonda ekani aniqlanib (`entry_side` ustuni) bazaga yoziladi, keyin faqat
  teskari tomonga o'tish faollashtiradi. Shu sababli entry joriy narxdan pastga qo'yilsa ham signal darhol
  "faol" bo'lib qolmaydi.
- **Qoidabuzarlik** — hozircha bu jarayon qo'lda ishlaydi (admin skrinshot/tarqatilgan kontentni ko'rgach, "🚫 Qoidabuzarlik" tugmasi orqali foydalanuvchi ID'sini kiritadi). Avtomatik aniqlash tizimi kelajakda watermark asosida qo'shilishi mumkin.

## Keyingi bosqichlar (tavsiya)

- Watermark funksiyasini video/rasmlarga qo'shish (har bir foydalanuvchi uchun individual, kim tarqatganini aniqlash uchun)
- Statistika bo'limi (necha foydalanuvchi, qaysi tarifda, oylik daromad)
- To'lovlar tarixi va hisobotlar
