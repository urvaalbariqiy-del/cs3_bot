# Cryptospot 3% — To'liq ko'p sahifali sayt

## Sahifalar
- `index.html` — Bosh sahifa (biz haqimizda, bo'limlar teaser'i, fikrlar)
- `vip3.html` — VIP 3% (tavsif, narxlar $10/$25, oylik natijalar)
- `community.html` — My Community (tavsif, faqat Mentorlik orqali kirish)
- `kurs.html` — CS3% Mentorlik (duo kitobi, 4 model, 3 xil tarif, FAQ)
- `video-darslar.html` — Video darsliklar ro'yxati (hozircha qulflangan holat)
- `signal.html` — Jonli TradingView grafigi + top coinlar + signallar ro'yxati
- `eslatmalar.html` — Qur'on/hadis eslatmalari
- `social.html` — Ijtimoiy tarmoqlar
- `admin.html` — Admin panel (Telegram ID orqali kirish)

## Navigatsiya
Barcha sahifalarda yagona hamburger menyu (☰) — bosilganda barcha sahifalarga
link beruvchi drawer ochiladi. Bu `assets/css/main.css`da global tarzda
sozlangan (`.nav-links` doim yashirin, `.burger` doim ko'rinadi).

## Backend
`backend/` papkasida — bot + admin API. Yangi qo'shilganlar:
- `admins` jadvali — kelajakda bir nechta admin/rol (lite/pro/premium) qo'shish uchun
- `signals` jadvali — Signal sahifasidagi savdo signallari
- `/api/admin/*` endpointlari — admin.html shu orqali ishlaydi (X-Admin-Id header bilan)

## Admin panel qanday ishlaydi
1. `admin.html`ni oching, ruxsat berilgan Telegram ID'ni kiriting (hozircha
   faqat `backend/.env`dagi `ADMIN_CHAT_ID` ishlaydi).
2. Kirgach: to'lov hamyoni, Mentorlik o'rinlari va Signal postlarini
   boshqarish mumkin.
3. Kelajakda ko'proq adminlar (masalan yordamchilar) qo'shish uchun
   `storage.add_admin(telegram_id, role)` funksiyasidan foydalaniladi —
   `role` maydoni keyinchalik lite/pro/premium ajratish uchun tayyor.

## Muhim: hali qilinishi kerak bo'lgan narsalar
- Backend Render.com'ga hali deploy qilinmagan (avvalgi backend/README.md'ga qarang)
- `assets/js/config.js`dagi `apiBaseUrl` va `telegramBotUsername` haqiqiy
  qiymatlar bilan to'ldirilishi kerak — shundan keyin Signal, Admin panel va
  Mentorlik o'rinlar hisoblagichi jonli ma'lumot bilan ishlay boshlaydi.
- `assets/img/logo-main.png` — bu fayl nav logotipi uchun ishlatiladi, uni
  o'zingizning haqiqiy logotip fayli bilan almashtiring (hozircha eski
  logo-vip3.png nusxasi qo'yilgan, placeholder sifatida).
