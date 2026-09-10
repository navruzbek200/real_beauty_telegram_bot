from __future__ import annotations

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("campaigns", "0006_one_template_per_type"),
    ]

    operations = [
        migrations.AlterField(
            model_name="messagetemplate",
            name="template_type",
            field=models.CharField(
                choices=[
                    ("welcome", "Ro'yxatdan o'tgach salomlashish"),
                    ("product_intro", "Mahsulot qo'llanmasi kirish"),
                    ("week1_checkin", "1-hafta so'rovi"),
                    ("week2_progress", "2-hafta natija so'rovi"),
                    ("birthday_sale", "Tug'ilgan kun chegirmasi"),
                    ("feedback_thanks", "Fikr uchun rahmat"),
                ],
                max_length=32,
                unique=True,
                verbose_name="Shablon turi",
            ),
        ),
    ]
