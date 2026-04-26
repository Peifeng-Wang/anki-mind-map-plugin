"""Dedicated unit tests for manager.linked_cleanup."""
import importlib
import json
import sys
import types
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PACKAGE_NAME = "mindmap_plugin_under_test"


class HookList(list):
    pass


class FakeAddonManager:
    def __init__(self):
        self.config = {}

    def getConfig(self, name):
        return dict(self.config)

    def writeConfig(self, name, config):
        self.config = dict(config)


class FakeNote(dict):
    def __init__(self, note_id=0, **fields):
        super().__init__(fields)
        self.id = note_id

    def keys(self):
        return super().keys()


class FakeCollection:
    def __init__(self, notes=None):
        self.notes = notes or {}
        self.updated_notes = []
        self.missing_lookups = []

    def get_note(self, note_id):
        if note_id not in self.notes:
            self.missing_lookups.append(note_id)
            raise KeyError(note_id)
        return self.notes[note_id]

    def update_note(self, note):
        self.updated_notes.append(note)


class FakeMainWindow:
    def __init__(self):
        self.addonManager = FakeAddonManager()
        self.col = FakeCollection()
        self.reviewer = None
        # mindmap_editors intentionally omitted in some tests to exercise getattr default


def install_anki_stubs():
    fake_mw = FakeMainWindow()
    from _aqt_stub import install_aqt_stub

    def _utils_factory():
        utils = types.ModuleType("aqt.utils")
        utils.showInfo = lambda *a, **kw: None
        utils.tooltip = lambda *a, **kw: None
        utils.getText = lambda *a, **kw: ("", False)
        utils.askUser = lambda *a, **kw: False
        return utils

    install_aqt_stub(
        fake_mw=fake_mw,
        hook_list_cls=HookList,
        utils_factory=_utils_factory,
    )
    return fake_mw


def import_plugin_module(name):
    if PACKAGE_NAME not in sys.modules:
        package = types.ModuleType(PACKAGE_NAME)
        package.__path__ = [str(ROOT)]
        sys.modules[PACKAGE_NAME] = package
    full_name = f"{PACKAGE_NAME}.{name}"
    sys.modules.pop(full_name, None)
    return importlib.import_module(full_name)


def _clear_package_modules():
    for key in list(sys.modules):
        if key.startswith(f"{PACKAGE_NAME}."):
            sys.modules.pop(key)


class GetLinkedMapsTests(unittest.TestCase):
    def setUp(self):
        self.mw = install_anki_stubs()
        _clear_package_modules()
        self.lc = import_plugin_module("manager.linked_cleanup")

    def test_returns_empty_when_data_missing(self):
        self.assertEqual(self.lc.get_linked_maps({}), [])

    def test_returns_empty_when_linkedmaps_missing(self):
        self.assertEqual(self.lc.get_linked_maps({"data": {"id": "root"}}), [])

    def test_returns_list_when_present(self):
        payload = {
            "data": {
                "linkedMaps": [
                    {"targetMapId": 7, "linkedNodeId": "n:a"},
                    {"targetMapId": 8, "linkedNodeId": "n:b"},
                ]
            }
        }
        self.assertEqual(len(self.lc.get_linked_maps(payload)), 2)

    def test_data_root_can_be_dict_without_linkedmaps(self):
        # data exists but no linkedMaps key
        self.assertEqual(self.lc.get_linked_maps({"data": {"foo": "bar"}}), [])


class RemoveLinkedNodeTests(unittest.TestCase):
    def setUp(self):
        install_anki_stubs()
        _clear_package_modules()
        self.lc = import_plugin_module("manager.linked_cleanup")

    def test_removes_node_under_data_key(self):
        payload = {"data": {"id": "root", "children": [{"id": "n1"}, {"id": "n2"}]}}
        self.lc.remove_linked_node(payload, "n1")
        self.assertEqual([c["id"] for c in payload["data"]["children"]], ["n2"])

    def test_no_data_key_is_silent_noop(self):
        payload = {"meta": "info"}
        # must not raise
        self.lc.remove_linked_node(payload, "anything")
        self.assertEqual(payload, {"meta": "info"})

    def test_node_id_not_present_is_noop(self):
        payload = {"data": {"id": "root", "children": [{"id": "n1"}]}}
        self.lc.remove_linked_node(payload, "missing")
        self.assertEqual(len(payload["data"]["children"]), 1)


class LoadTargetMapTests(unittest.TestCase):
    def setUp(self):
        self.mw = install_anki_stubs()
        _clear_package_modules()
        self.lc = import_plugin_module("manager.linked_cleanup")

    def test_returns_note_and_parsed_data(self):
        target_note = FakeNote(5, Data=json.dumps({"data": {"id": "root"}}))
        self.mw.col = FakeCollection(notes={5: target_note})
        note, data = self.lc.load_target_map(self.mw, 5)
        self.assertIs(note, target_note)
        self.assertEqual(data, {"data": {"id": "root"}})

    def test_propagates_keyerror_from_collection(self):
        self.mw.col = FakeCollection(notes={})
        with self.assertRaises(KeyError):
            self.lc.load_target_map(self.mw, 999)


