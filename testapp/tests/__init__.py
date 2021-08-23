from __future__ import print_function

import subprocess

from django.test import TestCase as DjangoTestCase
from django.core.management import call_command

from django_commander.commands import commands, MissingDependencyException
from django_commander.models import Command, CommandLog
from django_commander.utils import clear_unfinished_command_logs, test_commands

from testapp.models import Parent, Child


class BaseTests(DjangoTestCase):

    """
    To test, navigate to django_commander root folder and run `python manage.py test testapp.tests`
    """

    def setUp(self):

        pass

    def test_command(self):

        with self.assertRaises(MissingDependencyException):
            commands["test_command_with_dependency"](parent_name="bob").run()
        commands["test_command_with_dependency"](
            parent_name="bob", ignore_dependencies=True
        ).run()
        commands["test_command"](parent_name="bob").run()
        _, sally = commands["test_command"](parent_name="bob", child_name="sally").run()
        bob, child = commands["test_command_with_dependency"](parent_name="bob").run()

        self.assertEqual(Parent.objects.count(), 1)
        self.assertEqual(Child.objects.count(), 2)
        self.assertEqual(Command.objects.count(), 2)
        self.assertEqual(CommandLog.objects.count(), 4)

        self.assertEqual(bob.commands.count(), 2)
        self.assertEqual(bob.command_logs.count(), 4)
        self.assertEqual(sally.commands.count(), 1)
        self.assertEqual(sally.command_logs.count(), 1)
        self.assertEqual(child.commands.count(), 2)
        self.assertEqual(child.command_logs.count(), 3)

        for log in CommandLog.objects.all():
            self.assertIsNotNone(log.end_time)
            self.assertIsNone(log.error)
            self.assertGreater(log.parent_related.count(), 0)
            self.assertGreater(log.child_related.count(), 0)

    def test_download_iterate_command(self):

        commands["test_download_iterate_command"]().run()
        self.assertEqual(Parent.objects.filter(name="bob").count(), 1)
        self.assertEqual(Parent.objects.filter(name="shelly").count(), 1)
        self.assertEqual(
            Parent.objects.get(name="bob")
            .commands.filter(name="test_download_iterate_command")
            .count(),
            1,
        )
        self.assertEqual(
            Parent.objects.get(name="shelly")
            .commands.filter(name="test_download_iterate_command")
            .count(),
            1,
        )
        commands["test_download_iterate_command"](refresh_cache=True).run()

    def test_iterate_download_command(self):

        commands["test_iterate_download_command"]().run()
        self.assertEqual(Parent.objects.filter(name="BOB").count(), 1)
        self.assertEqual(Parent.objects.filter(name="SHELLY").count(), 1)
        self.assertEqual(
            Parent.objects.get(name="BOB")
            .commands.filter(name="test_iterate_download_command")
            .count(),
            1,
        )
        self.assertEqual(
            Parent.objects.get(name="SHELLY")
            .commands.filter(name="test_iterate_download_command")
            .count(),
            1,
        )
        commands["test_iterate_download_command"](refresh_cache=True).run()

    def test_database_models(self):

        for name in ["bob", "shelly", "suzy", "jeff"]:
            for i in range(0, 5):
                commands["test_command"](parent_name=name).run()

            log = CommandLog.objects.all()[0]
            string = str(log)
            log.error = "ERROR"
            log.save()
            log_id = log.pk
            clear_unfinished_command_logs()
            self.assertEqual(CommandLog.objects.filter(pk=log_id).count(), 0)

            cmd = Command.objects.get(
                name="test_command", parameters={"parent_name": name}
            )
            self.assertIsNotNone(cmd.command_class)
            self.assertIsNotNone(cmd.command)
            cmd.run()
            cmd.consolidate_logs()
            self.assertEqual(cmd.logs.count(), 1)

    def test_test_commands(self):

        test_commands()

    def test_multiprocessed_download_iterate_command(self):

        commands["test_multiprocessed_download_iterate_command"](
            num_cores=1, test=True
        ).run()
        self.assertEqual(Parent.objects.filter(name="bob").count(), 1)
        self.assertEqual(Parent.objects.filter(name="shelly").count(), 1)
        self.assertEqual(
            Parent.objects.get(name="bob")
            .commands.filter(name="test_multiprocessed_download_iterate_command")
            .count(),
            1,
        )
        self.assertEqual(
            Parent.objects.get(name="shelly")
            .commands.filter(name="test_multiprocessed_download_iterate_command")
            .count(),
            1,
        )
        commands["test_multiprocessed_download_iterate_command"](
            num_cores=1, refresh_cache=True, test=True
        ).run()

    def test_multiprocessed_iterate_download_command(self):
        commands["test_multiprocessed_iterate_download_command"](
            num_cores=1, test=True
        ).run()
        self.assertEqual(Parent.objects.filter(name="BOB").count(), 1)
        self.assertEqual(Parent.objects.filter(name="SHELLY").count(), 1)
        self.assertEqual(
            Parent.objects.get(name="BOB")
            .commands.filter(name="test_multiprocessed_iterate_download_command")
            .count(),
            1,
        )
        self.assertEqual(
            Parent.objects.get(name="SHELLY")
            .commands.filter(name="test_multiprocessed_iterate_download_command")
            .count(),
            1,
        )
        commands["test_multiprocessed_iterate_download_command"](
            num_cores=1, refresh_cache=True, test=True
        ).run()

    def test_multiprocessing(self):
        pass
        # # Haven't figured out how to test multiprocessing; the unit testing module keeps the db in a single transaction
        # # Also, when you trigger manage.py externally, it's going to try to use the main database, not the test one
        # process = subprocess.Popen(
        #     ['python', 'manage.py', 'run_command_task', 'test_command', 'bob', '--child_name', 'jeff'],
        #     stdout=subprocess.PIPE,
        #     stderr=subprocess.PIPE
        # )
        # stdout, stderr = process.communicate()

    def test_views(self):

        from django.urls import reverse

        commands["test_command"](parent_name="bob").run()
        command_id = Command.objects.all()[0].pk

        for view, method, args, data, tests in [
            (
                "django_commander:home",
                "get",
                [],
                {},
                [
                    (lambda x: len(x["commands"]), 1),
                    (lambda x: x["commands"][0]["command"].name, "test_command"),
                    (lambda x: x["commands"][0]["latest_log"].error, None),
                ],
            ),
            (
                "django_commander:view_command",
                "get",
                [command_id],
                {},
                [
                    (lambda x: x["command"].name, "test_command"),
                    (lambda x: len(x["logs"]), 1),
                ],
            ),
        ]:
            response = getattr(self.client, method)(reverse(view, args=args), data=data)
            self.assertEqual(response.status_code, 200)
            for func, value in tests:
                self.assertEqual(func(response.context), value)

    def test_m2m_changed(self):

        parent = Parent.objects.create(name="bob")
        command = Command.objects.create(name="test_command")
        log = CommandLog.objects.create(command=command)
        parent.command_logs.add(log)
        self.assertIn(command, parent.commands.all())

    def tearDown(self):
        from django.conf import settings
        import shutil, os

        cache_path = os.path.join(
            settings.BASE_DIR, settings.DJANGO_COMMANDER_CACHE_PATH
        )
        if os.path.exists(cache_path):
            shutil.rmtree(cache_path)
