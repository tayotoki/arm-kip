# Generated by Django 4.1 on 2023-05-08 09:03

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('ARM', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='devicekipreport',
            name='station',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, to='ARM.station', verbose_name='Станция'),
        ),
    ]
