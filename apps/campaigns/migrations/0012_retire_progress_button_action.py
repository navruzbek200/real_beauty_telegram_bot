"""
Retire the "Rasm yuborish" (send before/after photo) auto-message button.

The progress-photo flow it opened is gone from the bot, so a rule still
carrying this action would show customers a button that does nothing. The
seeded "2-hafta — natija rasmi" rule survives as a text-only check-in.
"""

from __future__ import annotations

from django.db import migrations, models


def retire(apps, schema_editor):
    AutoMessage = apps.get_model("campaigns", "AutoMessage")
    AutoMessage.objects.filter(button_action="progress").update(button_action="none")


def unretire(apps, schema_editor):
    # Which rows carried the progress action is no longer recorded once
    # they're switched to "none".
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('campaigns', '0011_retire_feedback_button_action'),
    ]

    operations = [
        migrations.RunPython(retire, unretire),
        migrations.AlterField(
            model_name='automessage',
            name='button_action',
            field=models.CharField(choices=[('none', 'Tugmasiz (faqat matn)'), ('discounts', "«Chegirmalarni ko'rish» tugmasi")], default='none', max_length=16, verbose_name='Xabar ostidagi tugma'),
        ),
    ]
