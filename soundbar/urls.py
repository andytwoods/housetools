from django.urls import path

from . import views

app_name = "soundbar"

urlpatterns = [
    path("", views.status, name="status"),
    path("connect/", views.connect, name="connect"),
    path("oauth/callback/", views.callback, name="callback"),
]
