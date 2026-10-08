from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('bot_settings', '0009_globalsettings_cash_on_delivery_enabled'),
    ]

    operations = [
        # AddField with a default fills the existing settings row too, so the
        # Mini App shows the «Biz haqimizda» row without anyone typing the URL.
        migrations.AddField(
            model_name='globalsettings',
            name='linktree_url',
            field=models.URLField(blank=True, default='https://linktr.ee/realbeauty_uz', verbose_name='Linktree («Biz haqimizda») havolasi'),
        ),
    ]
