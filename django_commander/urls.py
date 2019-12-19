from django.conf.urls import url

from django_commander import views


app_name = "django_commander"
urlpatterns = [
    url(r"^$", views.home, name="home"),
    url(r"^(?P<command_id>.+)$", views.view_command, name="view_command"),
]
