"""
Retire the "Fikr bildirish" (submit feedback) auto-message button.

The whole product-rating flow it opened (rating 1-5 + a written comment) has
been removed from the bot. Any rule still configured with this action would
otherwise show customers a button that silently does nothing when tapped —
worse than no button at all. Existing rows fall back to text-only rather
than losing the message altogether.
"""

from __future__ import annotations

from django.db import migrations, models


def retire(apps, schema_editor):
    AutoMessage = apps.get_model("campaigns", "AutoMessage")
    AutoMessage.objects.filter(button_action="feedback").update(button_action="none")


def unretire(apps, schema_editor):
    # Not reversible in any meaningful way — which rows used to carry the
    # feedback action is no longer recorded once they're switched to "none".
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('campaigns', '0010_seed_auto_messages'),
    ]

    operations = [
        migrations.RunPython(retire, unretire),
        migrations.AlterField(
            model_name='automessage',
            name='button_action',
            field=models.CharField(choices=[('none', 'Tugmasiz (faqat matn)'), ('progress', '«Rasm yuborish» tugmasi'), ('discounts', "«Chegirmalarni ko'rish» tugmasi")], default='none', max_length=16, verbose_name='Xabar ostidagi tugma'),
        ),
    ]
