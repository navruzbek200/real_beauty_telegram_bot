# Real Beauty — Telegram Marketing Bot + CRM

Telegram bot (aiogram 3) + boshqaruv paneli, bitta PostgreSQL bazada. Bot uch
tilda ishlaydi (o'zbek / rus / ingliz), teri turini 10 savollik test bilan
aniqlaydi, bonus (ball + keshbek) dasturini yuritadi. Celery avtomatik
xabarlarni yuboradi — vaqti va matni boshqaruv panelida sozlanadi.

Boshqaruv paneli ikki qatlamdan iborat: **Django REST Framework API**
(`/api/v1/`) va uning ustidagi **React SPA** (`frontend/`). Eski
django-unfold admin (`/admin/`) ham ishlab turibdi — ko'chish davrida ikkalasi
parallel ishlaydi (pastdagi "API va React SPA" bo'limiga qarang).

## Arxitektura

| Qism             | Stack                     | Kirish nuqtasi           |
| ---------------- | -------------------------- | ------------------------ |
| Bot              | aiogram 3 + Redis FSM      | `python -m bot.main`     |
| API              | Django 5 + DRF + JWT       | `/api/v1/`               |
| React SPA        | React 19 + TS + Vite       | `frontend/`, nginx `/`   |
| Eski admin panel | Django 5 + django-unfold   | `/admin/`                |
| Rejalashtiruv    | Celery worker + beat       | `celery -A tasks.celery` |
| Baza             | PostgreSQL 16              | —                        |
| Broker / FSM     | Redis 7                    | —                        |
| Prod kirish      | nginx (SPA + media + proxy)| `docker/nginx/`          |

### Django app'lar

- `apps.users` — Xaridorlar (`TelegramUser`), sotib olingan mahsulotlar,
  Xodimlar (auth `User` proxy) va sotuvchi profillari (referal havola).
- `apps.products` — Mahsulotlar, qo'llanma qadamlari (himoyalangan video) va
  «Bu oydagi top» ro'yxati (`TopProduct` — o'sha jadvalning proxy'si).
- `apps.campaigns` — Avtomatik xabarlar (`AutoMessage` + jurnal), xabar
  shablonlari (Jinja2), e'lonlar, yuborilganlar jurnali.
- `apps.support` — Murojaatlar: bot ↔ admin ikki tomonlama chat.
- `apps.analytics` — Fikrlar (baho 1-5), teri testi natijalari va natija
  rasmlari (original Telegramda `file_id` orqali, diskda faqat thumbnail).
- `apps.loyalty` — Bonus dasturi: ball hisobi, harakatlar tarixi, darajalar,
  sovg'alar va promokodlar.
- `apps.bot_settings` — Umumiy sozlamalar (singleton) va chegirmalar.

### Muhim dizayn qarorlari

- **Uch til:** mijoz `/start` bosgach birinchi savol — til. Tanlov
  `TelegramUser.language`da saqlanadi, `LanguageMiddleware` uni har bir
  handlerga `lang` bo'lib beradi. Barcha qat'iy matnlar `bot/i18n/`da
  (uz/ru/en bir xil kalitlar bilan), adminda yozilgan matnlar esa bazada
  `_ru`/`_en` ustunlarda — bo'sh bo'lsa o'zbekchaga qaytadi (`core.i18n.pick`).
  Menyu tugmalari `MenuText` filtri orqali uch tilda ham topiladi: mijozning
  ekranida eski klaviatura qolishi mumkin.
- **Avtomatik xabarlar:** vaqt, matn va tugma — bitta `AutoMessage` qatori.
  Vaqt birligi **daqiqa / soat / kun** bo'lgani uchun kampaniyani 1 daqiqaga
  qo'yib sinab ko'rish mumkin; «Sinov rejimi» esa xabarni faqat tanlangan
  bitta mijozga yuboradi, shuning uchun sinov paytida boshqalarga tegmaydi.
  Celery beat har daqiqada yuritiladi, takrorlanmaslik `AutoMessageLog`dagi
  `anchor` (`up:<id>` yoki `user:<id>`) bilan ta'minlanadi.
- **Teri testi:** teri turi faqat **1-savoldan** aniqlanadi (0–1 quruq,
  2 aralash, 3 normal, 4–5 yog'li); qolgan 9 savol javobi 3 dan katta bo'lsa
  o'z tavsiya blokini qo'shadi. Qoidalar `apps/analytics/skin_logic.py`da —
  Django'dan mustaqil, shuning uchun mobil ilova ham shu mantiqni ishlatadi.
- **Bonus dasturi:** daraja **jami yig'ilgan** ballga qarab beriladi, balansga
  emas — aks holda sovg'a olish darajani pasaytirar va hech kim ball
  sarflamas edi. Har bir ball harakati `PointsTransaction`da; takroriy
  to'lovni `reference` (masalan `userproduct:42`) bo'yicha unique cheklov
  to'xtatadi.

- **Xaridor qo'shish:** faqat ism + telefon. Mijoz botga kirib raqamini
  yuborganda kartasi telefonning oxirgi 9 raqami (`phone_tail`) orqali avtomatik
  ulanadi. Telegram ID hech qayerda qo'lda kiritilmaydi.
- **Rasmlar:** original Telegram serverida qoladi (`file_id`), diskda 400px
  thumbnail (~40KB). Eski thumbnaillar 180 kundan keyin tozalanadi — original
  baribir ochiladi (`/tg-file/<file_id>/` staff-only proxy).
- **Jurnal tozalash:** CampaignLog 90 kun, admin log 90 kun, thumbnail 180 kun —
  haftalik Celery beat.
- **Tarjima:** Django'ning `uz` katalogi chala; yetishmagani `locale/`da.
  `.po` o'zgartirilsa `python scripts/compile_messages.py` yuritiladi
  (gettext talab qilinmaydi).

## Katalog (mahsulotlar, rasmlar, tavsiflar)

Do'konning haqiqiy mahsulot ro'yxati kodda turadi:

| Nima                         | Qayerda                              |
| ---------------------------- | ------------------------------------ |
| Ma'lumot (nom, uz/ru/en matn)| `apps/products/catalog/` (brend bo'yicha) |
| Studiya rasmlari             | `apps/products/assets/catalog/*.jpg` (1000×1000, kvadratga to'ldirilgan) |
| Bazaga yozadigan buyruq      | `manage.py sync_catalog`             |

```bash
python manage.py sync_catalog --dry-run     # nima o'zgarishini ko'rsatadi
python manage.py sync_catalog               # qo'llaydi
python manage.py sync_catalog --force-photo # rasmlarni ham qayta yuklaydi
```

Buyruq **faqat to'ldiradi**: bazada bo'sh bo'lgan tavsif yoki rasmni yozadi,
adminda yozilgan matnni va **narxlarni hech qachon o'zgartirmaydi**. Shuning
uchun uni har deploydan keyin yuritish xavfsiz — do'konning o'z tahrirlari
saqlanib qoladi. Mahsulot `name` bo'yicha topiladi: adminda nomni
o'zgartirsangiz, bu yerda ham o'zgartiring, aks holda keyingi yuritishda
dublikat paydo bo'ladi.

Yangi mahsulot qo'shish: rasmni `assets/catalog/`ga (kvadrat JPEG) qo'ying,
`catalog/<brend>.py`ga `photo`/`name`/`uz`/`ru`/`en` bilan qator qo'shing va
buyruqni yuriting. Narxni admin panelda belgilaysiz — narxsiz mahsulot Mini
App'da «Narx tez orada» bo'lib chiqadi va sotib olinmaydi.

## Lokal ishga tushirish

```bash
./run_local.sh          # hammasi: db, redis, migrate, django, bot, celery
SEED=1 ./run_local.sh   # + demo ma'lumotlar
```

Admin: http://localhost:8000/admin/ (admin/admin).
Skript eski bot nusxalarini o'zi o'ldiradi — Telegram bitta tokenga bitta
polling ulanishiga ruxsat beradi, ikkinchi nusxa botni "o'lik" qilib qo'yadi.

## API va React SPA

### Backend — `/api/v1/`

- Auth: JWT (`djangorestframework-simplejwt`). `POST /api/v1/auth/login/`
  (username+password, admin/`Staff` hisoblari bilan bir xil), `POST
  /api/v1/auth/refresh/` (rotatsiya bilan), `GET /api/v1/auth/me/` (rol +
  ruxsatlar ro'yxati).
- Ruxsatlar mavjud Django Group/permission tizimidan olinadi
  (`apps/users/roles.py`) — admin panelda ishlagan narsa API'da ham xuddi
  shunday ishlaydi, alohida ruxsat tizimi yo'q.
- Har bir app'ning ViewSet'lari `apps/api/views/`da, serializer'lari
  `apps/api/serializers/`da. Sahifalash, `?search=`, `?ordering=` va
  filterlar (`django-filter`) barcha ro'yxatlarda bor.
- OpenAPI sxema: `GET /api/v1/schema/` (drf-spectacular). Sxemani faylga
  chiqarish:

  ```bash
  python manage.py spectacular --file schema.yaml
  ```

- CORS: `CORS_ALLOWED_ORIGINS` (`.env`) — lokal devda Vite manzili
  (`http://localhost:5173`) kerak. Prodda kerak emas: SPA va API bitta
  origin'dan (nginx) xizmat qiladi.

### Frontend — `frontend/`

React 19 + TypeScript (strict) + Vite, Feature-Sliced Design arxitekturasi
(`app → pages → widgets → features → entities → shared`, faqat pastga
import). TanStack Query serverdagi holat uchun, Zustand faqat UI/sessiya
holati uchun (server ma'lumoti Zustand'da saqlanmaydi). Tiplar
**qo'lda yozilmaydi** — OpenAPI sxemadan avtomatik generatsiya qilinadi.

```bash
cd frontend
npm install
cp .env.example .env       # VITE_API_BASE_URL=http://localhost:8000

# Backend allaqachon ishlab turishi kerak (yuqoridagi ./run_local.sh)
npm run generate:types     # OpenAPI sxemadan src/shared/api/generated.ts yaratadi
npm run dev                # http://localhost:5173
```

Tekshiruvlar (CI/deploy'dan oldin ham shu buyruqlar ishlatiladi):

```bash
npm run typecheck   # tsc -b --noEmit
npm run lint        # eslint . — FSD qatlam qoidalari ham shu yerda tekshiriladi
npm run build       # tsc -b && vite build
```

`eslint-plugin-boundaries` qatlamlar orasidagi importni qattiq nazorat
qiladi: bir xil qatlamdagi ikkita "slice" bir-birini to'g'ridan-to'g'ri
import qila olmaydi (masalan `entities/product` → `entities/customer`
xato beradi), faqat pastga (masalan `features` → `entities`) import
mumkin. `app` va `shared` — texnik qatlamlar, ular o'z ichida erkin.

Backend'da biror serializer/endpoint o'zgarsa, `npm run generate:types`ni
qayta yuritish kerak — aks holda frontend eski tiplarga qarab ishlaydi.

### Ma'lum cheklovlar

- Rasm/fayl maydonlari (`Product.photo`, `TelegramUser.photo`,
  `ProductTutorialStep.video_file`, `Broadcast.photo` va h.k.) SPA'da
  ko'pchilik joyda **faqat ko'rish** uchun — yuklab qo'yish faqat
  Mahsulotlar sahifasida bor (`multipart/form-data` orqali). Qolganlarini
  hozircha faqat eski `/admin/` orqali yuklash mumkin.
- «Bu oydagi topga qo'shish» ommaviy amali (checkbox bilan bir nechta
  qatorni tanlash) SPA'da har bir qator uchun alohida tugma bo'ldi
  (bir xil natija, bitta-bitta bosiladi).

## Deploy (VPS, Docker)

1. **Server:** Docker + docker compose o'rnatilgan bo'lsin. DNS A-yozuv
   domeningizni serverga qaratsin.

2. **Sozlash:**

   ```bash
   git clone <repo> && cd realbeauty
   cp .env.example .env
   nano .env    # hamma qiymatni to'ldiring — fayl ichida yo'riqnoma bor
   ```

   Majburiy: `DJANGO_SECRET_KEY` (kuchli), `ALLOWED_HOSTS` (domen),
   `POSTGRES_PASSWORD` (kuchli), `BOT_TOKEN`, `BOT_USERNAME`.
   `prod.py` bo'sh/zaif qiymat bilan ataylab ishga tushmaydi.

3. **Ishga tushirish:**

   ```bash
   docker compose up -d --build
   docker compose exec django python manage.py createsuperuser
   ```

   `migrate` servisi avtomatik: baza tayyor bo'lmaguncha app'lar ko'tarilmaydi.
   `frontend-sync` servisi React SPA'ni build qilib, nginx o'qiydigan
   volume'ga nusxalaydi — alohida qadam kerak emas, `--build` bilan birga
   ishlaydi. nginx `/` ostida SPA'ni, `/admin/` va `/api/v1/` ostida
   Django'ni, `/tg-file/` ostida Telegram fayl proksisini beradi.

4. **HTTPS:** `certbot --nginx` (yoki Cloudflare proxy). `prod.py`da
   `SECURE_SSL_REDIRECT=True` — TLS'siz ishlamaydi, bu ataylab.

5. **Yangilash:**

   ```bash
   git pull && docker compose up -d --build
   ```

### Diqqat — bitta bot qoidasi

Bitta `BOT_TOKEN` bilan faqat **bitta** bot jarayoni polling qilishi mumkin.
Serverda ishlayotganda lokalda `run_local.sh` ishlatmang (yoki alohida
test-bot token oling), aks holda ikkalasi ham `TelegramConflictError` bilan
talashib, foydalanuvchiga bot o'lik ko'rinadi.

### Zaxira nusxa

```bash
docker compose exec db pg_dump -U realbeauty realbeauty | gzip > backup_$(date +%F).sql.gz
```

Media (thumbnail'lar) `media` volume'da; originallar Telegramda — bazani
saqlasangiz rasmlarga havolalar ham saqlanadi. Cron'ga qo'ying.

## Rollar

| Rol           | Ko'radi                                                        |
| ------------- | -------------------------------------------------------------- |
| Administrator | Hammasi                                                         |
| Sotuvchi      | Xaridorlar (qo'shish/tahrirlash), Murojaatlar (javob), Fikrlar, Teri testi natijalari, Natija rasmlari, Mahsulotlar (ko'rish), Bonus promokodlari (tekshirish/belgilash) |

Sotuvchi ruxsatlari kodda: `apps/users/roles.py` (`SELLER_PERMISSIONS`) —
migratsiya 0009 mavjud bazani shu ro'yxatga tenglashtiradi. Bu ro'yxat
`/admin/` va yangi `/api/v1/` (demak — React SPA) uchun bir xil: ikkalasi
ham bitta Django Group/permission tizimidan foydalanadi.

## Testlar

```bash
DJANGO_SETTINGS_MODULE=core.settings.test ./.venv/bin/python manage.py test tests
```

`core/settings/test.py` `BOT_TOKEN`ni bo'shatadi (test paytida hech kimga
haqiqiy xabar ketmasligi uchun) va Redis o'rniga xotiradagi kesh ishlatadi.
