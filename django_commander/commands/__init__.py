from __future__ import print_function

from builtins import input
from builtins import str
from builtins import object

import os

from multiprocessing import Pool
from argparse import ArgumentParser

from django.conf import settings

from django_pewtils import CacheHandler, get_app_settings_folders
from pewtils import is_not_null, extract_attributes_from_folder_modules, classproperty

from django_commander.models import Command, CommandLog
from django_commander.utils import (
    MissingDependencyException,
    cache_results,
    log_command,
    command_multiprocess_wrapper,
)


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
        has_root_folder_prefix = "_".join(cls.__module__.split(".")[-2:])
        return "_".join(has_root_folder_prefix.split("_")[1:])

    @classmethod
    def create_or_modify_parser(cls, parser=None):

        if not parser:
            parser = ArgumentParser()
        if hasattr(cls, "add_arguments"):
            parser = cls.add_arguments(parser)
        parser.add_argument("--ignore_dependencies", action="store_true", default=False)
        parser.add_argument("--test", action="store_true", default=False)

        return parser

    def __init__(self, **options):

        dispatched = options.get("dispatched", False)
        if "dispatched" in list(options.keys()):
            del options["dispatched"]

        self.parameters, self.options = {}, {}
        for k, v in list(options.items()):
            if k in self.parameter_names:
                self.parameters[k] = v
            else:
                self.options[k] = v

        for default_opt in ["ignore_dependencies", "test"]:
            self.options[default_opt] = options.get(default_opt, False)

        if self.options["test"] and hasattr(self, "test_parameters"):
            self.parameters.update(self.test_parameters)
        if self.options["test"] and hasattr(self, "test_options"):
            self.options.update(self.test_options)

        if not dispatched:

            command_string = [self.parameters[p] for p in self.parameter_names]
            for k, v in list(self.options.items()):
                if type(v) != bool:
                    command_string.extend(["--{}".format(k), str(v)])
                elif v == True:
                    command_string.append("--{}".format(k))
            parser = self.create_or_modify_parser()

            skip = False
            try:
                parsed = parser.parse_args(command_string)
            except (SystemExit, TypeError):
                try:
                    parsed = parser.parse_known_args()[0]
                    print(
                        "Unable to parse arguments, using defaults and whatever was passed in manually to the function, if applicable"
                    )
                except SystemExit:
                    print(
                        "Unable to parse arguments, using defaults and whatever was passed in manually to the function, if applicable"
                    )
                    skip = True
                except Exception as e:
                    print("UNKNOWN ERROR: {}".format(e))
                    print(
                        "Unable to parse arguments, using defaults and whatever was passed in manually to the function, if applicable"
                    )
                    skip = True
            except Exception as e:
                print("UNKNOWN ERROR: {}".format(e))
                print(
                    "Unable to parse arguments, using defaults and whatever was passed in manually to the function, if applicable"
                )
                skip = True
            if not skip:
                for k, v in list(vars(parsed).items()):
                    if k in self.parameter_names and k not in list(
                        self.parameters.keys()
                    ):
                        self.parameters[k] = v
                    elif k not in self.parameter_names and k not in list(
                        self.options.keys()
                    ):
                        self.options[k] = v

        self.log = None
        self.check_dependencies(dispatched=dispatched)

        if self.options["test"]:
            path = os.path.join(settings.S3_CACHE_PATH, self.name, "test")
        else:
            path = os.path.join(settings.S3_CACHE_PATH, self.name)
        self.cache = CacheHandler(
            os.path.join(settings.S3_CACHE_PATH, "datasets"),
            hash=False,
            use_s3=settings.DJANGO_COMMANDER_USE_S3,
            aws_access=settings.AWS_ACCESS_KEY_ID,
            aws_secret=settings.AWS_SECRET_ACCESS_KEY,
            bucket=settings.S3_BUCKET,
        )

    def check_dependencies(self, dispatched=False):

        if hasattr(self, "dependencies"):
            missing = []
            for d, params in self.dependencies:
                logs = (
                    CommandLog.objects.filter(command__name=d)
                    .filter(end_time__isnull=False)
                    .filter(error__isnull=True)
                )
                for p in params:
                    if type(params[p]) == type(lambda x: x):
                        params[p] = params[p](self)
                    else:
                        params[p] = str(params[p])
                    logs = logs.filter(
                        command__parameters__regex=r"[\"']?%s[\"']?\: [\"']?%s[\"']?"
                        % (p, params[p])
                    )
                if logs.count() == 0:
                    missing.append((d, params))
            if len(missing) > 0 and not self.options["ignore_dependencies"]:
                if dispatched:
                    choice = ""
                    while choice.lower() not in ["y", "n"]:
                        choice = str(
                            eval(
                                input(
                                    "Missing dependencies: %s.  Do you want to continue? (y/n) >> "
                                    % str(missing)
                                )
                            )
                        )
                    print(choice)
                    if choice.lower() == "n":
                        if self.log:
                            self.log.delete()
                        raise MissingDependencyException(
                            "Missing dependencies: %s" % str(missing)
                        )
                else:
                    raise MissingDependencyException(
                        "Missing dependencies: %s" % str(missing)
                    )

    @log_command
    def run(self):

        raise NotImplementedError


