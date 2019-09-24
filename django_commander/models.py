from builtins import str
from builtins import object
from django.db import models
from picklefield.fields import PickledObjectField

from django_pewtils.abstract_models import BasicExtendedModel
from django_pewtils import get_model


class LoggedExtendedModel(BasicExtendedModel):

    """
    This abstract model can be used as a base class on any model that you want to track.  All of the commands in
    django_commander (i.e. BasicCommand and everything that inherits from it) are automatically logged in the database
    with a unique Command row that's a combination of the command's name and the parameters passed to it, and when
    a command is run, it is logged with a new row in the CommandLog table.  You can also choose to write your commands
    such that they create associations in the database with objects that they modify.  If those objects inherit from
    LoggedExtendedModel, you can add the command directly (`my_object.command_logs.add(self.log)`) or you can pass
    `self.log` to django_pewtils' `.create_or_update` function, which will automatically create the association.
    """

    commands = models.ManyToManyField(
        "django_commander.Command", related_name="%(class)s_related"
    )
    command_logs = models.ManyToManyField(
        "django_commander.CommandLog", related_name="%(class)s_related"
    )

    class Meta(object):

        abstract = True


class Command(BasicExtendedModel):

    """
    Refers to a command class that's used to load data into the database.  Parameters are values used that have a bearing
    on the data that get loaded in, and so the name and parameters, taken together, refer to a specific set of data
    loaded by a specific process.  If your app's models inherit from LoggedExtendedModel, you can use M2M relations
    with CommandLog and Command to track the sources from which a given object's data have been pulled, for example.
    """

    name = models.CharField(
        max_length=400, db_index=True, help_text="The name of a command"
    )
    parameters = models.TextField(
        null=True, help_text="The parameters used to initialize the command"
    )

    class Meta(object):

        unique_together = ("name", "parameters")

    def __str__(self):

        return "%s %s" % (self.name, self.parameters)

    @property
    def command_class(self):

        from django_commander.commands import commands

        return commands[self.name]

    @property
    def command(self):

        return self.command_class()

    def run(self):

        self.command.run()


class CommandLog(BasicExtendedModel):

    """
    A specific log generated by a command, including optional parameters and any errors generated by the command.
    """

    command = models.ForeignKey(
        "django_commander.Command",
        on_delete=models.CASCADE,
        related_name="logs",
        help_text="The parent command",
    )
    start_time = models.DateTimeField(
        auto_now_add=True, help_text="The time at which the command began executing"
    )
    end_time = models.DateTimeField(
        null=True, help_text="The time at which the command finished (if applicable)"
    )
    options = models.TextField(null=True, help_text="The options passed to the command")
    error = PickledObjectField(
        null=True, help_text="The error returned by the command (if applicable)"
    )
    celery_task_id = models.TextField(null=True)

    def __str__(self):

        if self.end_time:
            status = "COMPLETED"
        elif self.error:
            status = "FAILED"
        else:
            status = "RUNNING"
        return "%s (pk=%s): %s" % (str(self.command), str(self.pk), status)

    @property
    def celery_task(self):

        return get_model("TaskResult", app_name="django_celery_results").objects.get(
            task_id=self.celery_task_id
        )


from django.db.models.signals import m2m_changed


def update_command_m2m(sender, **kwargs):
    if kwargs["action"] == "post_add" and "instance" in kwargs and kwargs["instance"]:
        obj = kwargs["instance"]
        commands = Command.objects.filter(
            pk__in=obj.command_logs.values_list("command_id", flat=True)
        )
        obj.commands.set(commands)


m2m_changed.connect(update_command_m2m, sender=LoggedExtendedModel.command_logs.through)
