# Generated by Django 3.2.7 on 2021-11-12 14:02

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('Dashboard', '0018_profile_email_id'),
    ]

    operations = [
        migrations.CreateModel(
            name='AssignmentCompleted',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('isCompleted', models.BooleanField(default=False)),
                ('assignment', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='Dashboard.assignments')),
                ('enrollment', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='Dashboard.enrollment')),
            ],
        ),
    ]
