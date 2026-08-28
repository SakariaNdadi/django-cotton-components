from django.urls import include, path

urlpatterns = [
    path("dcc/", include("django_cotton_components.urls")),
]
