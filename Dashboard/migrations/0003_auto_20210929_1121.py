# Generated by Django 3.2.7 on 2021-09-29 05:51

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('Dashboard', '0002_auto_20210924_0325'),
    ]

    operations = [
        migrations.CreateModel(
            name='Courses',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('course_name', models.CharField(max_length=100)),
            ],
            options={
                'ordering': ('course_name',),
            },
        ),
        migrations.RemoveField(
            model_name='grades',
            name='user',
        ),
        migrations.AlterModelOptions(
            name='profile',
            options={'ordering': ('user',)},
        ),
        migrations.RemoveConstraint(
            model_name='profile',
            name='user_course_pair_profile',
        ),
        migrations.RemoveField(
            model_name='profile',
            name='course',
        ),
        migrations.RemoveField(
            model_name='profile',
            name='role',
        ),
        migrations.DeleteModel(
            name='Grades',
        ),
        migrations.AddField(
            model_name='profile',
            name='courses',
            field=models.ManyToManyField(to='Dashboard.Courses'),
        ),
    ]