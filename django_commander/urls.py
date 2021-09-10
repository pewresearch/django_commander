from django.urls import re_path

from django_commander import views


app_name = "django_commander"
urlpatterns = [
    re_path(r"^$", views.home, name="home"),
    re_path(r"^(?P<command_id>.+)$", views.view_command, name="view_command"),
]
