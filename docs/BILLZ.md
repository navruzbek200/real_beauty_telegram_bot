# BILLZ integratsiyasi

Integratsiya BILLZ’dan mijozning ismi, telefon raqami va xarid mahsulotlarini o‘qiydi. BILLZ’dagi savdo, mijoz, narx yoki ombor yozuvlarini o‘zgartirmaydi.

## Ishga tushirish

Serverning mavjud `.env` fayliga quyidagilarni qo‘shing. Kalitni Git’ga yoki frontendga joylamang.

```dotenv
BILLZ_SECRET_TOKEN=<integratsiya kaliti>
BILLZ_SHOP_IDS=
BILLZ_HISTORY_START=2000-01-01
```

`BILLZ_SHOP_IDS` bo‘sh bo‘lsa hisobdagi barcha faol filiallar olinadi. Cheklash kerak bo‘lsa filial IDlarini vergul bilan yozing.

```bash
docker compose up -d --build
docker compose exec django python manage.py sync_billz --check
```

Mavjud deploy jarayoni yangi migratsiyalarni bajaradi. Celery har daqiqada yangi savdolarni tekshiradi, har safar tarixning bir bo‘lagini ham oladi. BILLZ katta hisobotlarda sekin ishlagani uchun joriy va kechagi kun alohida so‘raladi, bir sahifada 20 ta yozuv olinadi. Eski tarix kunlik bo‘laklardan boshlanadi; bo‘sh davrlarda bo‘lak asta kattalashadi, 365 kundan oshmaydi. So‘rovlar uzoq davom etsa keyingi ish avvalgisini kutadi. To‘liq tarixni alohida tugatish uchun:

```bash
docker compose exec django python manage.py sync_billz --history
```

Bu buyruq Telegram xabarlarini yubormaydi. Bir vaqtdagi sinxronlash Redis qulfi bilan cheklanadi. Keyingi kunlarda tarix davrlari qaytadan tekshiriladi. Yangi xaridlarni olish muvaffaqiyatsiz bo‘lsa uning belgisi surilmaydi; faqat tarix so‘rovi xato bersa yangi xaridlar belgisi saqlanadi va tarix bo‘lagi kichraytirilib qayta uriniladi.

## Mahsulot va qo‘llanmalar

Bir xil yagona nomli mahsulotlar avtomatik moslanadi. Taxminiy nom o‘xshashligiga asoslangan bog‘lash yo‘q. Mos kelmagan mahsulotlar uchun `/admin/billz/billzproduct/` sahifasida **Botdagi mahsulot**ni tanlang; shu bot mahsulotiga mavjud panelda video qo‘llanmasini biriktiring. Xaridorning xaridlar oynasidagi **Qo‘llanmani biriktirish** havolasi kerakli yozuvni ochadi. Eski Django admin uchun xodimning oddiy panel loginidan foydalaniladi.

Eski xaridlar va hali qo‘llanmasi bo‘lmagan mahsulotlar tarixda saqlanadi. Minnatdorchilik xabari katalog yoki videoga bog‘liq emas: yangi chekdagi barcha mahsulotlar BILLZ’dan olinadi. Qo‘llanmasi bor mahsulot uchun video alohida beriladi. Eski va yangi haqiqiy takroriy savdolar alohida saqlanadi, qo‘llanma huquqi esa mijoz/mahsulot uchun bitta.

## Mijozni aniqlash

Bir to‘liq xalqaro telefon raqami uchun bazada bitta mijoz kartasi saqlanadi. Qo‘lda qayta karta yaratish yoki boshqa kartaga shu raqamni yozish rad etiladi. Import va mobil ilova mavjud kartani qayta ishlatadi. Turli davlat kodlari bilan bir xil oxirgi raqamlar turli odamlar hisoblanadi.

Botda BILLZ yoqilganida mijoz avval tilni tanlaydi va o‘z kontaktini yuboradi. BILLZ’da ism mavjud bo‘lsa u qayta so‘ralmaydi; tug‘ilgan sana va teri turi majburiy ro‘yxatdan o‘tish bosqichi emas. Yangi yoki ilgari boshlangan ro‘yxatdan o‘tish ikkinchi kartani yaratmaydi.

0017 migratsiya eski bir xil telefon kartalarini bog‘langan xaridlar, buyurtmalar, bonuslar, dars ruxsatlari va jurnallarni saqlab birlashtiradi. Ikki alohida Telegram hisobi bo‘lgan noaniq juftlik avtomatik qo‘shilmaydi. Qo‘lda telefon keyin o‘zgartirilsa, eski telefon xaridlari o‘z raqamidagi kartada qoladi. Panel tasdiqlangan va tasdiqlanmagan Telegram ulanishlarini farqlab ko‘rsatadi.

