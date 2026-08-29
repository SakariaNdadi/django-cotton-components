from django.urls import include, path

urlpatterns = [
    path("dcc/", include("django_control_components.urls")),
]
