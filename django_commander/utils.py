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