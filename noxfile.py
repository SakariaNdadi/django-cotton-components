"""Task sessions. Run ``uv run nox -l`` to list."""

from __future__ import annotations

import nox

nox.options.default_venv_backend = "uv"
nox.options.reuse_existing_virtualenvs = True

PYTHONS = ["3.12", "3.13"]
DJANGOS = ["5.2", "6.1"]

SECURITY_CRITICAL = [
    "src/django_control_components/htmx.py",
    "src/django_control_components/core/attributes.py",
    "src/django_control_components/schemas/forms_bridge.py",
    "src/django_control_components/images/validators.py",
    "src/django_control_components/tables/query.py",
    "src/django_control_components/actions/registry.py",
]


def _install(session: nox.Session, *extra: str) -> None:
    session.run_install(
        "uv",
        "sync",
        "--no-default-groups",
        "--group",
        "dev",
        *extra,
        env={"UV_PROJECT_ENVIRONMENT": session.virtualenv.location},
    )


@nox.session(python=PYTHONS)
@nox.parametrize("django", DJANGOS)
def tests(session: nox.Session, django: str) -> None:
    _install(session)
    session.install(f"django~={django}.0")
    session.run("pytest", "-q", *session.posargs)


@nox.session
def lint(session: nox.Session) -> None:
    _install(session)
    session.run("ruff", "check", ".")
    session.run("ruff", "format", "--check", ".")


@nox.session
def typecheck(session: nox.Session) -> None:
    _install(session)
    session.run("mypy")


@nox.session
def coverage(session: nox.Session) -> None:
    _install(session)
    session.run("pytest", "-q", "--cov", "--cov-report=term-missing", "--cov-report=xml")
    # Per-module 100% branch floor on the modules where a missed branch is a vuln.
    present = [
        p
        for p in SECURITY_CRITICAL
        if session.run("test", "-f", p, external=True, success_codes=[0, 1]) == 0
    ]
    if present:
        session.run("coverage", "report", "--fail-under=100", "--include", ",".join(present))


@nox.session
def security(session: nox.Session) -> None:
    _install(session)
    session.install("semgrep", "pip-audit")
    session.run("ruff", "check", "--select", "S", ".")
    session.run(
        "semgrep", "--error", "--config", "p/django", "--config", "p/security-audit", "src/"
    )
    session.run("pip-audit", "--strict")
    session.run("pytest", "-q", "tests/test_security.py")


@nox.session
def build_css(session: nox.Session) -> None:
    """Compile css/dcc.css -> src/django_control_components/static/dcc/dcc.css."""
    session.run(
        "npx",
        "--yes",
        "@tailwindcss/cli@next",
        "-i",
        "css/dcc.css",
        "-o",
        "src/django_control_components/static/dcc/dcc.css",
        "--minify",
        external=True,
    )


@nox.session
def css_check(session: nox.Session) -> None:
    build_css(session)
    session.run(
        "git", "diff", "--exit-code", "--", "src/django_control_components/static/", external=True
    )


@nox.session
def packaging(session: nox.Session) -> None:
    _install(session)
    session.run("uv", "build", "--all-packages", external=True)
    session.run(
        "python",
        "-c",
        "import zipfile,glob,sys;"
        "core=[w for w in glob.glob('dist/*.whl') if 'studio' not in w][-1];"
        "studio=[w for w in glob.glob('dist/*.whl') if 'studio' in w][-1];"
        "cn=zipfile.ZipFile(core).namelist();"
        "sn=zipfile.ZipFile(studio).namelist();"
        "want=['django_control_components/templates/','django_control_components/static/dcc/dcc.css'];"
        "missing=[x for x in want if not any(e.startswith(x) or e==x for e in cn)];"
        "missing+=['studio/ leaked into core wheel'] if any('/studio/' in e for e in cn) else [];"
        "missing+=['studio wheel missing templates'] if not any('studio/templates/' in e for e in sn) else [];"
        "missing+=['studio wheel ships __init__.py'] if 'django_control_components/__init__.py' in sn else [];"
        "sys.exit('packaging check failed: '+str(missing) if missing else 0)",
    )
