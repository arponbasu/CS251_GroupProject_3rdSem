# Generated by Django 3.2.7 on 2021-10-18 11:45

import Dashboard.models
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('Dashboard', '0011_auto_20211018_1126'),
    ]

    operations = [
        migrations.AddField(
            model_name='assignmentfiles',
            name='file_name',
            field=models.CharField(default='files/vedang', max_length=100),
        ),
        migrations.AlterField(
            model_name='assignmentfiles',
            name='file',
            field=models.FileField(upload_to=Dashboard.models.getFileName),
        ),
    ]