from __future__ import print_function, absolute_import

from django_commander.commands import (
    MultiprocessedIterateDownloadCommand,
    cache_results,
)
from django_commander.utils import log_command
from testapp.models import Parent


class Command(MultiprocessedIterateDownloadCommand):

    parameter_names = []
    dependencies = []
    test_parameters = {}
    test_options = {}

    @staticmethod
    def add_arguments(parser):
        return parser

    def __init__(self, **options):
        super(Command, self).__init__(**options)

    def iterate(self):
        for name in ["bob", "shelly"]:
            yield [name]

    @cache_results
    def download(self, name):
        new_name = name.upper()
        return [new_name]

    @log_command
    def parse_and_save(self, name, new_name):

        parent = Parent.objects.create_or_update(
            {"name": name}, {"name": new_name}, command_log=self.log
        )

    def cleanup(self, results):
        pass
