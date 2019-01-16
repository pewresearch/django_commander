from __future__ import print_function
from tqdm import tqdm

from django_commander.models import Command
from django_commander.commands import BasicCommand


class Command(BasicCommand):

    """
    """

    parameter_names = []
    dependencies = []

    def run(self):

        for command in tqdm(Command.objects.all(), desc="Clearing extra logs"):
            try:
                command.logs.filter(error__isnull=False).delete()
                if command.logs.count() == 0:
                    command.delete()
                else:
                    finished_logs = command.logs.filter(end_time__isnull=False)
                    if finished_logs.count() > 0:
                        keeper = finished_logs.order_by("-end_time")[0]
                    else:
                        keeper = command.logs.order_by("-start_time")[0]
                        command.logs.exclude(pk=keeper.pk).delete()
            except Exception as e:
                print(command)
                print(e)