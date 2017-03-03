import sys, datetime, traceback, copy
from optparse import NO_DEFAULT, OptionParser
from importlib import import_module

from django.core.management.base import CommandError, BaseCommand, handle_default_options

from django_commander.utils import get_project_commands

from pewtils.django.subcommands import SubcommandDispatcher


class Subcommand(BaseCommand):

    def __init__(self, subcommand, *args, **kwargs):

        self.subcommand_name = subcommand
        self.commands = get_project_commands()
        super(Subcommand, self).__init__(*args, **kwargs)

    def create_parser(self, prog_name, subcommand):

        parser = super(Subcommand, self).create_parser(prog_name, subcommand)
        for xparam in self.commands[self.subcommand_name].parameter_defaults:

            param = copy.copy(param)
            name = param.pop("name")
            if param['default'] == None:
                param['type'] = str
            else:
                param['type'] = type(param['default'])
            parser.add_argument("{0}".format(name), **param)

        for opt in self.commands[self.subcommand_name].option_defaults:

            opt = copy.copy(opt)
            name = opt.pop("name")
            if opt['default'] == None:
                opt['type'] = str
            else:
                opt['type'] = type(opt['default'])

            if opt['type'] == bool:
                del opt['type']
                if opt['default']:
                    parser.add_argument("--{0}".format(name), action="store_false", **opt)
                else:
                    parser.add_argument("--{0}".format(name), action="store_true", **opt)
            elif "nargs" in opt:
                parser.add_argument("{0}".format(name), **opt)
            else:
                parser.add_argument("--{0}".format(name), **opt)

        parser.add_argument("--ignore_dependencies", action="store_true", default=False)

        return parser

    def handle(self, *args, **options):

        d = self.commands[self.subcommand_name](**options)
        d.run()


class Command(SubcommandDispatcher):

    subcommands = get_project_commands().keys()
    custom_commander = Subcommand