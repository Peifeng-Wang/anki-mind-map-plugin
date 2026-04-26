import json
import sys
import unittest
from unittest.mock import MagicMock, patch, PropertyMock

# Mock Anki/Qt before importing the module under test
_mock_aqt = MagicMock()
_mock_qt = MagicMock()
_mock_webview = MagicMock()
_mock_utils = MagicMock()

sys.modules['aqt'] = _mock_aqt
sys.modules['aqt.qt'] = _mock_qt
sys.modules['aqt.webview'] = _mock_webview
sys.modules['aqt.utils'] = _mock_utils

# Provide common Qt names used by the module
_mock_qt.QDialog = MagicMock
_mock_qt.QVBoxLayout = MagicMock
_mock_qt.QShortcut = MagicMock
_mock_qt.QKeySequence = MagicMock
_mock_qt.QUrl = MagicMock
_mock_qt.Qt = MagicMock()
_mock_qt.QWidget = MagicMock
_mock_qt.QHBoxLayout = MagicMock
_mock_qt.QToolButton = MagicMock
_mock_qt.QDialog.__name__ = 'QDialog'

from core.tree_utils import (
    traverse_nodes, find_node, remove_node, update_node, collect_node_info
)


class TestTreeOperations(unittest.TestCase):
    def test_traverse_nodes(self):
        results = []
        root = {
            "id": "root", "topic": "Root",
            "children": [
                {"id": "c1", "topic": "Child1"},
                {"id": "c2", "topic": "Child2", "children": [
                    {"id": "c2_1", "topic": "GrandChild"}
                ]}
            ]
        }
        traverse_nodes(root, lambda n: results.append(n.get("id")))
        self.assertEqual(results, ["root", "c1", "c2", "c2_1"])

    def test_find_node_found(self):
        root = {
            "id": "root",
            "children": [
                {"id": "c1"},
                {"id": "c2", "children": [{"id": "target"}]}
            ]
        }
        node = find_node(root, "target")
        self.assertIsNotNone(node)
        self.assertEqual(node["id"], "target")

    def test_find_node_not_found(self):
        root = {"id": "root", "children": [{"id": "c1"}]}
        self.assertIsNone(find_node(root, "missing"))

    def test_remove_node(self):
        root = {
            "id": "root",
            "children": [
                {"id": "c1"},
                {"id": "c2", "children": [{"id": "c2_1"}]}
            ]
        }
        self.assertTrue(remove_node(root, "c1"))
        self.assertEqual(len(root["children"]), 1)
        self.assertTrue(remove_node(root, "c2_1"))
        self.assertEqual(root["children"][0].get("children", []), [])

    def test_remove_node_not_found(self):
        root = {"id": "root", "children": [{"id": "c1"}]}
        self.assertFalse(remove_node(root, "missing"))

    def test_update_node(self):
        root = {"id": "root", "children": [{"id": "c1", "topic": "Old"}]}
        self.assertTrue(update_node(root, "c1", lambda n: n.update({"topic": "New"})))
        self.assertEqual(root["children"][0]["topic"], "New")

    def test_update_node_not_found(self):
        root = {"id": "root"}
        self.assertFalse(update_node(root, "missing", lambda n: None))

    def test_collect_node_info(self):
        root = {
            "id": "root", "noteId": 1,
            "children": [
                {"id": "c1", "noteId": 2},
                {"id": "c2"}
            ]
        }
        ids, note_map = collect_node_info(root)
        self.assertEqual(ids, {"root", "c1", "c2"})
        self.assertEqual(note_map, {"root": 1, "c1": 2})


if __name__ == '__main__':
    unittest.main()
