from future import standard_library
standard_library.install_aliases()
from celery import shared_task


class MissingDependencyException(Exception):
    pass


@shared_task
def run_command_task(command_name, params):

    try:
        from django_commander.commands import commands
        commands[command_name](**params).run()
        return "Success: {}".format(command_name)
    except Exception as e:
        return e


def test_commands():

    from django_commander.commands import commands
    for command_name in list(commands.keys()):
        params = {"test": True}
        if hasattr(commands[command_name], "test_options"):
            params.update(commands[command_name].test_options)
        if hasattr(commands[command_name], "test_parameters"):
            params.update(commands[command_name].test_parameters)
        try:
            commands[command_name](**params).run()
            print("{}: SUCCESS!".format(command_name))
        except Exception as e:
            print("{}: FAILURE!  {}".format(command_name, e))