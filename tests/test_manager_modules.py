import importlib
import json
import os
import sys
import types
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PACKAGE_NAME = "mindmap_plugin_under_test"


class Signal:
    def __init__(self):
        self.handlers = []

    def connect(self, handler):
        self.handlers.append(handler)


class FakeWidget:
    def __init__(self, *args, **kwargs):
        self.args = args
        self.children = []
        self.stylesheet = ""
        self.text = args[0] if args and isinstance(args[0], str) else ""
        self.html = ""
        self.placeholder = ""
        self.readonly = False
        self.maximum_height = None
        self.clicked = Signal()
        self.itemDoubleClicked = Signal()
        self._current_row = -1
        self.items = []
        self._updates_enabled = True

    def setWindowTitle(self, value):
        self.window_title = value

    def resize(self, width, height):
        self.size = (width, height)

    def addWidget(self, widget):
        self.children.append(widget)

    def addLayout(self, layout):
        self.children.append(layout)

    def addStretch(self):
        self.children.append("stretch")

    def setReadOnly(self, value):
        self.readonly = value

    def setMaximumHeight(self, value):
        self.maximum_height = value

    def setStyleSheet(self, value):
        self.stylesheet = value

    def setText(self, value):
        self.text = value

    def setHtml(self, value):
        self.html = value

    def setPlaceholderText(self, value):
        self.placeholder = value

    def setOpenExternalLinks(self, value):
        self.open_external_links = value

    def setSearchPaths(self, value):
        self.search_paths = value

    def clear(self):
        self.items.clear()

    def addItem(self, value):
        self.items.append(value)

    def currentRow(self):
        return self._current_row

    def setCurrentRow(self, value):
        self._current_row = value

    def exec(self):
        return None

    def close(self):
        self.closed = True

    def setUpdatesEnabled(self, value):
        self._updates_enabled = value

    def count(self):
        return len(self.items)


class FakeFileDialog:
    save_filename = ""
    open_filename = ""

    @staticmethod
    def getSaveFileName(*args):
        return FakeFileDialog.save_filename, ""

    @staticmethod
    def getOpenFileName(*args):
        return FakeFileDialog.open_filename, ""


class HookList(list):
    pass


class FakeAddonManager:
    def __init__(self):
        self.config = {}
        self.writes = []

    def getConfig(self, name):
        return dict(self.config)

    def writeConfig(self, name, config):
        self.writes.append((name, dict(config)))
        self.config = dict(config)


class FakeNote(dict):
    def __init__(self, note_id=0, **fields):
        super().__init__(fields)
        self.id = note_id

    def keys(self):
        return super().keys()


class FakeModels:
    def __init__(self, existing=None):
        self.existing = existing
        self.saved = []
        self.added = []

    def by_name(self, name):
        return self.existing

    def new(self, name):
        return {"name": name, "flds": [], "tmpls": []}

    def new_field(self, name):
        return {"name": name}

    def add_field(self, model, field):
        model["flds"].append(field)

    def new_template(self, name):
        return {"name": name}

    def add_template(self, model, template):
        model["tmpls"].append(template)

    def add(self, model):
        self.added.append(model)
        self.existing = model

    def save(self, model):
        self.saved.append(model)


class FakeCollection:
    def __init__(self, notes=None, models=None):
        self.notes = notes or {}
        self.models = models or FakeModels()
        self.added_notes = []
        self.updated_notes = []
        self.removed_notes = []

    def get_note(self, note_id):
        return self.notes[note_id]

    def find_notes(self, query):
        return list(self.notes)

    def version(self):
        return 42

    def new_note(self, model):
        return FakeNote(999)

    def add_note(self, note, deck_id):
        note.deck_id = deck_id
        self.added_notes.append(note)

    def update_note(self, note):
        self.updated_notes.append(note)

    def remove_notes(self, note_ids):
        self.removed_notes.extend(note_ids)


class FakeMainWindow:
    def __init__(self):
        self.addonManager = FakeAddonManager()
        self.col = FakeCollection()
        self.reviewer = None
        self.mindmap_editors = []


