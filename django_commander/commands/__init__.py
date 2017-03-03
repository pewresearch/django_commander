import pkgutil, importlib

from multiprocessing import Pool
import datetime, traceback

from pewtils.django import get_model, reset_django_connection, CacheHandler, django_multiprocessor
from pewtils import is_not_null, classproperty

from django_commander.models import Command, CommandLog
from django_commander.utils import MissingDependencyException


def log_command(handle):
    def wrapper(self, *args, **options):
        self.command = Command.objects.create_or_update({
            "name": self.name,
            "parameters": str(self.parameters)
        })
        self.log = CommandLog.objects.create(
            command=self.command,
            options=str(self.options)
        )
        self.log_id = int(self.log.pk)
        try:
            handle(self, *args, **options)
            if self.log:
                self.log.end_time = datetime.datetime.now()
                try: self.log.save()
                except:
                    # sometimes for really long-standing processes, there's a timeout SSL error
                    # so, we'll just fetch the log object again before saving and closing out
                    self.log = CommandLog.objects.get(pk=self.log_id)
                    self.log.end_time = datetime.datetime.now()
                    self.log.save()
        except Exception as e:
            tb = traceback.format_exc()
            print e
            print tb
            if self.log:
                try:
                    self.log.error = {
                        "traceback": tb,
                        "exception": e
                    }
                    self.log.save()
                except:
                    self.log.error = {
                        "traceback": str(tb),
                        "exception": str(e)
                    }
                    self.log.save()
    return wrapper


def cache_results(func):

    def wrapper(self, *args, **options):

        """
        Gets wrapped on the download function

        Uses the cache folder in the logos-data S3 bucket if ENV is set to prod or prod-read-only; otherwise it
        uses a local cache (for local/dev/test environments).  If set to prod-read-only, it doesn't save anything,
        it just loads from the prod cache.
        """

        hashstr = str(self.__class__.name) + str(func.__name__) + str(args) + str(self.parameters)
        if self.options["refresh_data"] or options.get("refresh_data"): data = None
        else: data = self.cache.read(hashstr)
        if not is_not_null(data) or self.options["refresh_data"] or options.get("refresh_data", False):
            print "Refreshing data from source for downcommand '%s.%s'" % (str(self.__class__.name), str(func.__name__))
            data = func(self, *args)
            self.cache.write(hashstr, data)

        return data

    return wrapper


class BasicCommand(object):

    """
    All Basic commands require an init function that have the following
         self.name
         option_default key, value tuples
         parameter defaults key, value tuples
         self.options   ( Passed in variables with names in option defaults override the defaults )
            options have no bearing on what gets downloaded rather how its gets processed
         self.parameters ( Passed in variables with names in option defaults override the defaults )
            parameters are for pulling and processing

         self.dependencies : list of  tuple of the name, paraemeters dictionary
         self.command = None

    required methods --  most be defined on every subclass

    download
    iterate
    parse_and_save
    cleanup ( can be blank )

    """

    @classproperty
    def name(cls):
        return "_".join(cls.__module__.split(".")[-2:])

    def __init__(self, *args, **options):

        self.options = {o['name']: options.get(o['name'], o['default']) for o in self.option_defaults}
        self.parameters = {p['name']: options.get(p['name'], p['default']) for p in self.parameter_defaults}
        self.log = None
        self.options["ignore_dependencies"] = options.get("ignore_dependencies", False)
        self.check_dependencies()
        # self.cache_identifier = self.name + str(self.parameters)
        self.cache = CacheHandler("commands/{}".format(self.name))

    def check_dependencies(self):

        if hasattr(self, "dependencies"):
            missing = []
            for d, params in self.dependencies:
                logs = CommandLog.objects.filter(command__name=d).filter(end_time__isnull=False).filter(error__isnull=True)
                for p in params:
                    if type(params[p]) == type(lambda x: x):
                        params[p] = params[p](self)
                    else:
                        params[p] = str(params[p])
                    #logs = logs.filter(args__regex="%s" % str(params[p]))
                    logs = logs.filter(command__parameters__regex=r"[\"']?%s[\"']?\: [\"']?%s[\"']?" % (p, params[p]))
                if logs.count() == 0:
                    missing.append((d, params))
            if len(missing) > 0 and not self.options["ignore_dependencies"]:
                choice = ""
                while choice.lower() not in ["y", "n"]:
                    choice = str(raw_input("Missing dependencies: %s.  Do you want to continue? (y/n) >> " % str(missing)))
                print choice
                if choice.lower() == "n":
                    if self.log:
                        self.log.delete()
                    raise MissingDependencyException("Missing dependencies: %s" % str(missing))

    def run(self):

        raise NotImplementedError

    def cleanup(self):

        raise NotImplementedError


