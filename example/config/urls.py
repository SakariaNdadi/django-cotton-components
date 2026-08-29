from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path

from demo.panels import admin_panel

urlpatterns = [
    path("admin/", admin.site.urls),
    path("dcc/", include("django_control_components.urls")),
    admin_panel.mount(),
    path("", include("demo.urls")),
    *static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT),
]
