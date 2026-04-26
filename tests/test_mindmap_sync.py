import importlib
import json
import sys
import types
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

# Mock Anki/Qt before importing the module under test
_mock_aqt = MagicMock()
_mock_qt = MagicMock()
_mock_webview = MagicMock()
_mock_utils = MagicMock()

sys.modules['aqt'] = _mock_aqt
sys.modules['aqt.qt'] = _mock_qt
sys.modules['aqt.webview'] = _mock_webview
sys.modules['aqt.utils'] = _mock_utils

ROOT = Path(__file__).resolve().parents[1]
PACKAGE_NAME = "mindmap_plugin_under_test"
if PACKAGE_NAME not in sys.modules:
    pkg = types.ModuleType(PACKAGE_NAME)
    pkg.__path__ = [str(ROOT)]
    sys.modules[PACKAGE_NAME] = pkg

# Load via the synthetic parent package so relative imports like
# ``from ..core.tree_utils`` resolve.
sync = importlib.import_module(f"{PACKAGE_NAME}.mindmap_editor.sync")
sync_nodes_to_cards = sync.sync_nodes_to_cards
sync_map_linked_nodes = sync.sync_map_linked_nodes
sync_to_linked_node = sync.sync_to_linked_node
sync_map_link_content = sync.sync_map_link_content
_BR_RE = sync._BR_RE
_HTML_TAG_RE = sync._HTML_TAG_RE


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


class TestSyncMethods(unittest.TestCase):
    def setUp(self):
        self.dialog = MagicMock()
        self.dialog.mw = MagicMock()
        self.dialog.note_id = 1
        self.dialog.note = {"Data": json.dumps({"data": {"id": "root", "topic": "Root", "children": []}})}

    def test_sync_nodes_to_cards(self):
        card_note = FakeNote({"Front": "Old Topic"})
        self.dialog.mw.col.get_note.return_value = card_note

        from contextlib import contextmanager

        @contextmanager
        def fake_node_sync():
            yield

        mock_card_linker = MagicMock()
        mock_card_linker.node_sync = fake_node_sync
        # sync.py uses ``from .. import card_linker``; register the stub in the
        # synthetic parent package so the relative import resolves. Restore
        # the previous module on exit so other tests can load the real one.
        cl_key = f'{PACKAGE_NAME}.card_linker'
        previous_cl = sys.modules.get(cl_key)
        previous_attr = getattr(sys.modules[PACKAGE_NAME], 'card_linker', None)
        sys.modules[cl_key] = mock_card_linker
        sys.modules[PACKAGE_NAME].card_linker = mock_card_linker
        try:
            sync_nodes_to_cards(self.dialog, [
                {"id": "n1", "topic": "New Topic", "noteId": 100}
            ])
            self.assertEqual(card_note["Front"], "New Topic")
            self.dialog.mw.col.update_note.assert_called()
        finally:
            if previous_cl is None:
                sys.modules.pop(cl_key, None)
            else:
                sys.modules[cl_key] = previous_cl
            if previous_attr is None:
                if hasattr(sys.modules[PACKAGE_NAME], 'card_linker'):
                    delattr(sys.modules[PACKAGE_NAME], 'card_linker')
            else:
                sys.modules[PACKAGE_NAME].card_linker = previous_attr

    def test_sync_map_linked_nodes(self):
        # Earlier tests may have replaced ``mindmap_editor`` with an empty
        # stub or popped it from sys.modules; re-import the real module.
        sys.modules.pop(f"{PACKAGE_NAME}.mindmap_editor", None)
        sys.modules.pop(f"{PACKAGE_NAME}.mindmap_editor.sync", None)
        sync_mod = importlib.import_module(f"{PACKAGE_NAME}.mindmap_editor.sync")
        with patch.object(sync_mod, 'sync_map_link_content') as mock_sync_map_link_content:
            self.dialog.note = {"Data": json.dumps({"data": {"id": "root", "topic": "Root", "isMapLink": True, "sourceMapId": 2, "children": []}})}
            sync_mod.sync_map_linked_nodes(self.dialog, [
                {"id": "root", "topic": "Updated"}
            ])
            mock_sync_map_link_content.assert_called_once_with(self.dialog, "root", "Updated", 2)

    def test_sync_to_linked_node(self):
        target_note = FakeNote({"Data": json.dumps({"data": {"id": "root", "topic": "Old", "children": [{"id": "ln1", "topic": "Old"}]}})})
        self.dialog.mw.col.get_note.return_value = target_note
        self.dialog.mw.mindmap_editors = []

        sync_to_linked_node(self.dialog, 2, "ln1", "New Topic")
        self.dialog.mw.col.update_note.assert_called_once()

    def test_sync_map_link_content(self):
        source_note = FakeNote({"Data": json.dumps({"data": {"id": "root", "topic": "Old"}}), "Title": "Old Title"})
        self.dialog.mw.col.get_note.return_value = source_note
        self.dialog.mw.mindmap_editors = []

        sync_map_link_content(self.dialog, "root", "New Topic", 2)
        self.dialog.mw.col.update_note.assert_called_once()


class TestClassLevelRegex(unittest.TestCase):
    def test_br_re_splits(self):
        parts = _BR_RE.split("a<br>b<br/>c")
        self.assertEqual(parts, ["a", "b", "c"])

    def test_html_tag_re_strips(self):
        result = _HTML_TAG_RE.sub('', "<b>hello</b>")
        self.assertEqual(result, "hello")


if __name__ == '__main__':
    unittest.main()
