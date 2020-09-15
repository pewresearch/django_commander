from __future__ import print_function

from builtins import input
from builtins import str
from builtins import object

import os
import re

from multiprocessing import Pool
from argparse import ArgumentParser
from difflib import SequenceMatcher

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
    The base `django_commander` command class.
    """

    @classproperty
    def name(cls):

        """
        Detects the name of the current command by it's file's name and location
        :return: Name of the command
        """

        module_name = "_".join(cls.__module__.split("."))
        for dir in sorted(
            settings.DJANGO_COMMANDER_COMMAND_FOLDERS,
            key=lambda x: len(x),
            reverse=True,
        ):
            dir = dir.replace("/", "_")
            d = SequenceMatcher(None, dir, module_name)
            i, j, k = max(d.get_matching_blocks(), key=lambda x: x[2])
            match = dir[i : i + k]
            if module_name.startswith(match) and dir.endswith(match):
                module_name = re.sub(match, "", module_name).strip("_")
                break
        return module_name

        # has_root_folder_prefix = "_".join(cls.__module__.split(".")[2:])
        # return has_root_folder_prefix
        # # return "_".join(has_root_folder_prefix.split("_")[1:])

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

        """
        Initializes the command and parses the parameters and options, checks for dependencies, and initializes
        a file cache.
        :param options:
        """

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
                        "Unable to parse arguments, using defaults and whatever was passed in manually to the "
                        "function, if applicable"
                    )
                except SystemExit:
                    print(
                        "Unable to parse arguments, using defaults and whatever was passed in manually to the "
                        "function, if applicable"
                    )
                    skip = True
                except Exception as e:
                    print("UNKNOWN ERROR: {}".format(e))
                    print(
                        "Unable to parse arguments, using defaults and whatever was passed in manually to the "
                        "function, if applicable"
                    )
                    skip = True
            except Exception as e:
                print("UNKNOWN ERROR: {}".format(e))
                print(
                    "Unable to parse arguments, using defaults and whatever was passed in manually to the "
                    "function, if applicable"
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
            path = os.path.join(settings.DJANGO_COMMANDER_S3_CACHE_PATH, self.name, "test")
        else:
            path = os.path.join(settings.DJANGO_COMMANDER_S3_CACHE_PATH, self.name)
        self.cache = CacheHandler(
            os.path.join(settings.DJANGO_COMMANDER_S3_CACHE_PATH, "datasets"),
            hash=False,
            use_s3=settings.DJANGO_COMMANDER_USE_S3,
            aws_access=settings.AWS_ACCESS_KEY_ID,
            aws_secret=settings.AWS_SECRET_ACCESS_KEY,
            bucket=settings.S3_BUCKET,
        )

    def check_dependencies(self, dispatched=False):

        """
        If the class has a `dependencies` attribute, then it loops over it and checks the database for each command
        listed as a dependency (along with specific parameters) to make sure that the required commands have been
        executed successfully. If you're running the command from the shell (instead of programmatically), it'll
        pause and explicitly ask for permission to continue if not all dependencies have been run.

        :param dispatched: Whether the current running command was dispatched via the command line or not
        """

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
        """
        Placeholder for the command's actual code
        """

        raise NotImplementedError


class DownloadIterateCommand(BasicCommand):

    """
    This command class is designed to first load/download some sort of file, iterate over it, and then do something with
    each value. Accordingly, it requires four functions to be defined:

    - `download`: Loads something and returns it. This function can be wrapped with the `@cache_results` decorator,
    which can save the returned result locally or in Amazon S3. When this is enabled, you can pass the option
    `--refresh_cache` to the command (this option exists on all commands by default) and it will refresh, otherwise
    the cached version will be used. This can be useful if you're downloading large files.
    - `iterate`: A function whose arguments should correspond to the value(s) returned by the `download` command. This
    function is expected to operate as an iterable, yielding objects to be processed.
    - `parse_and_save`: A function whose arguments should correspond to the value(s) being yielded by the `iterate`
    command. This function should process each object, save things to the database, etc. No return value is expected.
    - `cleanup`: A function that gets run after everything has finished. It's required, but you can just put `pass`
    there if there's no additional work to be done.

    An example of when this type of command might be useful would be for a command that downloads a roster of
    politicians, iterates over each row in the roster, and then looks up and updates information about the politician
    in each row.
    """

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
        :return: Iterate must yield lists of parameters, each of which will be passed as positional arguments to
        parse_and_save
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

    """
    This type of command operates in the opposite manner as `DownloadIterateCommand`. It expects to loop over something
    (like a list of IDs) and download/load something for each of the yielded values. The results, in turn, are each
    processed by the `parse_and_save` function. For instances of this class, the `@cache_results` decorator should also
    be used on the `download` function, with the only difference being that this class will result in multiple cached
    files, one for each of the values passed to `download`. Once again, `--refresh_cache` will ignore any cached files.
    An example of when this type of command might be useful would be a command that loops over politician objects
    that are stored in a database, downloads the Wikipedia page for each politician, and then saves each pages in the
    database. The required functions are:

    - `iterate`: A function that iterates over a list of some sort and yields values.
    - `download`: Arguments correspond to the values yielded by `iterate`; this function should fetch some data and
    return it. Can be wrapped with the `@cache_results` decorator, which can save the returned result locally or in
    Amazon S3. When this is enabled, you can pass the option `--refresh_cache` to the command (this option exists on
    all commands by default) and it will refresh, otherwise the cached version will be used. This can be useful if
    you're downloading large files.
    - `parse_and_save`: A function whose arguments should correspond first to the values(s) yielded by `iterate` and
    then to the value(s) returned by `download`. No return value is expected.
    - `cleanup`: A function to run after everything else has finished
    """

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
        :return: Must yield an iterable that produces lists of arguments, which will be passed to `download`
        """
        raise NotImplementedError

    def download(self, *args, **options):
        """
        :param args: Passed from the `iterate` function
        :return: Must return a single list of values that will be passed as additional arguments to `parse_and_save`
        """
        raise NotImplementedError

    def parse_and_save(self, *args, **options):
        """
        :param args: Consist of the values yielded by `iterate`, followed by the values returned by `download`
        :return: None (commits to the database)
        """
        raise NotImplementedError

    @log_command
    def run(self):

        """
        Checks dependencies, calls the iterate function.  Passes the values that are returned to download, which then
        yields one or more sets of values to parse and save, which commits to the database.  Then calls cleanup
        :return: None
        """

        self.check_dependencies()
        for iargs in self.iterate():
            dargs = self.download(*iargs)
            if any([is_not_null(a) for a in dargs]):
                try:
                    self.parse_and_save(*(dargs + iargs))
                except TypeError:
                    print("Outdated cache, refreshing data")
                    dargs = self.download(*iargs, **{"refresh_cache": True})
                    if any([is_not_null(a) for a in dargs]):
                        self.parse_and_save(*(dargs + iargs))

        self.cleanup()

    def cleanup(self):

        raise NotImplementedError


