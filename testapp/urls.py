from django.conf.urls import include
from django.urls import re_path
from testapp import views


urlpatterns = [
    re_path(r"^login$", views.login, name="login"),
    re_path(r"^logout$", views.logout, name="logout"),
]

urlpatterns += [re_path(r"^commands/", include("django_commander.urls"))]
