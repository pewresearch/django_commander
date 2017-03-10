# Django Commander

Django Commander allows you to easily create, organize, and log management commands and subcommands.
You might wonder why you may need something that goes above and beyond the traditional Django management
command system.  Here are some things that Django Commander does that you can't do with out-of-the-box Django:

1. Organize and nest your management commands into subfolders and easily access them from the command line
with no hassle
2. Automatically log commands that get run
3. Use a standardized system for loading and processing data
4. Keep track of the objects in your database that get modified by each command

## Installation

### Dependencies

django_commander requires:

- Python (>= 2.7)
- Django (>= 1.10)
- Celery (>=4.0.2)
- [Pewtils (our own in-house Python utilities)](https://github.com/pewresearch/pewtils)

You'll need to install Pewtils in order for Django Commander to work, but other than that,
there are no special requirements.

### Setup and Configuration

First, you'll need to run migrations to get your database set up.

```
$ python manage.py migrate
```

Next, you need to specify where your commands will go in your `settings.py` file.  This is accomplished
using the `DJANGO_COMMANDER_COMMAND_FOLDERS` setting.

```python
DJANGO_COMMANDER_COMMAND_FOLDERS = [
    os.path.abspath(os.path.join(APP_ROOT, "commands").decode('utf-8')).replace('\\', '/'),
]
```

#### Multiprocessing and Task Management

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
* `DownloadIterateLoader`
* `IterateDownloadLoader`
* `MultiprocessedIterateDownloadLoader`
* `MultiprocessedDownloadIterateLoader`

Imagine you create a simple command such as:

```python

from django_commander.commands import BasicCommand

class Command(BasicCommand):

    option_defaults = [
        {"name": "my_option", "default": False, "type": bool}
    ]
    parameter_defaults = [
        {"name": "my_parameter", "default": None, "type": str}
    ]
    dependencies = []

    def __init__(self, **options):

        super(BasicCommand, self).__init__(**options)

    def run(self):

        pass

    def cleanup(self):

        pass

```

If you put this in your command module (found somewhere in one of your `DJANGO_COMMANDER_COMMAND_FOLDERS`),
then you can immediately run it via `manage.py` - for starters, let's put it in the root command directory
and call the file `my_command.py`.  We've specified a single option, `my_option`, which takes a boolean value,
and a single parameter, `my_parameter`, which expects a string.  When it comes to logging, Django Commander
separates parameters into "parameters" and "options" based on what's necessary versus optional for a command.
Parameters define core functionality of the command - for example, if you have a command to scrape a website,
you may demand a parameter for the domain to be scraped.  Options, in this case, might include a "--skip_existing"
flag to optionally skip webpages that have already been scraped.  You can then run your new command like so:

```bash
$ python manage.py run_command my_command PARAM_VALUE --my_option OPTION_VALUE
```

Commands can be nested in as many submodules as you want, and they will always be accessible via `manage.py`
by concatenating the folder names together with underscores.  If we were to move this new command down to a
submodule, in a folder named "scrapers", we could then run it like so:

```bash
$ python manage.py run_command scrapers_my_command PARAM_VALUE --my_option OPTION_VALUE
```

Every time a command is run, it is logged in the `django_commander.models.CommandLog` table.  A
`django_commander.models.Command` object is automatically created when a new command is first run.
You can then see details on all of your commands by querying those tables, like so:

```python
from django_commander.models import Command
print Command.objects.get(name="scrapers_my_command").logs.all()
```

### Accessing Commands Directly

Django Commander also lets you access your commands directly.  It automatically scans every Django app
you have installed, and extracts all of the command classes into a single dictionary, found in
`django_commander.commands.commands`.  You can import this from any app in your project, and run the commands
manually, if you so choose:

```python
from django_commander.commands import commands
commands["scrapers_my_command"](PARAM_VALUE, my_option=OPTION_VALUE).run()
```

You can also access commands through the Django ORM:

```python
from django_commander.models import Command
my_command = Command.objects.get(name="scrapers_my_command").command_class
my_command(PARAM_VALUE, my_option=OPTION_VALUE).run()
print my_command.logs.order_by("-end_time")[0]
```

# TODO: explain the different command and loader classes
# TODO: explain how to log manually, and using the create_or_update function
# TODO: explain dependencies
# TODO: verify that the examples are actually correct (underscore command concatenation, etc)