class MultiprocessedIterateDownloadCommand(BasicCommand):

    """
    A multiprocessed version of the `IterateDownloadCommand`. Functions the same way, but accepts an additional
    `num_cores` parameter (corresponding to the number of processors to use during multiprocessing) and it will apply
    the `parse_and_save` function in parallel to improve efficiency. Once all of the values have been processed by
    `parse_and_save`, the `cleanup` function will be run.

    * For the multiprocessed version of this command, `parse_and_save` can optionally return values, and `cleanup`
    will be passed a list of all of the returned values at the end of the command. Accordingly, `cleanup` must accept an
    argument.
    * Additionally, the `@log_command` must be added to `parse_and_save` to enable logging on these commands.
    """

    def __init__(self, **options):

        super(MultiprocessedIterateDownloadCommand, self).__init__(**options)

    @classmethod
    def create_or_modify_parser(cls, parser=None):

        parser = super(
            MultiprocessedIterateDownloadCommand, cls
        ).create_or_modify_parser(parser=parser)
        parser.add_argument("--refresh_cache", action="store_true", default=False)
        parser.add_argument("--num_cores", default=1, type=int)

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
        self.cleanup(results)

    def cleanup(self, results):

        raise NotImplementedError


class MultiprocessedDownloadIterateCommand(BasicCommand):

    """
    A multiprocessed version of the `DownloadIterateCommand`. Functions the same way, but accepts an additional
    `num_cores` parameter (corresponding to the number of processors to use during multiprocessing) and it will apply
    the `parse_and_save` function in parallel to improve efficiency. Once all of the values have been processed by
    `parse_and_save`, the `cleanup` function will be run.

    * For the multiprocessed version of this command, `parse_and_save` can optionally return values, and `cleanup`
    will be passed a list of all of the returned values at the end of the command. Accordingly, `cleanup` must accept an
    argument.
    * Additionally, the `@log_command` must be added to `parse_and_save` to enable logging on these commands.
    """

    def __init__(self, **options):

        super(MultiprocessedDownloadIterateCommand, self).__init__(**options)

    @classmethod
    def create_or_modify_parser(cls, parser=None):

        parser = super(
            MultiprocessedDownloadIterateCommand, cls
        ).create_or_modify_parser(parser=parser)
        parser.add_argument("--refresh_cache", action="store_true", default=False)
        parser.add_argument("--num_cores", default=1, type=int)

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
        self.cleanup(results)

    def cleanup(self, results):

        raise NotImplementedError


commands = {}
for dir in get_app_settings_folders("DJANGO_COMMANDER_COMMAND_FOLDERS"):
    commands.update(
        extract_attributes_from_folder_modules(
            dir, "Command", include_subdirs=True, concat_subdir_names=True
        )
    )