class DownloadIterateLoader(BasicCommand):

    def download(self, **options):
        """
        :return: Must return a single list of values that will be passed as positional arguments to iterate
        """
        raise NotImplementedError

    def iterate(self, *args):
        """
        :param args: Passed from the download function
        :return: Iterate must yield lists of parameters, each of which will be passed as positional arguments to parse_and_save
        """
        raise NotImplementedError

    def parse_and_save(self, *args):
        """
        :param args: Passed from the iterate function
        :return: None (commits to the database)
        """
        raise NotImplementedError

    @log_command
    def run(self):
        """
        Checks dependencies, calls the download function.  Passes the values that are returned to iterate, which then
        yields one or more sets of values to parse and save, which commits to the database.  Then calls cleanup
        :return: None
        """
        self.check_dependencies()
        dargs = self.download()
        # if type(dargs) != list: dargs = [dargs, ]
        for iargs in self.iterate(*dargs):
            if any([is_not_null(a) for a in iargs]):
                self.parse_and_save(*iargs)
        self.cleanup()

    def check_rows(self):
        raise NotImplementedError


class IterateDownloadLoader(BasicCommand):

    def iterate(self):
        """
        :return:
        """
        raise NotImplementedError

    def download(self, *args):
        """
        :param args:
        :return:
        """
        raise NotImplementedError

    def parse_and_save(self, *args):
        """
        :param args:
        :return:
        """
        raise NotImplementedError

    @log_command
    def run(self):

        self.check_dependencies()
        for iargs in self.iterate():
            dargs = self.download(*iargs)
            # if type(dargs) != list: dargs = [dargs, ]
            if any([is_not_null(a) for a in dargs]):
                try: self.parse_and_save(*(dargs + iargs))
                except TypeError:
                    print "Outdated cache, refreshing data"
                    dargs = self.download(*iargs, **{"refresh_data": True})
                    if any([is_not_null(a) for a in dargs]):
                        self.parse_and_save(*(dargs + iargs))

        self.cleanup()


class MultiprocessedIterateDownloadLoader(BasicCommand):

    def iterate(self):
        """
        :return:
        """
        raise NotImplementedError

    def download(self, *args):
        """
        :param args:
        :return:
        """
        raise NotImplementedError

    def parse_and_save(self, *args):
        """
        :param args:
        :return:
        """
        raise NotImplementedError

    @log_command
    def run(self):

        self.check_dependencies()
        results = []
        pool = Pool(processes=self.options["num_cores"])
        for iargs in self.iterate():
            dargs = self.download(*iargs)
            if any([is_not_null(a) for a in dargs]):
                pargs = [self.name] + [self.parameters] + [self.options] + list(dargs) + list(iargs)
                if 'test' in self.options.keys() and self.options['test']:
                    pool.apply(command_multiprocess_wrapper, args=pargs)
                else:
                    results.append(pool.apply_async(command_multiprocess_wrapper, args=pargs))
        pool.close()
        pool.join()
        self.process_results(results)

    def process_results(self, results):
        """
        Processing that you want to happen at the end of the run.
        """

        raise NotImplementedError


class MultiprocessedDownloadIterateLoader(BasicCommand):

    def download(self, **options):
        raise NotImplementedError

    def iterate(self, *args):
        raise NotImplementedError

    def parse_and_save(self, *args):
        raise NotImplementedError

    @log_command
    def run(self):

        self.check_dependencies()
        dargs = self.download()
        results = []
        pool = Pool(processes=self.options["num_cores"])
        for iargs in self.iterate(*dargs):
            iargs = [self.name] + [self.parameters] + [self.options] + list(iargs)
            if 'test' in self.options.keys() and self.options['test']:
                pool.apply(command_multiprocess_wrapper, args=iargs)
            else:
                results.append(pool.apply_async(command_multiprocess_wrapper, args=iargs))
        pool.close()
        pool.join()
        self.process_results(results)

    def process_results(self, results):
        """
        Processing that you want to happen at the end of the run.
        """

        raise NotImplementedError


def command_multiprocess_wrapper(command_name, parameters, options, *args):

    params = {}
    params.update(parameters)
    params.update(options)
    reset_django_connection()
    from logos.commands import commands
    return commands[command_name](**params).parse_and_save(*args)





# import pkgutil, importlib
# from django.conf import settings
#
#
# path = settings.DJANGO_COMMANDER_COMMAND_DIR
# i = 0
# path_split = path.split("/")
# while path_split[i] != settings.SITE_NAME: i += 1
# name = ".".join(path_split[i:])
#
# print path
# print name
#
# commands = {}
# path = pkgutil.extend_path(path, name)
# for importer, modname, ispkg in pkgutil.walk_packages(path=path, prefix=name + '.'):
#     print modname
#     if not ispkg:
#         print "woot"
#         module = importlib.import_module(modname)
#         if hasattr(module, "Command"):
#             print "wootier"
#             command = getattr(module, "Command")
#             commands[command.name] = command