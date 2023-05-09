# Generated by Django 4.1 on 2023-05-08 15:56

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('ARM', '0002_devicekipreport_station'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='devicekipreport',
            options={'verbose_name': 'Прибор', 'verbose_name_plural': 'Ящик'},
        ),
        migrations.AlterField(
            model_name='device',
            name='current_check_date',
            field=models.DateField(blank=True, null=True, verbose_name='дата проверки'),
        ),
        migrations.AlterField(
            model_name='devicekipreport',
            name='mounting_address',
            field=models.CharField(help_text="Если прибор готовится в АВЗ какой-то станции, укажите станцию и впишите в это поле 'авз'.", max_length=10, verbose_name='Монтажный адрес'),
        ),
        migrations.AlterField(
            model_name='kipreport',
            name='explanation',
            field=models.TextField(blank=True, max_length=300, null=True, verbose_name='Пояснение'),
        ),
        migrations.AlterField(
            model_name='kipreport',
            name='title',
            field=models.CharField(blank=True, max_length=100, null=True, verbose_name='Заголовок'),
        ),
    ]