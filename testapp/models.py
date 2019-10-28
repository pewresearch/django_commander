from django.db import models

from django_commander.models import LoggedExtendedModel
from django_commander.managers import LoggedExtendedManager


class Child(LoggedExtendedModel):

    name = models.TextField()
    parent = models.ForeignKey(
        "testapp.Parent", related_name="children", on_delete=models.CASCADE
    )

    objects = LoggedExtendedManager().as_manager()


class Parent(LoggedExtendedModel):

    name = models.TextField(null=True)

    objects = LoggedExtendedManager().as_manager()
