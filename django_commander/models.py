from django.db import models
from picklefield.fields import PickledObjectField

from pewtils.django.abstract_models import BasicExtendedModel


class LoggedExtendedModel(BasicExtendedModel):

    commands = models.ManyToManyField("django_commander.Command", related_name="%(class)s_related")
    command_logs = models.ManyToManyField("django_commander.CommandLog", related_name="%(class)s_related")

    class Meta:

        abstract=True


class Command(BasicExtendedModel):

    """
    Refers to a command class that's used to load data into the database.  Parameters are values used that have a bearing
    on the data that get loaded in, and so the name and parameters, taken together, refer to a specific set of data
    loaded by a specific process.  Most models in Logos have ManyToMany relationships with Commands, so we can track
    the sources from which a given object's data have been pulled.
    """

    name = models.CharField(max_length=400, db_index=True, help_text="The name of a command")
    parameters = models.TextField(null=True, help_text="The parameters used to initialize the command")

    class Meta:

        unique_together = ("name", "parameters")

    def __str__(self):

        return "%s %s" % (
            self.name,
            self.parameters
        )

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

    command = models.ForeignKey("django_commander.Command", related_name="logs", help_text="The parent command")
    start_time = models.DateTimeField(auto_now_add=True, help_text="The time at which the command began executing")
    end_time = models.DateTimeField(null=True, help_text="The time at which the command finished (if applicable)")
    options = models.TextField(null=True, help_text="The options passed to the command")
    error = PickledObjectField(null=True, help_text="The error returned by the command (if applicable)")

    def __str__(self):

        if self.end_time: status = "COMPLETED"
        elif self.error: status = "FAILED"
        else: status = "RUNNING"
        return "%s (pk=%s): %s" % (
            str(self.command),
            str(self.pk),
            status
        )