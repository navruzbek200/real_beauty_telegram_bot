from django.db import migrations, models

# The shop's channel has been live all along, but the column shipped blank and
# the Mini App hides a link it has no URL for — so the YouTube row simply never
# appeared. Ship the real channel as the default and backfill the existing row.
YOUTUBE_DEFAULT = "https://www.youtube.com/@Realbeauty_uz1/shorts"


def fill_youtube(apps, schema_editor):
    GlobalSettings = apps.get_model("bot_settings", "GlobalSettings")
    # Only where it is still blank: a shop that typed its own link keeps it.
    GlobalSettings.objects.filter(youtube_url="").update(youtube_url=YOUTUBE_DEFAULT)


class Migration(migrations.Migration):

    dependencies = [
        ('bot_settings', '0007_globalsettings_shop_tagline_en_and_more'),
    ]

    operations = [
        migrations.AlterField(
            model_name='globalsettings',
            name='youtube_url',
            field=models.URLField(blank=True, default=YOUTUBE_DEFAULT, verbose_name='YouTube havolasi'),
        ),
        migrations.RunPython(fill_youtube, migrations.RunPython.noop),
    ]
