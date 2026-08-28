"""Task sessions. Run ``uv run nox -l`` to list."""

from __future__ import annotations

import nox

nox.options.default_venv_backend = "uv"
nox.options.reuse_existing_virtualenvs = True

PYTHONS = ["3.12", "3.13"]
DJANGOS = ["5.2", "6.1"]

SECURITY_CRITICAL = [
    "src/django_cotton_components/htmx.py",
    "src/django_cotton_components/core/attributes.py",
    "src/django_cotton_components/schemas/forms_bridge.py",
    "src/django_cotton_components/images/validators.py",
    "src/django_cotton_components/tables/query.py",
    "src/django_cotton_components/actions/registry.py",
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
    """Compile css/dcc.css -> src/django_cotton_components/static/dcc/dcc.css."""
    session.run(
        "npx",
        "--yes",
        "@tailwindcss/cli@next",
        "-i",
        "css/dcc.css",
        "-o",
        "src/django_cotton_components/static/dcc/dcc.css",
        "--minify",
        external=True,
    )


@nox.session
def css_check(session: nox.Session) -> None:
    build_css(session)
    session.run(
        "git", "diff", "--exit-code", "--", "src/django_cotton_components/static/", external=True
    )


@nox.session
def packaging(session: nox.Session) -> None:
    _install(session)
    session.run("uv", "build", external=True)
    session.run(
        "python",
        "-c",
        "import zipfile,glob,sys;"
        "w=sorted(glob.glob('dist/*.whl'))[-1];"
        "n=zipfile.ZipFile(w).namelist();"
        "want=['django_cotton_components/templates/','django_cotton_components/static/dcc/dcc.css'];"
        "missing=[x for x in want if not any(e.startswith(x) or e==x for e in n)];"
        "sys.exit('missing from wheel: '+str(missing) if missing else 0)",
    )