def install_anki_stubs():
    fake_mw = FakeMainWindow()
    from _aqt_stub import install_aqt_stub

    def _utils_factory():
        utils = types.ModuleType("aqt.utils")
        utils.messages = []
        utils.tooltips = []
        utils.showInfo = lambda message: utils.messages.append(message)
        utils.tooltip = lambda message: utils.tooltips.append(message)
        utils.getText = lambda *args, **kwargs: ("", False)
        utils.askUser = lambda *args, **kwargs: False
        return utils

    _, _, utils, hooks = install_aqt_stub(
        fake_mw=fake_mw,
        widget_factory=FakeWidget,
        file_dialog=FakeFileDialog,
        hook_list_cls=HookList,
        hook_names=(
            "reviewer_did_show_question",
            "reviewer_did_show_answer",
            "webview_did_receive_js_message",
        ),
        utils_factory=_utils_factory,
    )
    # Keep parity with the original stub: QTimer.singleShot is a no-op
    # here (rather than firing the callback immediately) because the
    # manager suite expects deferred execution.
    qt = sys.modules["aqt.qt"]
    qt.QTimer = types.SimpleNamespace(singleShot=lambda ms, cb: None)
    return fake_mw, utils, hooks


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


class NoteUtilsTests(unittest.TestCase):
    def setUp(self):
        self.mw, self.utils, self.hooks = install_anki_stubs()
        _clear_package_modules()
        self.note_utils = import_plugin_module("manager.note_utils")

    def test_constants(self):
        self.assertEqual(self.note_utils.FIELD_TITLE, "Title")
        self.assertEqual(self.note_utils.FIELD_DATA, "Data")
        self.assertEqual(self.note_utils.FIELD_ALLOW_NEW_CARDS, "AllowNewCards")
        self.assertEqual(self.note_utils.ALLOW_NEW_CARDS_ENABLED, "1")
        self.assertEqual(self.note_utils.ALLOW_NEW_CARDS_DISABLED, "0")
        self.assertEqual(self.note_utils.ACTIVE_ICON, "✓")
        self.assertEqual(self.note_utils.INACTIVE_ICON, "✗")
        self.assertEqual(self.note_utils.NOTE_QUERY, '"note:MindMap Master"')

    def test_get_note_title(self):
        note = FakeNote(1, Title="Map A")
        self.assertEqual(self.note_utils.get_note_title(note), "Map A")

    def test_get_allow_new_cards_enabled(self):
        note = FakeNote(1, AllowNewCards="1")
        self.assertEqual(self.note_utils.get_allow_new_cards(note), "1")

    def test_get_allow_new_cards_disabled(self):
        note = FakeNote(1, AllowNewCards="0")
        self.assertEqual(self.note_utils.get_allow_new_cards(note), "0")

    def test_get_allow_new_cards_missing_defaults_to_enabled(self):
        note = FakeNote(1)
        self.assertEqual(self.note_utils.get_allow_new_cards(note), "1")

    def test_load_note_data(self):
        payload = {"data": {"id": "root"}}
        note = FakeNote(1, Data=json.dumps(payload))
        self.assertEqual(self.note_utils.load_note_data(note), payload)

    def test_save_note_data(self):
        note = FakeNote(1, Data="")
        data = {"data": {"id": "root"}}
        self.note_utils.save_note_data(note, data)
        self.assertEqual(json.loads(note["Data"]), data)

    def test_sync_root_title_updates_topic(self):
        note = FakeNote(1, Data=json.dumps({"nodeData": {"id": "root", "topic": "Old"}}))
        self.note_utils.sync_root_title(note, "New")
        data = json.loads(note["Data"])
        self.assertEqual(data["nodeData"]["topic"], "New")

    def test_sync_root_title_noop_when_no_nodeData(self):
        note = FakeNote(1, Data=json.dumps({"data": {}}))
        self.note_utils.sync_root_title(note, "New")
        self.assertEqual(json.loads(note["Data"]), {"data": {}})

    def test_sync_root_title_noop_when_nodeData_id_not_root(self):
        note = FakeNote(1, Data=json.dumps({"nodeData": {"id": "other", "topic": "Old"}}))
        self.note_utils.sync_root_title(note, "New")
        data = json.loads(note["Data"])
        self.assertEqual(data["nodeData"]["topic"], "Old")

    def test_sync_root_title_swallows_exception(self):
        note = FakeNote(1)  # missing Data field
        # Should not raise
        self.note_utils.sync_root_title(note, "New")


