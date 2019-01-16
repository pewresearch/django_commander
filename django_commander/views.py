from future import standard_library
standard_library.install_aliases()
import datetime

from django.shortcuts import render
from django.template import RequestContext
from django.contrib.auth.decorators import login_required
from django.conf import settings

from django_commander.models import Command, CommandLog


@login_required
def home(request):

    commands = []
    for c in Command.objects.all():
        commands.append({"command": c, "latest_log": c.logs.order_by("-start_time")[0]})
    commands = sorted(commands, key=lambda x: x['latest_log'].start_time, reverse=True)

    return render(request, 'django_commander/index.html', {"commands": commands})


@login_required
def view_command(request, command_id):

    command = Command.objects.get(pk=command_id)
    logs = command.logs.order_by("-start_time")

    return render(request, 'django_commander/command.html', {"command": command, "logs": logs})