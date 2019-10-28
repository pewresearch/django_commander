import traceback, datetime

from celery import shared_task
from tqdm import tqdm

from pewtils import is_not_null
from django_pewtils import reset_django_connection

from django_commander.models import Command, CommandLog


class MissingDependencyException(Exception):
    pass


@shared_task
def run_command_task(command_name, params):

    try:
        from django_commander.commands import commands

        commands[command_name](**params).run()
        return "Success: {}".format(command_name)
    except Exception as e:
        return e


def log_command(handle):
    def wrapper(self, *args, **options):
        self.command = Command.objects.create_or_update(
            {"name": self.name, "parameters": self.parameters}
        )
        self.log = CommandLog.objects.create(command=self.command, options=self.options)
        self.log_id = int(self.log.pk)
        try:
            result = handle(self, *args, **options)
            if self.log:
                self.log.end_time = datetime.datetime.now()
                try:
                    self.log.save()
                except:
                    # sometimes for really long-standing processes, there's a timeout SSL error
                    # so, we'll just fetch the log object again before saving and closing out
                    self.log = CommandLog.objects.get(pk=self.log_id)
                    self.log.end_time = datetime.datetime.now()
                    self.log.save()
            return result
        except Exception as e:
            tb = traceback.format_exc()
            print(e)
            print(tb)
            if self.log:
                try:
                    self.log.error = {"traceback": tb, "exception": e}
                    self.log.save()
                except:
                    self.log.error = {"traceback": str(tb), "exception": str(e)}
                    self.log.save()
            return None

    return wrapper


def cache_results(func):
    def wrapper(self, *args, **options):

        """
        Gets wrapped on the download function

        Uses the cache folder in the logos-data S3 bucket if ENV is set to prod or prod-read-only; otherwise it
        uses a local cache (for local/dev/test environments).  If set to prod-read-only, it doesn't save anything,
        it just loads from the prod cache.
        """

        hashstr = (
            str(self.__class__.name)
            + str(func.__name__)
            + str(args)
            + str(self.parameters)
        )
        if self.options["refresh_cache"] or options.get("refresh_cache"):
            data = None
        else:
            data = self.cache.read(hashstr)
        if (
            not is_not_null(data)
            or self.options["refresh_cache"]
            or options.get("refresh_cache", False)
        ):
            print(
                "Refreshing cached data from source for command '%s.%s'"
                % (str(self.__class__.name), str(func.__name__))
            )
            data = func(self, *args)
            self.cache.write(hashstr, data)

        return data

    return wrapper


def command_multiprocess_wrapper(command_name, parameters, options, *args):

    params = {}
    params.update(parameters)
    params.update(options)
    if not params.get("test", False):
        reset_django_connection()
    from django_commander.commands import commands

    return commands[command_name](**params).parse_and_save(*args)


def test_commands():

    from django_commander.commands import commands

    for command_name in list(commands.keys()):
        params = {}
        if hasattr(commands[command_name], "test_options") or hasattr(
            commands[command_name], "test_parameters"
        ):
            if hasattr(commands[command_name], "test_options"):
                params.update(commands[command_name].test_options)
            if hasattr(commands[command_name], "test_parameters"):
                params.update(commands[command_name].test_parameters)
        params["test"] = True
        commands[command_name](**params).run()


def clear_unfinished_command_logs():

    for command in tqdm(Command.objects.all(), desc="Clearing extra logs"):
        command.logs.filter(error__isnull=False).delete()
        command.logs.filter(end_time__isnull=True).delete()
        if command.logs.count() == 0:
            command.delete()
