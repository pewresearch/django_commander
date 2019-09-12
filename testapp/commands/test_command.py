from __future__ import print_function

from django_commander.commands import BasicCommand, log_command
from testapp.models import *


class Command(BasicCommand):

    """
    """

    parameter_names = ["parent_name"]
    dependencies = []

    @staticmethod
    def add_arguments(parser):
        parser.add_argument("parent_name", type=str)
        parser.add_argument("--child_name", type=str, default=None)
        return parser

    def __init__(self, **options):

        super(Command, self).__init__(**options)

    @log_command
    def run(self):

        child_name = self.options["child_name"] if self.options["child_name"] else "child"

        # Testing Django-native way of adding a log to an object
        parent, created = Parent.objects.get_or_create(name=self.parameters["parent_name"])
        parent.command_logs.add(self.log)
        # Testing Django-Pewtils method of adding a log to an object
        child = Child.objects.create_or_update({"name": child_name, "parent": parent}, command_log=self.log)

        return (parent, child)
