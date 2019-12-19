# Generated by Django 2.2.6 on 2019-10-28 14:10

import django.contrib.postgres.fields.jsonb
import datetime
from django.core.serializers.json import DjangoJSONEncoder
from django.db import migrations


def convert_parameters_to_json(apps, schema_editor):
    Command = apps.get_model("django_commander", "Command")
    for command in Command.objects.all():
        params = eval(command.parameters_old)
        command.parameters = params
        command.save()


def convert_options_to_json(apps, schema_editor):
    CommandLog = apps.get_model("django_commander", "CommandLog")
    for log in CommandLog.objects.all():
        opts = eval(log.options_old)
        log.options = opts
        log.save()


class Migration(migrations.Migration):

    dependencies = [("django_commander", "0004_auto_20190930_1957")]

    operations = [
        migrations.RenameField(
            model_name="command", old_name="parameters", new_name="parameters_old"
        ),
        migrations.AddField(
            model_name="command",
            name="parameters",
            field=django.contrib.postgres.fields.jsonb.JSONField(
                default=dict,
                help_text="The parameters used to initialize the command",
                encoder=DjangoJSONEncoder,
            ),
        ),
        migrations.RunPython(convert_parameters_to_json),
        # migrations.RemoveField(model_name="commandlog", name="parameters_old"),
        migrations.RenameField(
            model_name="commandlog", old_name="options", new_name="options_old"
        ),
        migrations.AddField(
            model_name="commandlog",
            name="options",
            field=django.contrib.postgres.fields.jsonb.JSONField(
                default=dict,
                help_text="The options passed to the command",
                encoder=DjangoJSONEncoder,
            ),
        ),
        migrations.RunPython(convert_options_to_json),
        # migrations.RemoveField(model_name="commandlog", name="options_old"),
    ]