class LinkedCleanupTests(unittest.TestCase):
    def setUp(self):
        self.mw, self.utils, self.hooks = install_anki_stubs()
        _clear_package_modules()
        self.linked_cleanup = import_plugin_module("manager.linked_cleanup")

    def test_get_linked_maps_empty(self):
        self.assertEqual(self.linked_cleanup.get_linked_maps({}), [])

    def test_get_linked_maps_with_links(self):
        payload = {"data": {"linkedMaps": [{"targetMapId": 2, "linkedNodeId": "n1"}]}}
        self.assertEqual(
            self.linked_cleanup.get_linked_maps(payload),
            [{"targetMapId": 2, "linkedNodeId": "n1"}],
        )

    def test_remove_node_by_id_direct_child(self):
        children = [{"id": "a"}, {"id": "b"}]
        root = {"id": "root", "children": children}
        result = self.linked_cleanup.remove_node_by_id(root, "a", root["children"], 0)
        self.assertTrue(result)
        self.assertEqual(children, [{"id": "b"}])

    def test_remove_node_by_id_nested(self):
        root = {"id": "root", "children": [{"id": "a", "children": [{"id": "b"}]}]}
        result = self.linked_cleanup.remove_node_by_id(root, "b")
        self.assertTrue(result)
        self.assertEqual(root["children"][0].get("children", []), [])

    def test_remove_node_by_id_not_found(self):
        root = {"id": "root", "children": [{"id": "a"}]}
        result = self.linked_cleanup.remove_node_by_id(root, "missing")
        self.assertFalse(result)

    def test_remove_node_by_id_non_dict_returns_false(self):
        self.assertFalse(self.linked_cleanup.remove_node_by_id("notadict", "x"))

    def test_remove_linked_node(self):
        payload = {"data": {"id": "root", "children": [{"id": "target"}]}}
        self.linked_cleanup.remove_linked_node(payload, "target")
        self.assertEqual(payload["data"]["children"], [])

    def test_remove_linked_node_no_data_key(self):
        payload = {"meta": {}}
        # Should not raise
        self.linked_cleanup.remove_linked_node(payload, "target")

    def test_load_target_map(self):
        target_note = FakeNote(2, Data=json.dumps({"data": {}}))
        self.mw.col = FakeCollection(notes={2: target_note})
        note, data = self.linked_cleanup.load_target_map(self.mw, 2)
        self.assertIs(note, target_note)
        self.assertEqual(data, {"data": {}})

    def test_cleanup_linked_nodes_on_delete_removes_linked_nodes(self):
        source_note = FakeNote(
            1,
            Data=json.dumps({
                "data": {
                    "linkedMaps": [
                        {"targetMapId": 2, "linkedNodeId": "node:1"}
                    ]
                }
            }),
        )
        target_note = FakeNote(
            2,
            Data=json.dumps({
                "data": {
                    "id": "root",
                    "children": [
                        {"id": "node:1"},
                        {"id": "node:2"},
                    ]
                }
            }),
        )
        self.mw.col = FakeCollection(notes={1: source_note, 2: target_note})
        self.linked_cleanup.cleanup_linked_nodes_on_delete(self.mw, 1)
        updated = self.mw.col.updated_notes
        self.assertEqual(len(updated), 1)
        self.assertIs(updated[0], target_note)
        data = json.loads(target_note["Data"])
        self.assertEqual(data["data"]["children"], [{"id": "node:2"}])

    def test_cleanup_linked_nodes_on_delete_skips_missing_target(self):
        source_note = FakeNote(
            1,
            Data=json.dumps({
                "data": {
                    "linkedMaps": [
                        {"targetMapId": 99, "linkedNodeId": "node:1"}
                    ]
                }
            }),
        )
        self.mw.col = FakeCollection(notes={1: source_note})
        # Should not raise even though target 99 is missing
        self.linked_cleanup.cleanup_linked_nodes_on_delete(self.mw, 1)
        self.assertEqual(self.mw.col.updated_notes, [])

    def test_cleanup_linked_nodes_on_delete_skips_missing_ids(self):
        source_note = FakeNote(
            1,
            Data=json.dumps({
                "data": {
                    "linkedMaps": [
                        {"targetMapId": None, "linkedNodeId": "node:1"},
                        {"targetMapId": 2, "linkedNodeId": None},
                    ]
                }
            }),
        )
        target_note = FakeNote(2, Data=json.dumps({"data": {"id": "root"}}))
        self.mw.col = FakeCollection(notes={1: source_note, 2: target_note})
        self.linked_cleanup.cleanup_linked_nodes_on_delete(self.mw, 1)
        self.assertEqual(self.mw.col.updated_notes, [])

    def test_cleanup_linked_nodes_on_delete_swallows_source_exception(self):
        self.mw.col = FakeCollection(notes={})
        # source_map_id 1 does not exist
        self.linked_cleanup.cleanup_linked_nodes_on_delete(self.mw, 1)
        self.assertEqual(self.mw.col.updated_notes, [])


