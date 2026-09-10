from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('products', '0006_alter_producttutorialstep_intro_text'),
    ]

    operations = [
        migrations.AddField(
            model_name='product',
            name='in_stock',
            field=models.BooleanField(
                default=True,
                db_index=True,
                verbose_name='Sotuvda mavjud',
            ),
        ),
    ]
