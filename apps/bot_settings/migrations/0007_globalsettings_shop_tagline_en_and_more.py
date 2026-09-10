from django.db import migrations, models

# The default Uzbek tagline ships with the model, so its two translations ship
# here — otherwise every install starts out greeting Russian and English
# customers in Uzbek, which is exactly the gap these columns exist to close.
UZ_DEFAULT = "Teringizga professional g'amxo'rlik"
RU_DEFAULT = "Профессиональный уход за вашей кожей"
EN_DEFAULT = "Professional care for your skin"


def fill_defaults(apps, schema_editor):
    GlobalSettings = apps.get_model("bot_settings", "GlobalSettings")
    # Only when the shop has not replaced the stock Uzbek line: a custom
    # tagline needs the shop's own translation, not ours.
    GlobalSettings.objects.filter(
        shop_tagline=UZ_DEFAULT, shop_tagline_ru="", shop_tagline_en=""
    ).update(shop_tagline_ru=RU_DEFAULT, shop_tagline_en=EN_DEFAULT)


class Migration(migrations.Migration):

    dependencies = [
        ('bot_settings', '0006_globalsettings_delivery_fee_bts_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='globalsettings',
            name='shop_tagline_en',
            field=models.CharField(blank=True, default=EN_DEFAULT, max_length=120, verbose_name="Do'kon shiori (inglizcha)"),
        ),
        migrations.AddField(
            model_name='globalsettings',
            name='shop_tagline_ru',
            field=models.CharField(blank=True, default=RU_DEFAULT, max_length=120, verbose_name="Do'kon shiori (ruscha)"),
        ),
        migrations.RunPython(fill_defaults, migrations.RunPython.noop),
    ]
