import sys, datetime, traceback, copy
from optparse import NO_DEFAULT, OptionParser
from importlib import import_module

from django.conf import settings
from django.core.management.base import CommandError, BaseCommand, handle_default_options

from pewtils.django.subcommands import SubcommandDispatcher

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

        run_command_task.apply_async(args=(self.subcommand_name, options), queue='celery')
        

class Command(SubcommandDispatcher):

    subcommands = commands.keys()
    custom_commander = Subcommand