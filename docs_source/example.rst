*************************************
Example
*************************************

Here's a simple example of an app that downloads an open-source roster of members of Congress and creates an object
for each of them in the database, updating their names:

**my_app/settings.py**

.. code-block:: python

    DJANGO_COMMANDER_COMMAND_FOLDERS = [
        os.path.abspath(os.path.join("my_app", "commands")),
    ]
    # We'll just use local caching
    DJANGO_COMMANDER_CACHE_PATH = "cache"
    DJANGO_COMMANDER_USE_S3 = False

**my_app/models.py**

.. code-block:: bash

    from django.db import models

    from django_commander.models import LoggedExtendedModel
    from django_commander.managers import LoggedExtendedManager


    class Politician(LoggedExtendedModel):

        bioguide_id = models.CharField(max_length=16, unique=True)
        last_name = models.CharField(max_length=32)

        objects = LoggedExtendedManager().as_manager()

**my_app/commands/load_politicians.py**

.. code-block:: bash

    from django_commander.commands import DownloadIterateCommand, cache_results
    from my_app.models import Politician


    class Command(DownloadIterateCommand):

        parameter_names = []
        dependencies = []
        test_parameters = {}
        test_options = {}

        @staticmethod
        def add_arguments(parser):
            return parser

        def __init__(self, **options):
            super(Command, self).__init__(**options)

        @cache_results
        def download(self):
            # Download the open-source data
            url = "https://raw.githubusercontent.com/unitedstates/congress-legislators/master/legislators-historical.yaml"
            data = yaml.load(urllib.request.urlopen(url).read())
            return [data,]

        def iterate(self, names):
            # Loop over the rows and yield them
            for yaml_data in data:
                yield [yaml_data]
                if self.options["test"]:
                    # If we're just testing the command, we'll only yield the first row
                    break

        def parse_and_save(self, yaml_data):

            bioguide_id = yaml_data.get("id", {}).get("bioguide", None)
            last_name = yaml_data.get("name", {}).get("last", None)
            if bioguide_id:

                # Create/update the record using base Django
                pol, created = Politician.objects.get_or_create(bioguide_id=bioguide_id)
                pol.last_name = last_name
                pol.command_logs.add(self.log)

                # Create/update the record using Django Pewtils (which has support for Django Commander)
                Politician.objects.create_or_update(
                    {"bioguide_id": bioguide_id},
                    {"last_name": last_name},
                    command_log=self.log
                )

        def cleanup(self):
            pass

With our command defined, we can run it from the CLI like so:

.. code-block:: bash

    python manage.py run_command load_politicians
    python manage.py run_command --refresh_cache

Or we can invoke it programatically:

.. code-block:: python

    # Using the django_commander.commands.commands dictionary:
    from django_commander.commands import commands
    commands["load_politicians"](refresh_cache=True).run()

    # Or, once we've run it at least once, using the record that was created in the database
    from django_commander.models import *
    Command.objects.get(name="load_politicians").command_class(refresh_cache=True).run()

Since our command associated each Politician object with the command log that updated it, we can now examine those
relations in the database:

.. code-block:: python

    pol = Politician.objects.get(pk=1)

    pol.command_logs.all()
    # [<CommandLog: load_politicians {} (pk=1): COMPLETED>, '...(remaining elements truncated)...']

    pol.command_logs.values()[0]
    # {'id': 1,
    #  'command_id': 1,
    #  'start_time': datetime.datetime(2021, 1, 1, 0, 0, 0, 0),
    #  'end_time': datetime.datetime(2021, 1, 1, 23, 59, 59, 0),
    #  'options': {'test': False, 'refresh_cache': False},
    #  'error': None}

    pol.commands.all()
    # [<Command: load_politicians {}>]