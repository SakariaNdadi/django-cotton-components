from django.urls import path

from . import views

app_name = "demo"

urlpatterns = [
    path("", views.DashboardView.as_view(), name="index"),
    path("articles/", views.ArticleListView.as_view(), name="article-list"),
    path("articles/new/", views.ArticleCreateView.as_view(), name="article-create"),
    path("articles/<int:pk>/edit/", views.ArticleUpdateView.as_view(), name="article-edit"),
    path("wizard/", views.ArticleWizard.as_view(), name="wizard"),
    path("login/", views.DemoLogin.as_view(), name="login"),
    path("logout/", views.DemoLogout.as_view(), name="logout"),
]
