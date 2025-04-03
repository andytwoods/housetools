# ruff: noqa
from django.urls import path

from . import views

urlpatterns = [
    path('update-youtube-status/', views.youtube_status, name='youtube-status'),
]

