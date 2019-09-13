from __future__ import print_function

import subprocess

from django.test import TestCase as DjangoTestCase
from django.core.management import call_command


class BaseTests(DjangoTestCase):

    """
    To test, navigate to django_commander root folder and run `python manage.py test testapp.tests`
    """

    def setUp(self):

        pass

    def test_command(self):

        from django_commander.commands import commands, MissingDependencyException
        from django_commander.models import Command, CommandLog
        from testapp.models import Parent, Child

        with self.assertRaises(MissingDependencyException):
            commands["test_command_with_dependency"](parent_name="bob").run()
        commands["test_command_with_dependency"](parent_name="bob", ignore_dependencies=True).run()
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

        # # Haven't figured out how to test multiprocessing; the unit testing module keeps the db in a single transaction
        # # Also, when you trigger manage.py externally, it's going to try to use the main database, not the test one
        # process = subprocess.Popen(
        #     ['python', 'manage.py', 'run_command_task', 'test_command', 'bob', '--child_name', 'jeff'],
        #     stdout=subprocess.PIPE,
        #     stderr=subprocess.PIPE
        # )
        # stdout, stderr = process.communicate()


    def tearDown(self):
        pass