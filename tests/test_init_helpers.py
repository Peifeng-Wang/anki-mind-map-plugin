"""Unit tests for ``core.config_merge.deep_merge_defaults``.

The helper used to live in the addon's ``__init__.py``. It was extracted to
``core/config_merge.py`` so it can be exercised without importing Anki.
"""
import importlib
import sys
import types
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PACKAGE_NAME = "mindmap_plugin_under_test"


def import_plugin_module(name: str):
    """Import ``<PACKAGE_NAME>.<name>`` from the project root."""
    if PACKAGE_NAME not in sys.modules:
        package = types.ModuleType(PACKAGE_NAME)
        package.__path__ = [str(ROOT)]
        sys.modules[PACKAGE_NAME] = package
    full_name = f"{PACKAGE_NAME}.{name}"
    sys.modules.pop(full_name, None)
    return importlib.import_module(full_name)


class DeepMergeDefaultsTests(unittest.TestCase):
    def setUp(self):
        for key in list(sys.modules):
            if key.startswith(f"{PACKAGE_NAME}."):
                sys.modules.pop(key)
        cm = import_plugin_module("core.config_merge")
        self.deep_merge_defaults = cm.deep_merge_defaults

    # --- top-level non-dict default ---------------------------------------
    def test_non_dict_default_preserves_user(self):
        merged, changed = self.deep_merge_defaults("user", "default")
        self.assertEqual(merged, "user")
        self.assertFalse(changed)

    def test_non_dict_default_preserves_falsy_user(self):
        merged, changed = self.deep_merge_defaults(0, 1)
        self.assertEqual(merged, 0)
        self.assertFalse(changed)
        merged, changed = self.deep_merge_defaults(None, 1)
        self.assertIsNone(merged)
        self.assertFalse(changed)

    # --- dict default vs non-dict user ------------------------------------
    def test_dict_default_replaces_non_dict_user(self):
        default = {"a": 1}
        merged, changed = self.deep_merge_defaults(None, default)
        self.assertEqual(merged, default)
        self.assertTrue(changed)

    def test_dict_default_replaces_string_user(self):
        merged, changed = self.deep_merge_defaults("not a dict", {"x": 2})
        self.assertEqual(merged, {"x": 2})
        self.assertTrue(changed)

    # --- dict + dict, key missing -----------------------------------------
    def test_missing_key_added(self):
        user = {"a": 1}
        merged, changed = self.deep_merge_defaults(user, {"a": 99, "b": 2})
        self.assertEqual(merged, {"a": 1, "b": 2})
        self.assertTrue(changed)
        # User's original value is preserved
        self.assertEqual(merged["a"], 1)

    def test_no_changes_when_all_keys_present(self):
        user = {"a": 1, "b": 2}
        merged, changed = self.deep_merge_defaults(user, {"a": 99, "b": 99})
        self.assertEqual(merged, {"a": 1, "b": 2})
        self.assertFalse(changed)

    def test_empty_user_dict_filled_from_defaults(self):
        merged, changed = self.deep_merge_defaults({}, {"a": 1, "b": 2})
        self.assertEqual(merged, {"a": 1, "b": 2})
        self.assertTrue(changed)

    def test_empty_default_dict_no_change(self):
        merged, changed = self.deep_merge_defaults({"a": 1}, {})
        self.assertEqual(merged, {"a": 1})
        self.assertFalse(changed)

    # --- nested dict merging ----------------------------------------------
    def test_nested_dict_missing_key_added(self):
        user = {"section": {"keep": "user"}}
        default = {"section": {"keep": "default", "added": "new"}}
        merged, changed = self.deep_merge_defaults(user, default)
        self.assertEqual(merged, {"section": {"keep": "user", "added": "new"}})
        self.assertTrue(changed)

    def test_nested_dict_no_changes(self):
        user = {"section": {"a": 1}}
        default = {"section": {"a": 99}}
        merged, changed = self.deep_merge_defaults(user, default)
        self.assertEqual(merged, {"section": {"a": 1}})
        self.assertFalse(changed)

    def test_deeply_nested_merge(self):
        user = {"l1": {"l2": {"l3": {"keep": "user"}}}}
        default = {"l1": {"l2": {"l3": {"keep": "default", "new": 1}, "sibling": 2}}}
        merged, changed = self.deep_merge_defaults(user, default)
        self.assertEqual(
            merged,
            {"l1": {"l2": {"l3": {"keep": "user", "new": 1}, "sibling": 2}}},
        )
        self.assertTrue(changed)

    def test_user_non_dict_at_nested_position_replaced_by_default_dict(self):
        # When a nested user value is not a dict but default is, the default wins.
        user = {"section": "scalar"}
        default = {"section": {"a": 1}}
        merged, changed = self.deep_merge_defaults(user, default)
        self.assertEqual(merged, {"section": {"a": 1}})
        self.assertTrue(changed)

    def test_user_dict_with_non_dict_default_for_existing_key_preserved(self):
        # Existing user key with non-dict default: user value preserved.
        user = {"flag": False}
        default = {"flag": True}
        merged, changed = self.deep_merge_defaults(user, default)
        self.assertEqual(merged, {"flag": False})
        self.assertFalse(changed)

    # --- mutation behaviour -----------------------------------------------
    def test_user_dict_is_mutated_in_place(self):
        user = {"a": 1}
        merged, _ = self.deep_merge_defaults(user, {"a": 99, "b": 2})
        # The function returns the same object after filling in keys.
        self.assertIs(merged, user)
        self.assertEqual(user, {"a": 1, "b": 2})

    def test_partial_changes_propagate_changed_flag(self):
        user = {"keep": 1, "section": {"have": "x"}}
        default = {"keep": 99, "section": {"have": "x", "missing": "y"}}
        merged, changed = self.deep_merge_defaults(user, default)
        self.assertTrue(changed)
        self.assertEqual(merged["section"]["missing"], "y")
        self.assertEqual(merged["section"]["have"], "x")
        self.assertEqual(merged["keep"], 1)


if __name__ == "__main__":
    unittest.main()
