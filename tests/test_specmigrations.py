"""The spec-migration framework mechanics. Uses locally-built SpecMigration
instances throughout so tests never touch the process-global production
registry (empty until real migrations land - see specmigrations/__init__.py)."""

from __future__ import annotations

from django_control_components.studio.specmigrations import (
    SpecMigration,
    current_version,
    migrate,
)


def _add_root(doc):
    doc = dict(doc)
    doc["root"] = {"type": "root"}
    return doc


def _rename_widgets(doc):
    doc = dict(doc)
    doc["items"] = doc.pop("widgets", [])
    return doc


def test_empty_registry_is_a_passthrough():
    doc = {"widgets": [1, 2, 3]}
    assert migrate(doc, migrations=[]) == doc


def test_current_version_of_empty_registry_is_zero():
    assert current_version([]) == 0
    assert current_version([SpecMigration(1, "a", _add_root)]) == 1


def test_migrate_applies_forward_and_stamps_version():
    steps = [SpecMigration(1, "add_root", _add_root)]
    out = migrate({"widgets": []}, migrations=steps)
    assert out == {"widgets": [], "root": {"type": "root"}, "schema_version": 1}


def test_migrate_applies_multiple_steps_in_ascending_order_regardless_of_registration_order():
    steps = [
        SpecMigration(2, "add_root", _add_root),
        SpecMigration(1, "rename_widgets", _rename_widgets),
    ]
    out = migrate({"widgets": ["a"]}, migrations=steps)
    assert out == {"items": ["a"], "root": {"type": "root"}, "schema_version": 2}


def test_migrate_skips_steps_already_applied():
    steps = [
        SpecMigration(1, "rename_widgets", _rename_widgets),
        SpecMigration(2, "add_root", _add_root),
    ]
    already_v1 = {"items": ["a"], "schema_version": 1}
    out = migrate(already_v1, migrations=steps)
    # only step 2 ran -- rename_widgets (v1) must not fire again
    assert out == {"items": ["a"], "root": {"type": "root"}, "schema_version": 2}


def test_migrate_at_current_version_is_a_noop():
    steps = [SpecMigration(1, "add_root", _add_root)]
    at_head = {"schema_version": 1, "root": {"type": "root"}}
    assert migrate(at_head, migrations=steps) == at_head


def test_migrate_never_mutates_the_input():
    original = {"widgets": [1]}
    frozen = dict(original)
    migrate(original, migrations=[SpecMigration(1, "rename_widgets", _rename_widgets)])
    assert original == frozen


def test_missing_schema_version_is_treated_as_zero():
    steps = [SpecMigration(1, "add_root", _add_root)]
    assert migrate({}, migrations=steps)["schema_version"] == 1


def test_register_decorator_populates_the_global_registry():
    from django_control_components.studio import specmigrations as mod

    before = len(mod._REGISTRY)
    try:

        @mod.register(999, "test_only_migration")
        def _forward(doc):
            return doc

        assert len(mod._REGISTRY) == before + 1
        assert mod._REGISTRY[-1].version == 999
    finally:
        mod._REGISTRY.pop()
