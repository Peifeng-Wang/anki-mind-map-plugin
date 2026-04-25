import json
import sys
import unittest
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

from mindmap_editor.sync import (
    sync_nodes_to_cards,
    sync_map_linked_nodes,
    sync_to_linked_node,
    sync_map_link_content,
    _BR_RE,
    _HTML_TAG_RE,
)


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

        mock_card_linker = MagicMock()
        mock_card_linker._syncing_from_node = False
        sys.modules['mindmap_editor.card_linker'] = mock_card_linker
        import mindmap_editor
        mindmap_editor.card_linker = mock_card_linker

        sync_nodes_to_cards(self.dialog, [
            {"id": "n1", "topic": "New Topic", "noteId": 100}
        ])
        self.assertEqual(card_note["Front"], "New Topic")
        self.dialog.mw.col.update_note.assert_called()

    @patch('mindmap_editor.sync.sync_map_link_content')
    def test_sync_map_linked_nodes(self, mock_sync_map_link_content):
        self.dialog.note = {"Data": json.dumps({"data": {"id": "root", "topic": "Root", "isMapLink": True, "sourceMapId": 2, "children": []}})}
        sync_map_linked_nodes(self.dialog, [
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
