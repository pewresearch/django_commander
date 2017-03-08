import pkgutil, importlib, re

from multiprocessing import Process

from django.conf import settings

from pewtils.django import reset_django_connection


class MissingDependencyException(Exception):
    pass

def run_command_async(command_name, params):

    def run_command(name, **params):
        reset_django_connection()
        from django_commander.commands import commands
        commands[name](**params).run()

    p = Process(target=run_command, args=(command_name, ), kwargs=params)
    p.start()
    p.join()