class CleanupLinkedNodesOnDeleteTests(unittest.TestCase):
    def setUp(self):
        self.mw = install_anki_stubs()
        _clear_package_modules()
        self.lc = import_plugin_module("manager.linked_cleanup")

    def _make_source(self, links):
        return FakeNote(
            1,
            Data=json.dumps({"data": {"linkedMaps": links}}),
        )

    def _make_target(self, note_id, child_ids):
        return FakeNote(
            note_id,
            Data=json.dumps({
                "data": {
                    "id": "root",
                    "children": [{"id": cid} for cid in child_ids],
                }
            }),
        )

    def test_removes_linked_nodes_in_multiple_targets(self):
        source = self._make_source([
            {"targetMapId": 2, "linkedNodeId": "n1"},
            {"targetMapId": 3, "linkedNodeId": "x1"},
        ])
        target_a = self._make_target(2, ["n1", "keep_a"])
        target_b = self._make_target(3, ["x1", "keep_b"])
        self.mw.col = FakeCollection(notes={1: source, 2: target_a, 3: target_b})

        self.lc.cleanup_linked_nodes_on_delete(self.mw, 1)

        self.assertEqual(len(self.mw.col.updated_notes), 2)
        a_data = json.loads(target_a["Data"])
        b_data = json.loads(target_b["Data"])
        self.assertEqual([c["id"] for c in a_data["data"]["children"]], ["keep_a"])
        self.assertEqual([c["id"] for c in b_data["data"]["children"]], ["keep_b"])

    def test_skips_link_with_missing_target_map_id(self):
        source = self._make_source([{"targetMapId": None, "linkedNodeId": "n1"}])
        self.mw.col = FakeCollection(notes={1: source})
        self.lc.cleanup_linked_nodes_on_delete(self.mw, 1)
        self.assertEqual(self.mw.col.updated_notes, [])

    def test_skips_link_with_missing_linked_node_id(self):
        source = self._make_source([{"targetMapId": 2, "linkedNodeId": None}])
        target = self._make_target(2, ["n1"])
        self.mw.col = FakeCollection(notes={1: source, 2: target})
        self.lc.cleanup_linked_nodes_on_delete(self.mw, 1)
        self.assertEqual(self.mw.col.updated_notes, [])

    def test_swallows_exception_when_target_missing(self):
        source = self._make_source([{"targetMapId": 999, "linkedNodeId": "n1"}])
        self.mw.col = FakeCollection(notes={1: source})
        # must not raise
        self.lc.cleanup_linked_nodes_on_delete(self.mw, 1)
        self.assertEqual(self.mw.col.updated_notes, [])

    def test_swallows_top_level_exception_when_source_missing(self):
        self.mw.col = FakeCollection(notes={})
        # must not raise
        self.lc.cleanup_linked_nodes_on_delete(self.mw, 42)
        self.assertEqual(self.mw.col.updated_notes, [])

    def test_partial_failure_continues_with_other_targets(self):
        # First target raises (missing), second succeeds.
        source = self._make_source([
            {"targetMapId": 999, "linkedNodeId": "n1"},
            {"targetMapId": 2, "linkedNodeId": "n2"},
        ])
        target_b = self._make_target(2, ["n2", "keep"])
        self.mw.col = FakeCollection(notes={1: source, 2: target_b})

        self.lc.cleanup_linked_nodes_on_delete(self.mw, 1)
        self.assertEqual(len(self.mw.col.updated_notes), 1)
        b_data = json.loads(target_b["Data"])
        self.assertEqual([c["id"] for c in b_data["data"]["children"]], ["keep"])

    def test_refreshes_matching_open_editor(self):
        source = self._make_source([{"targetMapId": 2, "linkedNodeId": "n1"}])
        target = self._make_target(2, ["n1"])
        self.mw.col = FakeCollection(notes={1: source, 2: target})

        refreshed = []

        class FakeEditor:
            def __init__(self, note_id):
                self.note_id = note_id

            def _handle_refresh(self):
                refreshed.append(self.note_id)

        self.mw.mindmap_editors = [FakeEditor(99), FakeEditor(2), FakeEditor(2)]
        self.lc.cleanup_linked_nodes_on_delete(self.mw, 1)

        # Loop breaks after first match: only one refresh recorded for note 2
        self.assertEqual(refreshed, [2])

    def test_does_not_refresh_when_no_matching_editor(self):
        source = self._make_source([{"targetMapId": 2, "linkedNodeId": "n1"}])
        target = self._make_target(2, ["n1"])
        self.mw.col = FakeCollection(notes={1: source, 2: target})

        refreshed = []

        class FakeEditor:
            def __init__(self, note_id):
                self.note_id = note_id

            def _handle_refresh(self):
                refreshed.append(self.note_id)

        self.mw.mindmap_editors = [FakeEditor(123), FakeEditor(456)]
        self.lc.cleanup_linked_nodes_on_delete(self.mw, 1)

        self.assertEqual(refreshed, [])
        self.assertEqual(len(self.mw.col.updated_notes), 1)

    def test_handles_missing_mindmap_editors_attribute(self):
        # Use bare object that lacks `mindmap_editors` to exercise getattr default.
        source = self._make_source([{"targetMapId": 2, "linkedNodeId": "n1"}])
        target = self._make_target(2, ["n1"])
        self.mw.col = FakeCollection(notes={1: source, 2: target})
        if hasattr(self.mw, "mindmap_editors"):
            delattr(self.mw, "mindmap_editors")
        # must not raise
        self.lc.cleanup_linked_nodes_on_delete(self.mw, 1)
        self.assertEqual(len(self.mw.col.updated_notes), 1)

    def test_no_linked_maps_does_nothing(self):
        source = FakeNote(1, Data=json.dumps({"data": {"id": "root"}}))
        self.mw.col = FakeCollection(notes={1: source})
        self.lc.cleanup_linked_nodes_on_delete(self.mw, 1)
        self.assertEqual(self.mw.col.updated_notes, [])


if __name__ == "__main__":
    unittest.main()
