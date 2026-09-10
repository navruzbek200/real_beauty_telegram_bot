from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('bot_settings', '0008_globalsettings_youtube_default'),
    ]

    operations = [
        migrations.AddField(
            model_name='globalsettings',
            name='cash_on_delivery_enabled',
            field=models.BooleanField(
                default=True,
                help_text="O'chirilsa Mini App'da «yetkazishda naqd» varianti "
                "ko'rsatilmaydi — faqat karta orqali to'lov qoladi.",
                verbose_name="Naqd to'lov (yetkazishda)",
            ),
        ),
    ]
