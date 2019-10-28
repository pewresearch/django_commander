from __future__ import print_function, absolute_import

from django_commander.commands import (
    MultiprocessedDownloadIterateCommand,
    cache_results,
)
from django_commander.utils import log_command
from testapp.models import Parent


class Command(MultiprocessedDownloadIterateCommand):

    parameter_names = []
    dependencies = []
    test_parameters = {}
    test_options = {"num_cores": 1}

    @staticmethod
    def add_arguments(parser):
        return parser

    def __init__(self, **options):
        super(Command, self).__init__(**options)

    @cache_results
    def download(self):
        return [["bob", "shelly"]]

    def iterate(self, names):
        for name in names:
            yield [name]

    @log_command
    def parse_and_save(self, name):
        Parent.objects.create_or_update({"name": name}, command_log=self.log)

    def cleanup(self, results):
        pass
