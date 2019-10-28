from __future__ import print_function, absolute_import

from django_commander.commands import IterateDownloadCommand, cache_results
from testapp.models import Parent


class Command(IterateDownloadCommand):

    parameter_names = []
    dependencies = []

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

    def parse_and_save(self, name, new_name):

        parent = Parent.objects.create_or_update(
            {"name": name}, {"name": new_name}, command_log=self.log
        )

    def cleanup(self):
        pass
