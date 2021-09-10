import traceback, datetime, os

from tqdm import tqdm
from multiprocessing import Process

try:
    from inspect import signature
except ImportError:
    from funcsigs import signature

from pewtils import is_not_null
from django_pewtils import reset_django_connection, get_model

from django_commander.models import Command, CommandLog


class MissingDependencyException(Exception):
    pass


def run_command_task(*args, **kwargs):
    """
    DEPRECATED
    """
    print(
        "django_commander.utils.run_command_task iss deprecated, please use django_commander.utils.run_command_async"
    )


def run_command_async(command_name, **params):

    """
    Run a command asynchronously as a subprocess
    :param command_name: Name of the command
    :param params: Parameters and options, passed as kwargs
    :return:
    """

    settings_module = os.environ["DJANGO_SETTINGS_MODULE"]
    p = Process(
        target=_command_wrapper, args=(settings_module, command_name), kwargs=params
    )
    p.start()


def _command_wrapper(settings_module, command_name, **params):

    import os, django

    os.environ["DJANGO_SETTINGS_MODULE"] = settings_module
    django.setup()
    from django_commander.commands import commands

    commands[command_name](**params).run()


def log_command(handle):
    def wrapper(self, *args, **options):
        if "num_cores" in self.options and self.options["num_cores"] > 1:
            reset_django_connection()
        self.command = Command.objects.create_or_update(
            {"name": self.name, "parameters": self.parameters}
        )
        option_subset = {}
        for k, v in self.options.items():
            if k not in [
                "no_color",
                "settings",
                "traceback",
                "verbosity",
                "pythonpath",
                "force_color",
            ]:
                option_subset[k] = v
        self.log = CommandLog.objects.create(
            command=self.command, options=option_subset
        )
        self.log_id = int(self.log.pk)
        try:
            result = handle(self, *args, **options)
            if "num_cores" in self.options and self.options["num_cores"] > 1:
                reset_django_connection()
            if self.log:
                self.log.end_time = datetime.datetime.now()
                try:
                    self.log.save()
                except:
                    # sometimes for really long-standing processes, there's a timeout SSL error
                    # so, we'll just fetch the log object again before saving and closing out
                    reset_django_connection()
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
        A decorator that can be added to the `download` function on a `DownloadIterateCommand` or
        `IterateDownloadCommand`. Caches the results either locally or in S3 based on your settings.
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
                "Refreshing cached data from source for command '{}.{}'".format(
                    str(self.__class__.name), str(func.__name__)
                )
            )
            data = func(self, *args)
            self.cache.write(hashstr, data)

        return data

    return wrapper


def command_multiprocess_wrapper(command_name, parameters, options, *args):

    """
    Decorator that resets Django connections for multiprocessing

    :param command_name: Name of the command
    :param parameters: Command parameters
    :param options: Command options
    :param args: Additional arguments

    :return:
    """

    params = {}
    params.update(parameters)
    params.update(options)
    # if not params.get("test", False):
    reset_django_connection()
    from django_commander.commands import commands

    return commands[command_name](**params).parse_and_save(*args)


def test_commands():

    """
    Loops over all commands, and runs any that have defined `test_parameters`.
    """

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
    """
    Clears out extra logs in the database for commands that didn't log an end time.
    """

    for command in tqdm(Command.objects.all(), desc="Clearing extra logs"):
        command.logs.filter(error__isnull=False).delete()
        command.logs.filter(end_time__isnull=True).delete()
        if command.logs.count() == 0:
            command.delete()


def compile_parser_from_function(parser, func):

    """
    Iterates over all of the arguments and keyword arguments defined in a given function and adds them to an argparse
    parser. Assumes that required (non-keyword) arguments are strings, and that boolean keyword arguments are False
    by default. Detects the type of other keyword arguments based on their specified defaults.

    # TODO: kwargs with default=None don't know what type to case; only way to fix this is with Python 3 type annotations

    :param parser:
    :param func:
    :return:
    """

    for param in signature(func).parameters.values():

        if param.default == param.empty:
            parser.add_argument(param.name, type=str)
        elif isinstance(param.default, bool):
            parser.add_argument(
                "--{}".format(param.name), action="store_true", default=param.default
            )
        elif isinstance(param.default, None):
            parser.add_argument("--{}".format(param.name), type=str, default=None)
        else:
            parser.add_argument(
                "--{}".format(param.name),
                type=type(param.default),
                default=param.default,
            )

    return parser
