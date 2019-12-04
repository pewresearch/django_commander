from __future__ import print_function, absolute_import

from django_commander.commands import DownloadIterateCommand, cache_results
from testapp.models import Parent


class Command(DownloadIterateCommand):

    parameter_names = []
    dependencies = []
    test_parameters = {}
    test_options = {}

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

    def parse_and_save(self, name):
        Parent.objects.create_or_update({"name": name}, command_log=self.log)

    def cleanup(self):
        pass
