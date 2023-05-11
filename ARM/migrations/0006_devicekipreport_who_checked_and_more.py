# Generated by Django 4.1 on 2023-05-11 14:11

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('ARM', '0005_device_old_information_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='devicekipreport',
            name='who_checked',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='kip_checker', to=settings.AUTH_USER_MODEL, verbose_name='Проверил'),
        ),
        migrations.AddField(
            model_name='devicekipreport',
            name='who_prepared',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='kip_preparer', to=settings.AUTH_USER_MODEL, verbose_name='Регулировал'),
        ),
    ]