BILLZ raqami to‘liq xalqaro shaklda moslanadi. Mijoz botda Telegram’ning **o‘z kontaktini yuborish** tugmasi bilan raqamiga egaligini tasdiqlaydi. Faqat matn bilan yozilgan telefon yoki username BILLZ tarixini ochmaydi. Avvaldan botga kirgan mijozlar birinchi `/start`da bir marta o‘z kontaktini tasdiqlaydi. Hali botni ochmagan mijozga Telegram orqali yozib bo‘lmaydi; uning xaridi saqlanib turadi.

Telefonsiz yoki yaroqsiz raqamli savdo BILLZ xaridlari jurnalida qoladi, lekin hech kimning Telegram hisobiga taxmin bilan ulanmaydi. BILLZ’dagi raqam tuzatilgach qayta tekshirishda bog‘lanadi.

## Avtomatik xabarlar

**BILLZ savdolari** bo‘limida har bir chek, uning barcha mahsulotlari va Telegram xabarining holati ko‘rinadi. **Xarid uchun minnatdorchilik matni** bir marta yoziladi; `{{ first_name }}`, `{{ product_name }}` / `{{ product.name }}`, `{{ products_text }}`, `{{ purchase_date }}` va `{{ order_number }}` har bir chek uchun avtomatik to‘ldiriladi. Oddiy matn yozilsa ham ism va mahsulotlar qo‘shiladi. O‘zbekcha, ruscha va inglizcha matnlar tahrirlanadi. **Onlayn buyurtmalar** Mini App savatchasi va yetkazib berish jarayoniga tegishli.

Yangi chek to‘liq olinib, mijoz o‘z telefonini tasdiqlaganidan keyin bitta minnatdorchilik xabari yuboriladi. Yangi funksiya yoqilishidan oldingi xaridlar ommaviy xabar yubormasdan tarixga olinadi. “Yuborildi” Telegram qabul qilganini bildiradi; o‘qilganini emas. Vaqtinchalik rad etilgan xabar qayta uriniladi, bloklangan mijoz va noaniq yetkazilish panelda ko‘rinadi. Noaniq yuborilish ko‘r-ko‘rona takrorlanmaydi. Juda uzun chek barcha mahsulotlarni saqlagan holda qismlarga bo‘linadi; qabul qilingan qismlar takrorlanmaydi.

7/15 kunlik eslatmalar ham chekdagi barcha mahsulotlarni oladi; muddat BILLZ’dagi haqiqiy xarid vaqtidan hisoblanadi. Mavjud standart ikkinchi qoida 15 kunga o‘tkaziladi; vaqt va matn admin tomonidan o‘zgartiriladi. Juda kech kelgan eslatmalar mavjud eskirish qoidasi bilan yuborilmaydi. To‘liq qaytarilgan savdo bo‘yicha keyingi xabarlar to‘xtaydi; boshqa faol xarid bo‘lmasa faqat BILLZ bergan qo‘llanma huquqi ham olib tashlanadi. Qo‘lda berilgan huquqlar saqlanadi.

## Tekshirish

`/admin/billz/billzsyncstate/` — oxirgi muvaffaqiyatli sinxronlash va tarixning borishi. `/admin/billz/billzpurchase/` — xom xaridlar jurnali. Xaridorning oddiy paneldagi oynasi BILLZ xaridlarini o‘zgartirmasdan ko‘rsatadi.

Kalit bo‘sh bo‘lsa integratsiya o‘chiq. BILLZ tokeni server keshida muddatli saqlanadi; eskirganda kalit orqali yangidan olinadi. Tarmoq, ruxsat va limit xatolari jurnalda kalit yoki mijoz ma’lumotlarini chiqarmaydi.

Bekor qilingan chek hisobotdan yo‘qolsa, bot BILLZ’dagi chek holatini alohida tekshiradi. Faqat BILLZ bekor qilinganini aniq tasdiqlaganda xarid **Bekor qilingan** deb belgilanadi; yozuv va mijoz tarixi saqlanadi, shu savdoga tegishli avtomatik qo‘llanma huquqi va xabarlari to‘xtaydi. Hisobotda yozuv topilmagani yoki so‘rov xatosi bekor qilish uchun yetarli emas. Qo‘lda biriktirilgan mahsulotlar saqlanadi. Qayta paydo bo‘lgan haqiqiy chek odatiy holatga qaytadi.

Rasmiy ma’lumot: https://docs.billz.io/uz/reference/api/operations/get_v1_customer_purchases_table/
