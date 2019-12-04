# Django Commander

Django Commander allows you to easily create, organize, and log management commands and subcommands.
You might wonder why you may need something that goes above and beyond the traditional Django management
command system.  Here are some things that Django Commander does that you can't do with out-of-the-box Django:

1. Organize and nest your management commands into subfolders and easily access them from the command line
with no hassle
2. Automatically log commands that get run
3. Use a standardized system for loading and processing data
4. Keep track of the objects in your database that get modified by each command
5. Easily run your commands programmatically and have them return values

## Installation

### Dependencies

django_commander requires:

- Python (>= 2.7)
- Django (>= 1.10)
- Celery (>=4.0.2)
- [Pewtils (our own in-house Python utilities)](https://github.com/pewresearch/pewtils)
- [Django Pewtils (our own in-house Django utilities)](https://github.com/pewresearch/django_pewtils)

You'll need to install Pewtils and Django Pewtils in order for Django Commander to work, but other than that,
there are no special requirements.

### Setup and Configuration

First, you'll need to run migrations to get your database set up.

```
$ python manage.py migrate
```

Next, you need to specify where your commands will go in your `settings.py` file.  This is accomplished
using the `DJANGO_COMMANDER_COMMAND_FOLDERS` setting. You can organize your commands however you like, and 
place them in as many folders as you want, provided that you include their locations in this list.

```python
DJANGO_COMMANDER_COMMAND_FOLDERS = [
    os.path.abspath(os.path.join(YOUR_APP_ROOT, "commands").decode('utf-8')).replace('\\', '/'),
]
```

### Multiprocessing and Task Management

In some cases, your commands will be long-running, and you may wish to run them in parallel and/or use
a task management system to schedule and execute them rather than using cronjobs or the shell.
Django Commander comes with a convenient wrapper that can run any command as a Celery task:
`django_commander.utils.run_command_task`.  For this to work, you need to have Celery installed in your main
application.  The only settings you'll need to add in your main `settings.py` file are:

```python
CELERY_BROKER_URL = "redis://localhost:6379/0"
BROKER_URL = 'redis://127.0.0.1:6379/'
CELERY_RESULT_BACKEND = 'redis://127.0.0.1:6379/'
CELERY_ACCEPT_CONTENT = ["pickle", "json"]
CELERY_TASK_SERIALIZER = "pickle"
CELERY_RESULT_SERIALIZER = "pickle"
```

Obviously, adapt the endpoints to connect to whatever broker and backend services you want.

## Using Django Commander

### Creating and Running Commands

Now that you have a folder to hold your commands, you can create your first command. Commands can currently
inherit from the following classes, found in `django_commander.commands.__init__`:

* `BasicCommand`
* `DownloadIterateCommand`
* `IterateDownloadCommand`
* `MultiprocessedIterateDownloadCommand`
* `MultiprocessedDownloadIterateCommand`

The following is an example of a simple BasicCommand

```python
from __future__ import absolute_import
from django_commander.commands import BasicCommand
from my_app.models import MyModel


class Command(BasicCommand):

    parameter_names = ["category"]
    dependencies = [
        ("process_category", {"category": lambda x: x.parameters["category"]})
    ]
    test_parameters = {}
    test_options = {}

    @staticmethod
    def add_arguments(parser):
        parser.add_argument("category", type=int)
        parser.add_argument("--refresh_processed", action="store_true", default=False)
        return parser

    def __init__(self, *args, **kwargs):
        super(Command, self).__init__(*args, **kwargs)

    def run(self):

        objects = MyModel.objects.filter(category=self.parameters["category"])
        if not self.options["refresh_processed"]:
            objects = objects.filter(processed=False)
        # DO SOMETHING
        return objects

    def cleanup(self):

        pass

```

NOTE: in Python 2, all commands must have `from __future__ import absolute_import` at the start of the file

The name of the command will be automatically determined by its filename, and any subfolders it's nested inside. 
Commands consist of a few different components.

#### Parameters and Options

All arguments for a command are defined in an `add_arguments` function that's defined on each command class. These are 
defined just like normal Django commands, using argparse syntax. Django Commander expects this to be a `staticmethod`.

Unlike base Django, Django Commander distinguishes between `parameters` and `options`, which is useful for logging and 
tracking commands that have been run. Parameters are defined as arguments that define the core functionality of the 
command, and have no default values - they are not optional. For example, if you have a command to scrape a website, 
you may demand a parameter for the domain to be scraped. Parameters are specified by including their name in a 
`parameter_names` property on the command class. Options, on the other hand, are simply optional; in the case of a 
command to scrape a website, you might include a `--skip_existing` option to skip webpages that have already been 
scraped, for example. Within any command, you can access the values of the parameters and options via `self.parameters` 
and `self.options`, respectively.

#### Dependencies

Every command must also have a `dependencies` property defined on it. It's perfectly fine to leave this as an empty list, 
but this property can also be useful for specifying other commands that first must be run successfully before the current 
command can be executed. Dependencies can be specified by providing a list of tuples, where the first value is the 
name of the command that must be run prior to the current one, and the second value is a dictionary where the keys 
correspond to parameter names for the dependency, and the values correspond to the required parameter values. You can 
also use `lambda` functions to access the parameters on the current command (as in the example above). If a command with 
dependencies is run and its dependencies have not yet been run, a warning dialogue will appear and explicitly ask for 
the user's permission to continue. This can be useful not only for documenting the logical order in which certain 
commands can be run, but also for preventing serious errors from occurring. An example of where this could be useful 
would be two commands, where the first one loads a roster of politician social media accounts, and the second one 
downloads their latest posts. In this case, it would certainly make sense to require the list of accounts to have been 
loaded before attempting to download their posts.

#### Test Parameters and Options

All Django Commander commands include a `test` option (which is automatically defined behind-the-scenes) and the 
`test_parameters` and `test_options` properties can be defined on each command class with dictionaries of values to be 
used during testing. While custom unit tests are recommended for any important command, in many cases commands are 
used for long-running data collection processes or analysis tasks, and it can often be useful to simply know whether 
or not a command can execute successfully, without testing all of its functionality on all possible input data. To help 
with this, you can call any command with the `test` option and define test behavior within your command with conditionals 
based on the value of `self.options["test"]`. If `test_parameters` and `test_options` are defined, you don't need to 
provide any arguments of your own.

#### Organizing command logic

The most basic Django Commander command, `BasicCommand` has a single function in which to place your command logic: 
`run`. This function should contain the full script of your command.

However, Django Commander also offers more complex types of commands specifically designed to encourage a consistent 
method for working with data. These take the form of the `DownloadIterateCommand` and `IterateDownloadCommand`. Each of 
these classes inherit from `BasicCommand` but instead of a single `run` function, they require `download`, `iterate`, 
`parse_and_save`, and `cleanup` functions that are designed to handle the logic of downloading something and iterating 
over the results, or iterating over a list and downloading something for each item (two very common practices when 
loading data).

##### `DownloadIterateCommand`
This command class is designed to first load/download some sort of file, iterate over it, and then do something with 
each value. Accordingly, it requires four functions to be defined:

- `download`: Loads something and returns it. This function can be wrapped with the `@cache_results` decorator, which 
can save the returned result locally or in Amazon S3. When this is enabled, you can pass the option `--refresh_cache` to 
the command (this option exists on all commands by default) and it will refresh, otherwise the cached version will be 
used. This can be useful if you're downloading large files.
- `iterate`: A function whose arguments should correspond to the value(s) returned by the `download` command. This 
function is expected to operate as an iterable, yielding objects to be processed.
- `parse_and_save`: A function whose arguments should correspond to the value(s) being yielded by the `iterate` 
command. This function should process each object, save things to the database, etc. No return value is expected.
- `cleanup`: A function that gets run after everything has finished. It's required, but you can just put `pass` there 
if there's no additional work to be done.

An example of when this type of command might be useful would be for a command that downloads a roster of politicians, 
iterates over each row in the roster, and then looks up and updates information about the politician in each row.

Example: 
```python
import pandas as pd
from django_commander.commands import DownloadIterateCommand, cache_results
from my_app.models import MyModel

class Command(DownloadIterateCommand):

    parameter_names = []
    dependencies = []
    test_parameters = {}
    test_options = {}

    @staticmethod
    def add_arguments(parser):
        return parser

    def __init__(self, *args, **kwargs):
        super(Command, self).__init__(*args, **kwargs)

    @cache_results
    def download(self):
        df = pd.read_csv("my_csv.csv")
        return df
        
    def iterate(self, df):
        for index, row in df.iterrows():
            yield [index, row, ]
            
    def parse_and_save(self, index, row):
        MyModel.objects.create_or_update(
            {"name": row["name"]}, 
            log=self.log
        )

    def cleanup(self):
        pass
```

##### `IterateDownloadCommand`
This type of command operates in the opposite manner as `DownloadIterateCommand`. It expects to loop over something 
(like a list of IDs) and download/load something for each of the yielded values. The results, in turn, are each 
processed by the `parse_and_save` function. For instances of this class, the `@cache_results` decorator should also be 
used on the `download` function, with the only difference being that this class will result in multiple cached files, 
one for each of the values passed to `download`. Once again, `--refresh_cache` will ignore any cached files. An example 
of when this type of command might be useful would be a command that loops over politician objects that are stored in 
a database, downloads the Wikipedia page for each politician, and then saves each pages in the database. 
The required functions are:

- `iterate`: A function that iterates over a list of some sort and yields values.
- `download`: Arguments correspond to the values yielded by `iterate`; this function should fetch some data and return 
it. Can be wrapped with the `@cache_results` decorator, which can save the returned result locally or in Amazon S3. 
When this is enabled, you can pass the option `--refresh_cache` to the command (this option exists on all commands 
by default) and it will refresh, otherwise the cached version will be used. This can be useful if you're downloading 
large files.
- `parse_and_save`: A function whose arguments should correspond first to the values(s) yielded by `iterate` and then 
to the value(s) returned by `download`. No return value is expected.
- `cleanup`: A function to run after everything else has finished

```python
import pandas as pd
from django_commander.commands import DownloadIterateCommand, cache_results
from my_app.models import MyModel

class Command(DownloadIterateCommand):

    parameter_names = []
    dependencies = []
    test_parameters = {}
    test_options = {}

    @staticmethod
    def add_arguments(parser):
        return parser

    def __init__(self, *args, **kwargs):
        super(Command, self).__init__(*args, **kwargs)

    def iterate(self):
        for obj in MyModel.objects.all():
            yield [obj, ]
        
    @cache_results
    def download(self, obj):
        df = pd.read_csv("{}.csv".format(obj.pk))
        return [df, ]
            
    def parse_and_save(self, obj, df):
        for index, row in df.iterrows():
            setattr(obj, row["field"], row["value"])
        obj.save()

    def cleanup(self):
        pass
```

##### Multiprocessed commands

Django Commander also provides multiprocessed versions of the above commands: `MultiprocessedIterateDownloadCommand` 
and `MultiprocessedDownloadIterateCommand`. These function exactly the same as the commands they inherit from, but 
they accept an additional `num_cores` parameter (corresponding to the number of processors to use during 
multiprocessing) and they will apply the `parse_and_save` functions in parallel to improve efficiency. Once all of the 
values have been processed by `parse_and_save`, the `cleanup` function will be run.

* One difference between these and other commands is that `parse_and_save` can optionally return values, and `cleanup` 
will be passed a list of all of the returned values at the end of the command. Accordingly, `cleanup` must accept an 
argument.
* Additionally, the `@log_command` must be added to `parse_and_save` to enable logging on these commands.


#### Running commands

Commands can be run via `manage.py` like so:

```bash
$ python manage.py run_command my_command PARAM_VALUE --my_option OPTION_VALUE
```

Commands can be nested in as many submodules as you want, and they will always be accessible via `manage.py`
by concatenating the folder names together with underscores.  If we were to move the above command down to a
submodule, in a folder named "scrapers", we could then run it like so:

```bash
$ python manage.py run_command scrapers_my_command PARAM_VALUE --my_option OPTION_VALUE
```

#### Logging

Django Commander allows for the logging of commands in the database. To enable this functionality, you can apply the 
`@log_command` decorator to the `run` function of a `BasicCommand` (all other commands have logging enabled by default.) 
When logging is enabled, every time a command is run it creates a new object in the 
`django_commander.models.CommandLog` table. A `django_commander.models.Command` object is automatically created when a 
new command is first run, which is unique to the name of the command and the parameters that were passed to it. 
(Commands run with different _options_ are treated as the same `Command` and the different options are stored on the 
`CommandLog` table.) You can then see details on all of your commands by querying these tables, like so:

```python
from django_commander.models import Command
Command.objects.get(name="scrapers_my_command").logs.all()
```

#### LoggedExtendedModels

When logging is enabled, each `BasicCommand` or command that inherits from it will have a `self.log` property that 
corresponds to a unique object on the `CommandLog` model. When the command finishes running, this log object will note 
the time it finished and any errors that were encountered. However, Django Commander also supports the association of 
specific `CommandLog`s with any objects in the database - which can be enormously useful for tracking which objects 
have been created or modified by different commands and when. To enable this tracking on any model in your app, you 
simply need to have it inherit from `django_commander.models.LoggedExtendedModel`, which is an extension of the 
`django_pewtils` `BasicExtendedModel`. The `LoggedExtendedModel` class automatically creates relations with the 
`django_commander` `Command` and `CommandLog` models, so that your commands can create these associations while the 
execute, like so:

```python
@log_command
def run(self):
    for obj in MyModel.objects.all():
        obj.command_logs.add(self.log)
```

#### Accessing Commands Directly

Django Commander also lets you access your commands directly.  It automatically scans every Django app
you have installed, and extracts all of the command classes into a single dictionary, found in
`django_commander.commands.commands`.  You can import this from any app in your project, and run the commands
manually, if you so choose:

```python
from django_commander.commands import commands
commands["scrapers_my_command"](PARAM_VALUE, my_option=OPTION_VALUE).run()
```

Since other applications (like `django_learning`) also make use of Django Commander, it's generally best to 
namespace your commands by placing them in a folder, like `commands/my_app`.

You can also access commands through the Django ORM using the `command_class` property on the `Command` model:

```python
from django_commander.models import Command
command = Command.objects.get(name="scrapers_my_command")
command.command_class(PARAM_VALUE, my_option=OPTION_VALUE).run()
print(command.logs.order_by("-end_time")[0])
```

Unlike traditional Django commands, Django Commander commands can return values. Examples of how this can be useful 
include having a command return its current API key if you're cycling through multiple keys, or returning an object 
that the command created.

