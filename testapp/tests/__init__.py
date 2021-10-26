from __future__ import print_function

import os
import time

from django.test import TestCase as DjangoTestCase
from django.test import TransactionTestCase as DjangoTransactionTestCase
from django.core.management import call_command
from django.conf import settings

from django_pewtils import CacheHandler

from django_commander.commands import commands, MissingDependencyException
from django_commander.models import Command, CommandLog
from django_commander.utils import clear_unfinished_command_logs, test_commands

from testapp.models import Parent, Child


class BaseTests(DjangoTransactionTestCase):

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
        cache = CacheHandler(
            os.path.join(
                settings.DJANGO_COMMANDER_CACHE_PATH, "test_download_iterate_command"
            ),
            hash=False,
            use_s3=settings.DJANGO_COMMANDER_USE_S3,
            bucket=settings.S3_BUCKET,
        )
        value = cache.read("test_download_iterate_commanddownload(){}")
        self.assertEqual(value, [["bob", "shelly"]])
        commands["test_download_iterate_command"](refresh_cache=False).run()
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
        cache = CacheHandler(
            os.path.join(
                settings.DJANGO_COMMANDER_CACHE_PATH, "test_iterate_download_command"
            ),
            hash=False,
            use_s3=settings.DJANGO_COMMANDER_USE_S3,
            bucket=settings.S3_BUCKET,
        )
        for name in ["bob", "shelly"]:
            value = cache.read(
                "test_iterate_download_commanddownload('" + name + "',){}"
            )
            self.assertEqual(value, [name.upper()])
        commands["test_iterate_download_command"](refresh_cache=False).run()
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
        from django_commander.commands import commands

        for command_name in commands.keys():
            self.assertTrue(
                os.path.exists(
                    os.path.join(
                        settings.DJANGO_COMMANDER_CACHE_PATH, command_name, "test"
                    )
                )
            )

    def test_multiprocessed_download_iterate_command(self):
        from django_pewtils import reset_django_connection

        commands["test_multiprocessed_download_iterate_command"](num_cores=2).run()
        reset_django_connection()
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
        cache = CacheHandler(
            os.path.join(
                settings.DJANGO_COMMANDER_CACHE_PATH,
                "test_multiprocessed_download_iterate_command",
            ),
            hash=False,
            use_s3=settings.DJANGO_COMMANDER_USE_S3,
            bucket=settings.S3_BUCKET,
        )
        value = cache.read("test_multiprocessed_download_iterate_commanddownload(){}")
        self.assertEqual(value, [["bob", "shelly"]])
        commands["test_multiprocessed_download_iterate_command"](
            num_cores=2, refresh_cache=True
        ).run()
        reset_django_connection()

    def test_multiprocessed_iterate_download_command(self):
        from django_pewtils import reset_django_connection

        commands["test_multiprocessed_iterate_download_command"](num_cores=2).run()
        reset_django_connection()
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
        cache = CacheHandler(
            os.path.join(
                settings.DJANGO_COMMANDER_CACHE_PATH,
                "test_multiprocessed_iterate_download_command",
            ),
            hash=False,
            use_s3=settings.DJANGO_COMMANDER_USE_S3,
            bucket=settings.S3_BUCKET,
        )
        for name in ["bob", "shelly"]:
            value = cache.read(
                "test_multiprocessed_iterate_download_commanddownload('"
                + name
                + "',){}"
            )
            self.assertEqual(value, [name.upper()])
        commands["test_multiprocessed_iterate_download_command"](
            num_cores=2, refresh_cache=True
        ).run()
        reset_django_connection()

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

    def test_run_command_async(self):

        from django_commander.utils import run_command_async

        run_command_async("test_command", parent_name="bobby", child_name="bobby jr.")
        time.sleep(5)
        self.assertEqual(Parent.objects.filter(name="bobby").count(), 1)
        self.assertEqual(Child.objects.filter(name="bobby jr.").count(), 1)

    def tearDown(self):
        from django.conf import settings
        import shutil, os

        cache_path = os.path.join(
            settings.BASE_DIR, settings.DJANGO_COMMANDER_CACHE_PATH
        )
        if os.path.exists(cache_path):
            shutil.rmtree(cache_path)
