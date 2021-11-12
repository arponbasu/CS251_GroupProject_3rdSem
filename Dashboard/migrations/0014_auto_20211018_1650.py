# Generated by Django 3.2.7 on 2021-10-18 16:50

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('Dashboard', '0013_merge_0010_feedback_0012_auto_20211018_1145'),
    ]

    operations = [
        migrations.AddField(
            model_name='assignmentfiles',
            name='feedback',
            field=models.CharField(blank=True, default='No feedback yet', max_length=100, null=True),
        ),
        migrations.AddField(
            model_name='assignmentfiles',
            name='grade',
            field=models.CharField(blank=True, default='Not graded yet', max_length=100, null=True),
        ),
        migrations.AddField(
            model_name='assignmentfiles',
            name='profile',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, to='Dashboard.profile'),
        ),
        migrations.DeleteModel(
            name='Feedback',
        ),
    ]