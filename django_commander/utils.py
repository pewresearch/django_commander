import traceback, datetime, sys

from optparse import NO_DEFAULT
from importlib import import_module
from celery import shared_task

from django.core.management.base import CommandError, BaseCommand

from pewtils import is_not_null
from django_pewtils import detect_primary_app, reset_django_connection

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
            {"name": self.name, "parameters": str(self.parameters)}
        )
        self.log = CommandLog.objects.create(
            command=self.command, options=str(self.options)
        )
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
        if self.options["refresh_data"] or options.get("refresh_data"):
            data = None
        else:
            data = self.cache.read(hashstr)
        if (
            not is_not_null(data)
            or self.options["refresh_data"]
            or options.get("refresh_data", False)
        ):
            print(
                "Refreshing data from source for command '%s.%s'"
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
    reset_django_connection()
    from django_commander.commands import commands

    return commands[command_name](**params).parse_and_save(*args)


def test_commands():

    from django_commander.commands import commands

    for command_name in list(commands.keys()):
        params = {"test": True}
        if hasattr(commands[command_name], "test_options") or hasattr(
            commands[command_name], "test_parameters"
        ):
            if hasattr(commands[command_name], "test_options"):
                params.update(commands[command_name].test_options)
            if hasattr(commands[command_name], "test_parameters"):
                params.update(commands[command_name].test_parameters)
        commands[command_name](**params).run()


class SubcommandDispatcher(BaseCommand):

    """
    A wrapper for subcommands; looks in the subcommand directory for a folder and file based on the passed parameters.
    Modified by borrowed from Django Subcommander repository: https://github.com/erikrose/django-subcommander
    """

    help = "A wrapper for subcommands"

    subcommands = []
    custom_commander = None

    import_template = (
        "{app_name}.management.subcommands.{dispatcher_name}.{module_name}"
    )

    def __init__(self):
        self.app_name = detect_primary_app()
        super(SubcommandDispatcher, self).__init__()

    def print_subcommands(self, prog_name):
        usage = ["", "Available subcommands:"]
        for name in sorted(self.subcommands):
            usage.append("  {0}".format(name))
        return "\n".join(usage)

    def usage(self, subcommand):
        usage = "%prog {0} subcommand [options] [args]".format(subcommand)
        if self.help:
            return "{0}\n\n{1}".format(usage, self.help)
        return usage

    def print_help(self, prog_name, subcommand):
        super(SubcommandDispatcher, self).print_help(prog_name, subcommand)
        sys.stdout.write("{0}\n\n".format(self.print_subcommands(prog_name)))

    def get_subcommand(self, dispatcher, subcommand):

        if self.custom_commander:
            return self.custom_commander(subcommand)
        else:
            try:
                module = import_module(
                    self.import_template.format(
                        app_name=self.app_name,
                        dispatcher_name=dispatcher,
                        module_name=subcommand,
                    )
                )
                return module.Command()
            except KeyError:
                raise CommandError(
                    "Unknown subcommand: {0} {1}".format(self.app_name, subcommand)
                )

    def run_from_argv(self, argv):

        # Set up any environment changes requested (e.g., Python path and Django settings), then run this command.
        if (
            len(argv) > 2
            and not argv[2].startswith("-")
            and argv[2] in self.subcommands
        ):
            dispatcher = argv[1]
            subcommand = argv[2]
            klass = self.get_subcommand(dispatcher, subcommand)
            klass.run_from_argv(argv[1:])
        else:
            super(SubcommandDispatcher, self).run_from_argv(argv)

    def handle(self, *args, **options):
        if not args or args[0] not in self.subcommands:
            return self.print_help("./manage.py", self.app_name)
        subcommand, args = args[0], args[1:]

        klass = self.get_subcommand(subcommand)
        # Grab out a list of defaults from the options. optparse does this for
        # us when the script runs from the command line, but since
        # call_command can be called programatically, we need to simulate the
        # loading and handling of defaults (see #10080 for details).
        defaults = {}
        for opt in klass.option_list:
            if opt.default is NO_DEFAULT:
                defaults[opt.dest] = None
            else:
                defaults[opt.dest] = opt.default
        defaults.update(options)

        return klass.execute(*args, **defaults)
