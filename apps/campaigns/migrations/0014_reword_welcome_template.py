from __future__ import annotations

from django.db import migrations

# The original welcome copy thanked the customer for a "purchase" that never
# happened — registration and buying are two different moments, and the
# message went out the second someone finished signing up, before they had
# bought anything at all.
_OLD_BODY = (
    "🎉 <b>{{ user.full_name }}</b>, Real Beauty oilasiga xush kelibsiz!\n\n"
    "Xaridingiz uchun rahmat. Quyida mahsulotingizdan to'g'ri foydalanish "
    "bo'yicha qo'llanmani yuboramiz.\n\n"
    "Savolingiz bo'lsa — pastdagi «✍️ Savol / Murojaat» tugmasini bosing, "
    "jamoamiz javob beradi 👇"
)

_NEW_BODY = (
    "🎉 <b>{{ user.full_name }}</b>, Real Beauty oilasiga xush kelibsiz!\n\n"
    "Savollaringiz bo'lsa — pastdagi «✍️ Savol / Murojaat» tugmasini bosing, "
    "jamoamiz albatta javob beradi 👇\n\n"
    "Sizga yordam berishdan mamnunmiz!"
)


def reword(apps, schema_editor):
    MessageTemplate = apps.get_model("campaigns", "MessageTemplate")
    # Only touch it if it still has the original seeded wording — a shop that
    # already edited this template must keep its own words untouched.
    MessageTemplate.objects.filter(
        template_type="welcome", body=_OLD_BODY
    ).update(body=_NEW_BODY)


def unreword(apps, schema_editor):
    MessageTemplate = apps.get_model("campaigns", "MessageTemplate")
    MessageTemplate.objects.filter(
        template_type="welcome", body=_NEW_BODY
    ).update(body=_OLD_BODY)


class Migration(migrations.Migration):
    dependencies = [
        ("campaigns", "0013_reminderrule"),
    ]

    operations = [migrations.RunPython(reword, unreword)]
