# Generated by Django 4.1 on 2023-05-31 07:51

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('ARM', '0006_devicekipreport_who_checked_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='kipreport',
            name='editable',
            field=models.BooleanField(default=True),
        ),
        migrations.AlterField(
            model_name='devicekipreport',
            name='mounting_address',
            field=models.CharField(help_text="Если прибор готовится в АВЗ какой-то станции, укажите станцию и впишите в это поле 'авз'.Если готовите много бесконтактной аппаратуры, например, предохранителей, укажите количество ввиде 'n шт.'", max_length=18, verbose_name='Монтажный адрес или АВЗ'),
        ),
    ]
