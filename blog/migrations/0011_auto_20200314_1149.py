# Generated by Django 2.2.10 on 2020-03-14 15:49

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('blog', '0010_subscriber_name'),
    ]

    operations = [
        migrations.AlterField(
            model_name='subscriber',
            name='name',
            field=models.CharField(max_length=100),
        ),
    ]
