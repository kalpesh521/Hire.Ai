# Generated by Django 5.0 on 2024-02-24 07:22

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('app', '0004_delete_interview'),
    ]

    operations = [
        migrations.CreateModel(
            name='UserDetails',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('role', models.CharField(choices=[('', '')], max_length=100)),
                ('experience', models.CharField(choices=[('', '')], max_length=100)),
                ('skills', models.CharField(choices=[('', '')], max_length=100)),
            ],
        ),
    ]
