import sys, datetime, traceback, copy
from optparse import NO_DEFAULT, OptionParser
from importlib import import_module

from django.conf import settings
from django.core.management.base import (
    CommandError,
    BaseCommand,
    handle_default_options,
)

from django_pewtils import get_model

from django_commander.utils import SubcommandDispatcher
from django_commander.commands import commands
from django_commander.utils import run_command_task


class Subcommand(BaseCommand):
    def __init__(self, subcommand, *args, **kwargs):

        self.subcommand_name = subcommand
        super(Subcommand, self).__init__(*args, **kwargs)

    def create_parser(self, prog_name, subcommand):

        parser = super(Subcommand, self).create_parser(prog_name, subcommand)
        parser = commands[self.subcommand_name].create_or_modify_parser(parser)

        return parser

    def handle(self, *args, **options):

        celery_task = run_command_task.apply_async(
            (self.subcommand_name, options), queue="celery"
        )
        log = (
            get_model("Command", app_name="django_commander")
            .objects.get(name__endswith=self.subcommand_name)
            .logs.order_by("-start_time")[0]
        )
        log.celery_task_id = celery_task.task_id
        log.save()


class Command(SubcommandDispatcher):

    subcommands = list(commands.keys())
    custom_commander = Subcommand
