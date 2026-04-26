import importlib
import json
import sys
import types
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from _aqt_stub import install_aqt_stub

# Mock Anki/Qt before importing the module under test
install_aqt_stub(fake_mw=MagicMock())

ROOT = Path(__file__).resolve().parents[1]
PACKAGE_NAME = "mindmap_plugin_under_test"
if PACKAGE_NAME not in sys.modules:
    pkg = types.ModuleType(PACKAGE_NAME)
    pkg.__path__ = [str(ROOT)]
    sys.modules[PACKAGE_NAME] = pkg

maplinks = importlib.import_module(f"{PACKAGE_NAME}.mindmap_editor.maplinks")
handle_get_editable_maps = maplinks.handle_get_editable_maps
handle_create_map_link = maplinks.handle_create_map_link
handle_jump_to_map = maplinks.handle_jump_to_map
handle_delete_map_link = maplinks.handle_delete_map_link
handle_unlink_map = maplinks.handle_unlink_map


class FakeNote:
    def __init__(self, fields):
        self._fields = fields.copy()
    def keys(self):
        return list(self._fields.keys())
    def __getitem__(self, k):
        return self._fields[k]
    def __setitem__(self, k, v):
        self._fields[k] = v
    def __contains__(self, k):
        return k in self._fields


class TestHandleGetEditableMaps(unittest.TestCase):
    def setUp(self):
        self.dialog = MagicMock()
        self.dialog.mw = MagicMock()
        self.dialog.note_id = 1
        self.dialog.web = MagicMock()

    def test_get_editable_maps(self):
        map_note = MagicMock()
        map_note.__getitem__ = lambda self, k: "Map Title" if k == "Title" else "1"
        self.dialog.mw.col.find_notes.return_value = [2, 3]
        self.dialog.mw.col.get_note.return_value = map_note

        handle_get_editable_maps(self.dialog)
        self.dialog.web.eval.assert_called_once()


class TestHandleCreateMapLink(unittest.TestCase):
    def setUp(self):
        self.dialog = MagicMock()
        self.dialog.mw = MagicMock()
        self.dialog.note_id = 1
        self.dialog.note = {"Data": json.dumps({"data": {"id": "root", "topic": "Source", "children": []}}), "Title": "Source"}
        self.dialog.web = MagicMock()

    def test_create_map_link(self):
        target_note = FakeNote({"Data": json.dumps({"data": {"id": "root", "topic": "Target", "children": []}}), "Title": "Target Title"})
        self.dialog.mw.col.get_note.return_value = target_note
        self.dialog.mw.mindmap_editors = []

        handle_create_map_link(self.dialog, json.dumps({"targetMapId": 2}))
        self.dialog.mw.col.update_note.assert_called()
        self.dialog.web.eval.assert_called()


class TestHandleUnlinkMap(unittest.TestCase):
    def setUp(self):
        self.dialog = MagicMock()
        self.dialog.mw = MagicMock()
        self.dialog.note_id = 1
        self.dialog.note = {"Data": json.dumps({"data": {"id": "root", "topic": "Source", "linkedMaps": [{"targetMapId": 2, "linkedNodeId": "ln1"}], "children": []}})}
        self.dialog.web = MagicMock()

    def test_unlink_map(self):
        target_note = MagicMock()
        target_note.__getitem__ = lambda self, k: json.dumps({"data": {"id": "root", "topic": "Target", "children": [{"id": "ln1"}]}})
        self.dialog.mw.col.get_note.return_value = target_note
        mw = MagicMock()
        mw.mindmap_editors = []
        self.dialog.mw = mw

        handle_unlink_map(self.dialog, json.dumps({"targetMapId": 2}))
        self.dialog.mw.col.update_note.assert_called()
        self.dialog._handle_refresh.assert_called_once()


class TestHandleDeleteMapLink(unittest.TestCase):
    def setUp(self):
        self.dialog = MagicMock()
        self.dialog.mw = MagicMock()
        self.dialog.note_id = 1
        self.dialog.web = MagicMock()

    def test_delete_map_link(self):
        source_note = FakeNote({"Data": json.dumps({"data": {"id": "root", "topic": "Source", "linkedMaps": [{"targetMapId": 2, "linkedNodeId": "ln1"}]}})})
        self.dialog.mw.col.get_note.return_value = source_note
        self.dialog.mw.mindmap_editors = []

        handle_delete_map_link(self.dialog, json.dumps({"sourceMapId": 1, "linkedNodeId": "ln1"}))
        self.dialog.mw.col.update_note.assert_called()


class TestHandleJumpToMap(unittest.TestCase):
    def setUp(self):
        self.dialog = MagicMock()
        self.dialog.mw = MagicMock()
        self.dialog.note_id = 1

    def test_jump_to_map(self):
        # Restore broad aqt mocks in case earlier tests replaced them with
        # narrower stubs that lack symbols main_dialog needs at import time.
        sys.modules['aqt'] = MagicMock()
        sys.modules['aqt.qt'] = MagicMock()
        sys.modules['aqt.webview'] = MagicMock()
        sys.modules['aqt.utils'] = MagicMock()
        sys.modules.pop(f"{PACKAGE_NAME}.mindmap_editor", None)
        sys.modules.pop(f"{PACKAGE_NAME}.mindmap_editor.maplinks", None)
        sys.modules.pop(f"{PACKAGE_NAME}.mindmap_editor.main_dialog", None)
        maplinks_mod = importlib.import_module(f"{PACKAGE_NAME}.mindmap_editor.maplinks")
        main_dialog_mod = importlib.import_module(f"{PACKAGE_NAME}.mindmap_editor.main_dialog")
        with patch.object(main_dialog_mod, 'MindMapDialog') as mock_cls:
            maplinks_mod.handle_jump_to_map(self.dialog, json.dumps({"targetMapId": 2, "focusNodeId": "n1"}))
            mock_cls.open_instance.assert_called_once_with(self.dialog.mw, 2, "n1")


if __name__ == '__main__':
    unittest.main()
