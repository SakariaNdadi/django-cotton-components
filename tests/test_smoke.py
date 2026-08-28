from __future__ import annotations

import pytest

import django_cotton_components


def test_version_exposed():
    assert django_cotton_components.__version__ == "1.0.0b1"


@pytest.mark.django_db  # the studio DashboardSpec JSONField check probes the backend
def test_system_checks_pass():
    from django.core.management import call_command

    call_command("check")
