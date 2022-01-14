import sys, datetime, traceback, copy
from optparse import NO_DEFAULT, OptionParser
from importlib import import_module

from django.core.management.base import (
    CommandError,
    BaseCommand,
    handle_default_options,
)

from django_pewtils import get_model

from django_commander.commands import commands


class Command(BaseCommand):

    """
    A wrapper around Django's `BaseCommand` that uses the first parameter as a namespace to look up a
    `django_commander` command and run it. Thanks to the Django Subcommander repository
    (https://github.com/erikrose/django-subcommander) for inspiration.
    """

    subcommands = list(commands.keys())

    def __init__(self, *args, **kwargs):

        self.subcommand_name = None
        super(Command, self).__init__(*args, **kwargs)

    def create_parser(self, prog_name, subcommand):

        parser = super(Command, self).create_parser(prog_name, subcommand)
        parser.add_argument("subcommand_name", type=str)
        if self.subcommand_name in commands.keys():
            parser = commands[self.subcommand_name].create_or_modify_parser(parser)

        return parser

    def run_from_argv(self, argv):

        # Set up any environment changes requested (e.g., Python path and Django settings), then run this command.
        if (
            len(argv) > 2
            and not argv[2].startswith("-")
            and argv[2] in self.subcommands
        ):
            dispatcher = argv[1]
            self.subcommand_name = argv[2]
            parser = self.create_parser("run_command", self.subcommand_name)

            if "--test" in argv[2:]:
                print("Testing {}".format(self.subcommand_name))
                print(
                    "Test parameters: {}".format(
                        commands[self.subcommand_name].test_parameters
                    )
                )
                print(
                    "Test options: {}".format(
                        commands[self.subcommand_name].test_options
                    )
                )
                new_args = argv[:3]
                for p in commands[self.subcommand_name].parameter_names:
                    new_args.append(
                        str(commands[self.subcommand_name].test_parameters[p])
                    )
                for k, v in commands[self.subcommand_name].test_options.items():
                    new_args.extend(["--{}".format(k), str(v)])
                argv = new_args

            options = {}
            for opt, val in parser.parse_args(argv[2:])._get_kwargs():
                options[opt] = val
            self.handle(**options)
        else:
            super(Command, self).run_from_argv(argv)

    def handle(self, *args, **options):

        if not self.subcommand_name:
            self.subcommand_name = options.get("subcommand_name", None)
            parser = self.create_parser("run_command", self.subcommand_name)
            for opt, val in parser.parse_args()._get_kwargs():
                if opt not in options:
                    options[opt] = val

        options["dispatched"] = True

        d = commands[self.subcommand_name](**options)
        d.run()
