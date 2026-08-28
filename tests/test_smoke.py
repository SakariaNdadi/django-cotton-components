from __future__ import annotations

import django_cotton_components


def test_version_exposed():
    assert django_cotton_components.__version__ == "1.0.0b1"


def test_system_checks_pass():
    from django.core.management import call_command

    call_command("check")
