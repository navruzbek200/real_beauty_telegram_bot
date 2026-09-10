from __future__ import annotations

from django.db import migrations

# Every automatic message the bot can send, with copy that is ready to go out
# as-is. Without this a fresh install sends nothing at all (the senders skip
# missing templates silently), and the shop owner has to guess both the wording
# and the placeholder names before the bot does anything.
TEMPLATES = [
    {
        "name": "Xush kelibsiz",
        "template_type": "welcome",
        "body": (
            "🎉 <b>{{ user.full_name }}</b>, Real Beauty oilasiga xush kelibsiz!\n\n"
            "Xaridingiz uchun rahmat. Quyida mahsulotingizdan to'g'ri foydalanish "
            "bo'yicha qo'llanmani yuboramiz.\n\n"
            "Savolingiz bo'lsa — pastdagi «✍️ Savol / Murojaat» tugmasini bosing, "
            "jamoamiz javob beradi 👇"
        ),
    },
    {
        "name": "Mahsulot qo'llanmasi",
        "template_type": "product_intro",
        "body": (
            "📘 <b>{{ product.name }}</b> — foydalanish qo'llanmasi.\n\n"
            "Har bir bosqichning videosini ko'rish uchun quyidagi tugmalarni "
            "bosing 👇"
        ),
    },
    {
        "name": "1-hafta so'rovi",
        "template_type": "week1_checkin",
        "body": (
            "👋 Salom, {{ user.full_name }}!\n\n"
            "<b>{{ product.name }}</b> mahsulotidan foydalanayotganingizga bir hafta "
            "bo'ldi. Teringiz o'zini qanday his qilyapti?\n\n"
            "Fikringiz biz uchun juda muhim — quyidagi tugma orqali yozib "
            "qoldiring 👇"
        ),
    },
    {
        "name": "2-hafta natija so'rovi",
        "template_type": "week2_progress",
        "body": (
            "✨ {{ user.full_name }}, <b>{{ product.name }}</b> bilan 2 hafta bo'ldi!\n\n"
            "Teringizdagi o'zgarishni ko'rsatadigan «oldin» va «keyin» "
            "rasmlaringizni yuborsangiz, natijangizni jamoamiz ko'rib chiqadi 👇"
        ),
    },
    {
        "name": "Tug'ilgan kun chegirmasi",
        "template_type": "birthday_sale",
        "body": (
            "🎂 <b>{{ user.full_name }}</b>, tug'ilgan kuningiz muborak!\n\n"
            "Sizga sovg'amiz — bugun barcha mahsulotlarga <b>{{ discount }}%</b> "
            "chegirma! 🎁\n\n"
            "Buyurtma uchun shu yerga yozing yoki do'konimizga tashrif buyuring."
        ),
    },
    {
        "name": "Fikr uchun rahmat",
        "template_type": "feedback_thanks",
        # Rendered with an empty context by the feedback handler — no placeholders.
        "body": (
            "🙏 Fikringiz uchun katta rahmat!\n\n"
            "Har bir izoh biz uchun qimmatli — xizmatimizni shu asosda "
            "yaxshilaymiz."
        ),
    },
]


def seed(apps, schema_editor):
    MessageTemplate = apps.get_model("campaigns", "MessageTemplate")
    for template in TEMPLATES:
        # Skip any type the shop has already written copy for — this must never
        # overwrite an admin's own wording.
        if MessageTemplate.objects.filter(
            template_type=template["template_type"]
        ).exists():
            continue
        MessageTemplate.objects.create(
            name=template["name"],
            template_type=template["template_type"],
            body=template["body"],
            parse_mode="HTML",
            is_active=True,
        )


def unseed(apps, schema_editor):
    MessageTemplate = apps.get_model("campaigns", "MessageTemplate")
    MessageTemplate.objects.filter(name__in=[t["name"] for t in TEMPLATES]).delete()


class Migration(migrations.Migration):
    dependencies = [
        ("campaigns", "0003_campaignlog_campaigns_c_sent_at_239ab4_idx_and_more"),
    ]

    operations = [migrations.RunPython(seed, unseed)]