class MindMapManagerFacadeTests(unittest.TestCase):
    def setUp(self):
        self.mw, self.utils, self.hooks = install_anki_stubs()
        _clear_package_modules()
        mindmap_editor = types.ModuleType(f"{PACKAGE_NAME}.mindmap_editor")
        mindmap_editor.MindMapDialog = types.SimpleNamespace(open_instance=lambda *args: None)
        sys.modules[f"{PACKAGE_NAME}.mindmap_editor"] = mindmap_editor

        # Stub the notes subpackage so ``from .notes.creation import ...`` works.
        notes_pkg = types.ModuleType(f"{PACKAGE_NAME}.notes")
        notes_pkg.__path__ = []
        sys.modules[f"{PACKAGE_NAME}.notes"] = notes_pkg
        creation = types.ModuleType(f"{PACKAGE_NAME}.notes.creation")
        creation.create_new_mindmap_note = lambda title, uid: 999
        sys.modules[f"{PACKAGE_NAME}.notes.creation"] = creation
        notes_pkg.creation = creation

        # Stub export.export_mindmap (used inside MindMapManager methods).
        export_pkg = types.ModuleType(f"{PACKAGE_NAME}.export")
        export_pkg.__path__ = []
        sys.modules[f"{PACKAGE_NAME}.export"] = export_pkg
        export_mindmap = types.ModuleType(f"{PACKAGE_NAME}.export.export_mindmap")
        export_mindmap.export_mindmap_to_json = lambda *args: (True, "/tmp/out.json", None)
        sys.modules[f"{PACKAGE_NAME}.export.export_mindmap"] = export_mindmap
        export_pkg.export_mindmap = export_mindmap

        self.mindmap_manager = import_plugin_module("mindmap_manager")

    def test_manager_delegates_to_note_utils(self):
        manager = self.mindmap_manager.MindMapManager(self.mw)
        note = FakeNote(1, Title="T", AllowNewCards="1", Data=json.dumps({"data": {}}))
        self.assertEqual(manager._get_note_title(note), "T")
        self.assertEqual(manager._get_allow_new_cards(note), "1")
        self.assertEqual(manager._load_note_data(note), {"data": {}})
        manager._save_note_data(note, {"data": {"id": "root"}})
        self.assertEqual(json.loads(note["Data"]), {"data": {"id": "root"}})

    def test_manager_remove_node_by_id(self):
        manager = self.mindmap_manager.MindMapManager(self.mw)
        data = {"data": {"id": "root", "children": [{"id": "child"}, {"id": "keep"}]}}
        manager._remove_linked_node(data, "child")
        self.assertEqual(data["data"]["children"], [{"id": "keep"}])

    def test_manager_get_selected_nid_out_of_range(self):
        manager = self.mindmap_manager.MindMapManager(self.mw)
        manager.notes = [("A", 1)]
        manager.list_widget.setCurrentRow(3)
        self.assertIsNone(manager.get_selected_nid())

    def test_refresh_list_populates_notes(self):
        note = FakeNote(1, Title="Map A", AllowNewCards="1", Data=json.dumps({"data": {}}))
        self.mw.col = FakeCollection(notes={1: note})
        manager = self.mindmap_manager.MindMapManager(self.mw)
        self.assertEqual(manager.notes, [("Map A", 1)])
        self.assertEqual(manager.list_widget.items, ["✓ Map A"])


if __name__ == "__main__":
    unittest.main()
