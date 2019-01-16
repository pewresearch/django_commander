from future import standard_library
standard_library.install_aliases()
import sys, datetime, traceback, copy
from optparse import NO_DEFAULT, OptionParser
from importlib import import_module

from django.core.management.base import CommandError, BaseCommand, handle_default_options

from django_pewtils.subcommands import SubcommandDispatcher

from django_commander.commands import commands


class Subcommand(BaseCommand):

    def __init__(self, subcommand, *args, **kwargs):

        self.subcommand_name = subcommand
        super(Subcommand, self).__init__(*args, **kwargs)

    def create_parser(self, prog_name, subcommand):

        parser = super(Subcommand, self).create_parser(prog_name, subcommand)
        parser = commands[self.subcommand_name].create_or_modify_parser(parser)

        return parser

    def handle(self, *args, **options):

        options["dispatched"] = True
        d = commands[self.subcommand_name](**options)
        d.run()


class Command(SubcommandDispatcher):

    subcommands = list(commands.keys())
    custom_commander = Subcommand