from django.urls import path
from . import views

urlpatterns = [
    path("", views.index),
    # path("", views.CarListView.as_view()),
]
