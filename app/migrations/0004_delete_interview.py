# Generated by Django 5.0 on 2024-01-30 05:55

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('app', '0003_alter_audiofile_id'),
    ]

    operations = [
        migrations.DeleteModel(
            name='Interview',
        ),
    ]
