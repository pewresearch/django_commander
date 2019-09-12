from django.db import models

from django_commander.models import LoggedExtendedModel


class Child(LoggedExtendedModel):

    name = models.TextField()
    parent = models.ForeignKey("testapp.Parent", related_name="children", on_delete=models.CASCADE)

class Parent(LoggedExtendedModel):

    name = models.TextField(null=True)