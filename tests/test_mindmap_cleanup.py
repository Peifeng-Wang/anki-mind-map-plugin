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

cleanup = importlib.import_module(f"{PACKAGE_NAME}.mindmap_editor.cleanup")
cleanup_orphaned_links = cleanup.cleanup_orphaned_links
clean_orphaned_card_links = cleanup.clean_orphaned_card_links
find_orphaned_node_ids = cleanup.find_orphaned_node_ids
remove_note_ids_from_nodes = cleanup.remove_note_ids_from_nodes
delete_orphaned_nodes_from_data = cleanup.delete_orphaned_nodes_from_data
_ORPHANED_LINK_RE = cleanup._ORPHANED_LINK_RE


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


class TestOrphanedLinkCleanup(unittest.TestCase):
    def setUp(self):
        self.dialog = MagicMock()
        self.dialog.note_id = 1
        self.dialog.mw = MagicMock()
        self.dialog.note = {"Data": json.dumps({"data": {"id": "root", "noteId": 100, "children": [{"id": "n1", "noteId": 101}]}})}

    def test_cleanup_no_data(self):
        self.dialog.note = {"Data": ""}
        cleanup_orphaned_links(self.dialog)
        self.dialog.mw.col.find_notes.assert_not_called()

    def test_cleanup_removes_orphaned_card_links(self):
        card_note = FakeNote({
            "Front": "content",
            "Back": '<div id="mindmap-link" data-mid="1" data-nid="missing" style="display:none;"> </div>'
        })
        self.dialog.mw.col.find_notes.return_value = [200]
        self.dialog.mw.col.get_note.return_value = card_note

        cleanup_orphaned_links(self.dialog)
        self.dialog.mw.col.update_note.assert_called()

    def test_cleanup_removes_note_ids(self):
        # Card 101 no longer links back
        self.dialog.mw.col.find_notes.return_value = []
        card_note = FakeNote({"Front": "no link"})
        self.dialog.mw.col.get_note.return_value = card_note

        cleanup_orphaned_links(self.dialog)
        # note should be updated with deleted noteIds / nodes
        self.dialog.mw.col.update_note.assert_called()

    def test_cleanup_exception_handled(self):
        self.dialog.mw.col.find_notes.side_effect = Exception("db error")
        cleanup_orphaned_links(self.dialog)
        # Should not raise


class TestFindOrphanedNodeIds(unittest.TestCase):
    def setUp(self):
        self.dialog = MagicMock()
        self.dialog.note_id = 1
        self.dialog.mw = MagicMock()

    def test_note_missing(self):
        self.dialog.mw.col.db.list.return_value = []
        result = find_orphaned_node_ids(self.dialog, {"n1": 101})
        self.assertEqual(result, ["n1"])

    def test_note_exists_no_link(self):
        self.dialog.mw.col.db.list.return_value = [101]
        note = FakeNote({"Front": "no link"})
        self.dialog.mw.col.get_note.return_value = note
        result = find_orphaned_node_ids(self.dialog, {"n1": 101})
        self.assertEqual(result, ["n1"])

    def test_note_exists_with_link(self):
        self.dialog.mw.col.db.list.return_value = [101]
        note = FakeNote({"Front": '<div data-mid="1">link</div>'})
        self.dialog.mw.col.get_note.return_value = note
        result = find_orphaned_node_ids(self.dialog, {"n1": 101})
        self.assertEqual(result, [])


class TestRemoveNoteIdsFromNodes(unittest.TestCase):
    def test_removes_orphaned(self):
        root = {
            "id": "root", "noteId": 100,
            "children": [
                {"id": "n1", "noteId": 101},
                {"id": "n2", "noteId": 102}
            ]
        }
        remove_note_ids_from_nodes(root, {"n1"})
        self.assertNotIn("noteId", root["children"][0])
        self.assertIn("noteId", root["children"][1])


class TestDeleteOrphanedNodesFromData(unittest.TestCase):
    def test_deletes_deep_orphaned_nodes(self):
        root = {
            "id": "root",
            "children": [
                {"id": "c1", "children": [{"id": "c1_1"}, {"id": "orphan1"}]},
                {"id": "c2", "children": [{"id": "orphan2"}]}
            ]
        }
        count = delete_orphaned_nodes_from_data({}, root, {"orphan1", "orphan2"})
        self.assertEqual(count, 2)
        self.assertEqual(len(root["children"][0]["children"]), 1)
        self.assertEqual(len(root["children"][1]["children"]), 0)


class TestClassLevelRegex(unittest.TestCase):
    def test_orphaned_link_re_matches(self):
        html = '<div id="mindmap-link" data-mid="123" data-nid="abc" style="display:none;"> </div>'
        match = _ORPHANED_LINK_RE.search(html)
        self.assertIsNotNone(match)
        self.assertEqual(match.group(1), "123")
        self.assertEqual(match.group(2), "abc")


if __name__ == '__main__':
    unittest.main()
