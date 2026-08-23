# Ishga tushirish (deploy) yo'riqnomasi

Loyiha ikki qismdan iborat va ular **ikki xil joyda** turadi:

```
Sayt (web/)   →  Vercel        —  bepul, allaqachon bor
API (api/+bot/) →  Railway     —  ~5 dollar/oy, doim ishlab turadi
```

**Nega Vercel API'ni ko'tara olmaydi:** Vercel serverless — funksiya
so'rovga javob berib, o'chadi. Bizga esa doim ishlab turadigan jarayon
kerak: bot Telegram'ni tinglaydi, narx kuzatuvchisi Binance bilan uzluksiz
ulanib turadi. Bundan tashqari Vercel'da yozilgan fayl saqlanmaydi —
`bot_database.db` har deploy'da yo'qolardi.

---

## 1-QISM. API'ni Railway'ga qo'yish

### 1.1. Loyihani ulash

1. https://railway.app ga kiring (GitHub bilan)
2. **New Project** → **Deploy from GitHub repo**
3. `cs3_bot` reposini tanlang
4. Branch: `claude/new-session-sohwaw`

Railway o'zi Python ekanini aniqlaydi va `Procfile` dagi buyruqni
(`python3 run_all.py`) ishga tushiradi.

### 1.2. Disk qo'shish (MUHIM)

Busiz baza har deploy'da o'chadi — obunachilar, signallar, hammasi.

1. Loyiha ichida servisni oching → **Variables** yonidagi **Settings**
2. **Volumes** → **New Volume**
3. Mount path: `/data`

### 1.3. O'zgaruvchilar

**Variables** bo'limiga quyidagilarni qo'shing:

| Nomi | Qiymati |
|---|---|
| `BOT_TOKEN` | @BotFather'dan olingan token |
| `BOT_USERNAME` | bot nomi, `@` siz. Masalan: `cryptospot3_bot` |
| `ADMIN_IDS` | `5079059516,7255169991` |
| `FREE_MODE` | `true` |
| `DB_PATH` | `/data/bot_database.db` ← diskka ishora qiladi |
| `API_SECRET` | uzun tasodifiy matn (pastga qarang) |
| `CORS_ORIGINS` | `https://cryptospot-3.vercel.app` |

`API_SECRET` uchun tasodifiy qiymat yasash:

```bash
python3 -c "import secrets; print(secrets.token_urlsafe(48))"
```

> Buni bir marta yasab qo'ying va keyin o'zgartirmang — o'zgartirilsa
> hamma foydalanuvchi saytdan chiqib ketadi (qaytadan ulanishi kerak).

### 1.4. Manzilni olish

**Settings** → **Networking** → **Generate Domain**.
`https://cs3-bot-production.up.railway.app` kabi manzil beradi.

Tekshirish: shu manzilga `/health` qo'shib brauzerda oching. Shunday
javob chiqishi kerak:

```json
{"ok": true, "service": "cryptospot3-api"}
```

Chiqmasa — Railway'dagi **Deployments** → **View Logs** ga qarang.

---

## 2-QISM. Saytni Vercel'ga qo'yish

Sizda allaqachon Vercel loyihasi bor. Uni yangi papkaga qaratamiz.

1. Vercel'da loyihangizni oching → **Settings** → **General**
2. **Root Directory** → **Edit** → `web` deb yozing → **Save**
3. **Build & Development Settings**:
   - Framework Preset: **Other**
   - Build Command: bo'sh qoldiring
   - Output Directory: bo'sh qoldiring

Sayt oddiy HTML — build qilish kerak emas.

> Agar Vercel loyihangiz eski repoga ulangan bo'lsa, **Settings → Git**
> dan uni `cs3_bot` reposiga va `claude/new-session-sohwaw` branchiga
> ulang.

---

## 3-QISM. Ikkalasini bog'lash

`web/assets/js/config.js` faylini oching va to'ldiring:

```js
window.SITE_CONFIG = {
  apiBaseUrl: "https://cs3-bot-production.up.railway.app",  // 1.4 dagi manzil
  telegramBotUsername: "cryptospot3_bot",                    // @ siz
  ...
};
```

GitHub'ga saqlang — Vercel o'zi qayta deploy qiladi (~30 soniya).

---

## 4-QISM. Tekshirish

Saytni ochib, shularni bosing:

- [ ] 9 sahifa ochiladi, hamburger menyu ishlaydi
- [ ] **Signallar** sahifasida signallar ko'rinadi
- [ ] **Ulanish** tugmasi → Telegram ochiladi → `/start` → sayt sizni tanidi
- [ ] `/admin.html` → **Ulanish** → panel ochiladi
- [ ] Paneldan signal qo'shing → Signallar sahifasida darhol chiqadi

Ishlamasa: brauzerda **F12** → **Console** ga qarang. Ko'p uchraydigan xato —
`CORS`. Unda `CORS_ORIGINS` da sayt manzili aynan to'g'ri yozilganini
tekshiring (oxirida `/` bo'lmasin).

---

## Keyinchalik

**Domen qo'shish.** Vercel → **Settings** → **Domains** → domeningizni
qo'shing. Shundan keyin `CORS_ORIGINS` ga yangi manzilni ham qo'shing
(vergul bilan, ikkalasi ham qolsin).

**Obunani yoqish.** Railway'da `FREE_MODE` ni `false` qiling. Obuna,
to'lov va tarif nazorati darhol kuchga kiradi — kod tayyor turibdi.

**Zaxira nusxa.** `/data/bot_database.db` — hamma narsa shu faylda.
Vaqti-vaqti bilan yuklab olib qo'ying.

---

## Bilib qo'yish kerak

**Bot bitta nusxada ishlashi shart.** Telegram bitta botga ikkita
tinglovchini qo'ymaydi. Ya'ni kompyuteringizdagi `start.bat` ni yoping,
aks holda Railway'dagi bot bilan urushadi (`409 Conflict`).

**Deploy paytida qisqa uzilish bo'ladi** — eski va yangi nusxa bir necha
soniya ustma-ust tushadi. Bu normal, o'zi tuzaladi.
