from django.conf.urls import include, url
from django.http import HttpResponse
from testapp import views


urlpatterns = [
    url(r"^login$", views.login, name="login"),
    url(r"^logout$", views.logout, name="logout"),
]

urlpatterns += [url(r"^commands/", include("django_commander.urls"))]
