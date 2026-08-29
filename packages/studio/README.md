# django-control-components-studio

The no-code builder seam for
[django-control-components](https://github.com/SakariaNdadi/django-control-components):
define panel resources, dashboards, nav, and role access from the browser instead of
Python.

## Install

```bash
pip install "django-control-components[studio]"
```

That pulls this package. Then add the app **after** the core app:

```python
INSTALLED_APPS = [
    # ...
    "django_cotton",
    "django_control_components",
    "django_control_components.studio",
]
```

Run migrations (`dcc_studio` app) and mount a panel with `.studio()` / `.dynamic()`.
See the [no-code docs](https://github.com/SakariaNdadi/django-control-components/blob/master/docs/no-code.md).