class DownloadIterateCommand(BasicCommand):
    def __init__(self, **options):

        super(DownloadIterateCommand, self).__init__(**options)

    @classmethod
    def create_or_modify_parser(cls, parser=None):

        parser = super(DownloadIterateCommand, cls).create_or_modify_parser(
            parser=parser
        )
        parser.add_argument("--refresh_cache", action="store_true", default=False)

        return parser

    def download(self, *args, **options):
        """
        :return: Must return a single list of values that will be passed as positional arguments to iterate
        """
        raise NotImplementedError

    def iterate(self, *args, **options):
        """
        :param args: Passed from the download function
        :return: Iterate must yield lists of parameters, each of which will be passed as positional arguments to parse_and_save
        """
        raise NotImplementedError

    def parse_and_save(self, *args, **options):
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
        for iargs in self.iterate(*dargs):
            if any([is_not_null(a) for a in iargs]):
                self.parse_and_save(*iargs)
        self.cleanup()

    def cleanup(self):

        raise NotImplementedError


class IterateDownloadCommand(BasicCommand):
    def __init__(self, **options):

        super(IterateDownloadCommand, self).__init__(**options)

    @classmethod
    def create_or_modify_parser(cls, parser=None):

        parser = super(IterateDownloadCommand, cls).create_or_modify_parser(
            parser=parser
        )
        parser.add_argument("--refresh_cache", action="store_true", default=False)

        return parser

    def iterate(self, *args, **options):
        """
        :return:
        """
        raise NotImplementedError

    def download(self, *args, **options):
        """
        :param args:
        :return:
        """
        raise NotImplementedError

    def parse_and_save(self, *args, **options):
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
            if any([is_not_null(a) for a in dargs]):
                try:
                    self.parse_and_save(*(dargs + iargs))
                except TypeError:
                    print("Outdated cache, refreshing data")
                    dargs = self.download(*iargs, **{"refresh_data": True})
                    if any([is_not_null(a) for a in dargs]):
                        self.parse_and_save(*(dargs + iargs))

        self.cleanup()

    def cleanup(self):

        raise NotImplementedError


class MultiprocessedIterateDownloadCommand(BasicCommand):
    def __init__(self, **options):

        super(MultiprocessedIterateDownloadCommand, self).__init__(**options)

    @classmethod
    def create_or_modify_parser(cls, parser=None):

        parser = super(
            MultiprocessedIterateDownloadCommand, cls
        ).create_or_modify_parser(parser=parser)
        parser.add_argument("--refresh_cache", action="store_true", default=False)

        return parser

    def iterate(self, *args, **options):
        """
        :return:
        """
        raise NotImplementedError

    def download(self, *args, **options):
        """
        :param args:
        :return:
        """
        raise NotImplementedError

    def parse_and_save(self, *args, **options):
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
                pargs = (
                    [self.name]
                    + [self.parameters]
                    + [self.options]
                    + list(dargs)
                    + list(iargs)
                )
                if (
                    "test" in list(self.options.keys()) and self.options["test"]
                ) or self.options["num_cores"] == 1:
                    # pool.apply(command_multiprocess_wrapper, args=pargs)
                    command_multiprocess_wrapper(*pargs)
                else:
                    results.append(
                        pool.apply_async(command_multiprocess_wrapper, args=pargs)
                    )
        pool.close()
        pool.join()
        self.process_results(results)

    def cleanup(self):

        raise NotImplementedError


class MultiprocessedDownloadIterateCommand(BasicCommand):
    def __init__(self, **options):

        super(MultiprocessedDownloadIterateCommand, self).__init__(**options)

    @classmethod
    def create_or_modify_parser(cls, parser=None):

        parser = super(
            MultiprocessedDownloadIterateCommand, cls
        ).create_or_modify_parser(parser=parser)
        parser.add_argument("--refresh_cache", action="store_true", default=False)

        return parser

    def download(self, *args, **options):
        raise NotImplementedError

    def iterate(self, *args, **options):
        raise NotImplementedError

    def parse_and_save(self, *args, **options):
        raise NotImplementedError

    @log_command
    def run(self):

        self.check_dependencies()
        dargs = self.download()
        results = []
        pool = Pool(processes=self.options["num_cores"])
        for iargs in self.iterate(*dargs):
            iargs = [self.name] + [self.parameters] + [self.options] + list(iargs)
            if (
                "test" in list(self.options.keys()) and self.options["test"]
            ) or self.options["num_cores"] == 1:
                # pool.apply(command_multiprocess_wrapper, args=iargs)
                command_multiprocess_wrapper(*iargs)
            else:
                results.append(
                    pool.apply_async(command_multiprocess_wrapper, args=iargs)
                )
        pool.close()
        pool.join()
        self.process_results(results)

    def cleanup(self):

        raise NotImplementedError


commands = {}
for dir in get_app_settings_folders("DJANGO_COMMANDER_COMMAND_FOLDERS"):
    commands.update(
        extract_attributes_from_folder_modules(
            dir, "Command", include_subdirs=True, concat_subdir_names=True
        )
    )
