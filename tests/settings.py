SECRET_KEY = "test-only-not-secret"

DEBUG = False

INSTALLED_APPS = [
    "django.contrib.contenttypes",
    "django.contrib.auth",
    "django.contrib.sessions",
    "django.contrib.staticfiles",
    "django_cotton",
    "django_control_components",
    "django_control_components.studio",
    "tests.testapp",
]

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": ":memory:",
    }
}

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
            ],
            "builtins": ["django_cotton.templatetags.cotton"],
        },
    }
]

MIDDLEWARE = [
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
]

ROOT_URLCONF = "tests.urls"

STATIC_URL = "/static/"

USE_TZ = True

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

MEDIA_ROOT = "/tmp/dcc-test-media"
MEDIA_URL = "/media/"
