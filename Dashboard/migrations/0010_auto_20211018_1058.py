# Generated by Django 3.2.7 on 2021-10-18 10:58

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('Dashboard', '0009_alter_enrollment_isteacher'),
    ]

    operations = [
        migrations.AddField(
            model_name='assignmentfiles',
            name='filename',
            field=models.CharField(default='files/abracadabra', max_length=100),
        ),
        migrations.AlterField(
            model_name='assignmentfiles',
            name='file',
            field=models.FileField(upload_to=models.CharField(default='files/abracadabra', max_length=100)),
        ),
    ]
