# -*- coding: utf-8 -*-
# Generated by Django 1.11.8 on 2017-12-21 11:21
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('django_commander', '0002_commandlog_celery_task_id'),
    ]

    operations = [
        migrations.AlterField(
            model_name='commandlog',
            name='celery_task_id',
            field=models.TextField(null=True),
        ),
    ]
