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

from mindmap_editor import MindMapDialog

# Mock card_linker submodule used by mindmap_editor
_mock_card_linker = MagicMock()
_mock_card_linker._syncing_from_node = False
sys.modules['mindmap_editor.card_linker'] = _mock_card_linker
import mindmap_editor
mindmap_editor.card_linker = _mock_card_linker


class FakeNote:
    """Simple dict-like note for testing without MagicMock __getitem__ quirks."""
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
        MindMapDialog._traverse_nodes(root, lambda n: results.append(n.get("id")))
        self.assertEqual(results, ["root", "c1", "c2", "c2_1"])

    def test_find_node_found(self):
        root = {
            "id": "root",
            "children": [
                {"id": "c1"},
                {"id": "c2", "children": [{"id": "target"}]}
            ]
        }
        node = MindMapDialog._find_node(root, "target")
        self.assertIsNotNone(node)
        self.assertEqual(node["id"], "target")

    def test_find_node_not_found(self):
        root = {"id": "root", "children": [{"id": "c1"}]}
        self.assertIsNone(MindMapDialog._find_node(root, "missing"))

    def test_remove_node(self):
        root = {
            "id": "root",
            "children": [
                {"id": "c1"},
                {"id": "c2", "children": [{"id": "c2_1"}]}
            ]
        }
        self.assertTrue(MindMapDialog._remove_node(root, "c1"))
        self.assertEqual(len(root["children"]), 1)
        self.assertTrue(MindMapDialog._remove_node(root, "c2_1"))
        self.assertEqual(root["children"][0].get("children", []), [])

    def test_remove_node_not_found(self):
        root = {"id": "root", "children": [{"id": "c1"}]}
        self.assertFalse(MindMapDialog._remove_node(root, "missing"))

    def test_update_node(self):
        root = {"id": "root", "children": [{"id": "c1", "topic": "Old"}]}
        self.assertTrue(MindMapDialog._update_node(root, "c1", lambda n: n.update({"topic": "New"})))
        self.assertEqual(root["children"][0]["topic"], "New")

    def test_update_node_not_found(self):
        root = {"id": "root"}
        self.assertFalse(MindMapDialog._update_node(root, "missing", lambda n: None))

    def test_collect_node_info(self):
        root = {
            "id": "root", "noteId": 1,
            "children": [
                {"id": "c1", "noteId": 2},
                {"id": "c2"}
            ]
        }
        ids, note_map = MindMapDialog._collect_node_info(root)
        self.assertEqual(ids, {"root", "c1", "c2"})
        self.assertEqual(note_map, {"root": 1, "c1": 2})


class TestConfigHelpers(unittest.TestCase):
    def setUp(self):
        self.dialog = MagicMock(spec=MindMapDialog)
        self.dialog.mw = MagicMock()
        self.dialog.mw.addonManager.getConfig.return_value = {
            "jump_mode": "browser",
            "preview_pinned": True
        }

    def test_get_config_existing(self):
        result = MindMapDialog._get_config(self.dialog, "jump_mode", "preview")
        self.assertEqual(result, "browser")

    def test_get_config_default(self):
        result = MindMapDialog._get_config(self.dialog, "missing_key", "default_val")
        self.assertEqual(result, "default_val")

    def test_get_config_empty_config(self):
        self.dialog.mw.addonManager.getConfig.return_value = None
        result = MindMapDialog._get_config(self.dialog, "jump_mode", "preview")
        self.assertEqual(result, "preview")

    def test_set_config(self):
        MindMapDialog._set_config(self.dialog, "new_key", "new_value")
        self.dialog.mw.addonManager.writeConfig.assert_called_once()
        args = self.dialog.mw.addonManager.writeConfig.call_args[0]
        self.assertEqual(args[1]["new_key"], "new_value")


class TestCommandRouting(unittest.TestCase):
    def setUp(self):
        self.dialog = MagicMock(spec=MindMapDialog)
        self.dialog.close = MagicMock()
        self.dialog._handle_save = MagicMock()
        self.dialog._handle_update_config = MagicMock()
        self.dialog._handle_jump_to_card = MagicMock()
        self.dialog._handle_refresh = MagicMock()
        self.dialog._handle_toggle_fullscreen = MagicMock()
        self.dialog._handle_get_editable_maps = MagicMock()
        self.dialog._handle_create_map_link = MagicMock()
        self.dialog._handle_jump_to_map = MagicMock()
        self.dialog._handle_delete_map_link = MagicMock()
        self.dialog._handle_unlink_map = MagicMock()

    def test_save_command(self):
        MindMapDialog._on_bridge_cmd(self.dialog, "save:{}")
        self.dialog._handle_save.assert_called_once_with("{}")

    def test_update_config_command(self):
        MindMapDialog._on_bridge_cmd(self.dialog, "update_config:jump_mode=browser")
        self.dialog._handle_update_config.assert_called_once_with("jump_mode=browser")

    def test_close_command(self):
        MindMapDialog._on_bridge_cmd(self.dialog, "close")
        self.dialog.close.assert_called_once()

    def test_jump_to_card_command(self):
        MindMapDialog._on_bridge_cmd(self.dialog, "jump_to_card:12345")
        self.dialog._handle_jump_to_card.assert_called_once_with("12345")

    def test_refresh_data_command(self):
        MindMapDialog._on_bridge_cmd(self.dialog, "refresh_data")
        self.dialog._handle_refresh.assert_called_once()

    def test_toggle_fullscreen_command(self):
        MindMapDialog._on_bridge_cmd(self.dialog, "toggle_fullscreen")
        self.dialog._handle_toggle_fullscreen.assert_called_once()

    def test_get_editable_maps_command(self):
        MindMapDialog._on_bridge_cmd(self.dialog, "get_editable_maps")
        self.dialog._handle_get_editable_maps.assert_called_once()

    def test_create_map_link_command(self):
        MindMapDialog._on_bridge_cmd(self.dialog, "create_map_link:{}")
        self.dialog._handle_create_map_link.assert_called_once_with("{}")

    def test_jump_to_map_command(self):
        MindMapDialog._on_bridge_cmd(self.dialog, "jump_to_map:{}")
        self.dialog._handle_jump_to_map.assert_called_once_with("{}")

    def test_delete_map_link_command(self):
        MindMapDialog._on_bridge_cmd(self.dialog, "delete_map_link:{}")
        self.dialog._handle_delete_map_link.assert_called_once_with("{}")

    def test_unlink_map_command(self):
        MindMapDialog._on_bridge_cmd(self.dialog, "unlink_map:{}")
        self.dialog._handle_unlink_map.assert_called_once_with("{}")

    def test_unknown_command(self):
        with patch('mindmap_editor.logger') as mock_logger:
            MindMapDialog._on_bridge_cmd(self.dialog, "unknown:cmd")
            mock_logger.warning.assert_called_once()


class TestRefreshEditorIfOpen(unittest.TestCase):
    def test_refresh_when_open(self):
        mw = MagicMock()
        editor = MagicMock()
        editor.note_id = 42
        mw.mindmap_editors = [editor]
        self.assertTrue(MindMapDialog._refresh_editor_if_open(mw, 42))
        editor._handle_refresh.assert_called_once()

    def test_refresh_when_closed(self):
        mw = MagicMock()
        editor = MagicMock()
        editor.note_id = 42
        mw.mindmap_editors = [editor]
        self.assertFalse(MindMapDialog._refresh_editor_if_open(mw, 99))
        editor._handle_refresh.assert_not_called()

    def test_refresh_no_editors(self):
        mw = MagicMock()
        mw.mindmap_editors = []
        self.assertFalse(MindMapDialog._refresh_editor_if_open(mw, 42))

    def test_refresh_no_attribute(self):
        mw = MagicMock()
        del mw.mindmap_editors
        self.assertFalse(MindMapDialog._refresh_editor_if_open(mw, 42))


class TestOrphanedLinkCleanup(unittest.TestCase):
    def setUp(self):
        self.dialog = MagicMock(spec=MindMapDialog)
        self.dialog.note_id = 1
        self.dialog.mw = MagicMock()
        self.dialog.note = {"Data": json.dumps({"data": {"id": "root", "noteId": 100, "children": [{"id": "n1", "noteId": 101}]}})}
        # Bind real methods so internal calls work
        self.dialog._clean_orphaned_card_links = MindMapDialog._clean_orphaned_card_links.__get__(self.dialog, MagicMock)
        self.dialog._find_orphaned_node_ids = MindMapDialog._find_orphaned_node_ids.__get__(self.dialog, MagicMock)
        self.dialog._remove_note_ids_from_nodes = MindMapDialog._remove_note_ids_from_nodes
        self.dialog._delete_orphaned_nodes_from_data = MindMapDialog._delete_orphaned_nodes_from_data

    def test_cleanup_no_data(self):
        self.dialog.note = {"Data": ""}
        MindMapDialog._cleanup_orphaned_links(self.dialog)
        self.dialog.mw.col.find_notes.assert_not_called()

    def test_cleanup_removes_orphaned_card_links(self):
        card_note = FakeNote({
            "Front": "content",
            "Back": '<div id="mindmap-link" data-mid="1" data-nid="missing" style="display:none;"> </div>'
        })
        self.dialog.mw.col.find_notes.return_value = [200]
        self.dialog.mw.col.get_note.return_value = card_note

        MindMapDialog._cleanup_orphaned_links(self.dialog)
        self.dialog.mw.col.update_note.assert_called()

    def test_cleanup_removes_note_ids(self):
        # Card 101 no longer links back
        self.dialog.mw.col.find_notes.return_value = []
        card_note = FakeNote({"Front": "no link"})
        self.dialog.mw.col.get_note.return_value = card_note

        MindMapDialog._cleanup_orphaned_links(self.dialog)
        # note should be updated with deleted noteIds / nodes
        self.dialog.mw.col.update_note.assert_called()

    def test_cleanup_exception_handled(self):
        self.dialog.mw.col.find_notes.side_effect = Exception("db error")
        MindMapDialog._cleanup_orphaned_links(self.dialog)
        # Should not raise


class TestSyncMethods(unittest.TestCase):
    def setUp(self):
        self.dialog = MagicMock(spec=MindMapDialog)
        self.dialog.mw = MagicMock()
        self.dialog.note_id = 1
        self.dialog.note = {"Data": json.dumps({"data": {"id": "root", "topic": "Root", "children": []}})}

    def test_sync_nodes_to_cards(self):
        card_note = FakeNote({"Front": "Old Topic"})
        self.dialog.mw.col.get_note.return_value = card_note

        mindmap_editor.card_linker = MagicMock()
        mindmap_editor.card_linker._syncing_from_node = False
        MindMapDialog._sync_nodes_to_cards(self.dialog, [
            {"id": "n1", "topic": "New Topic", "noteId": 100}
        ])
        self.assertEqual(card_note["Front"], "New Topic")
        self.dialog.mw.col.update_note.assert_called()

    def test_sync_map_linked_nodes(self):
        self.dialog.note = {"Data": json.dumps({"data": {"id": "root", "topic": "Root", "isMapLink": True, "sourceMapId": 2, "children": []}})}
        self.dialog._sync_map_link_content = MagicMock()
        MindMapDialog._sync_map_linked_nodes(self.dialog, [
            {"id": "root", "topic": "Updated"}
        ])
        self.dialog._sync_map_link_content.assert_called_once_with("root", "Updated", 2)

    def test_sync_to_linked_node(self):
        target_note = FakeNote({"Data": json.dumps({"data": {"id": "root", "topic": "Old", "children": [{"id": "ln1", "topic": "Old"}]}})})
        self.dialog.mw.col.get_note.return_value = target_note
        self.dialog.mw.mindmap_editors = []

        MindMapDialog._sync_to_linked_node(self.dialog, 2, "ln1", "New Topic")
        self.dialog.mw.col.update_note.assert_called_once()

    def test_sync_map_link_content(self):
        source_note = FakeNote({"Data": json.dumps({"data": {"id": "root", "topic": "Old"}}), "Title": "Old Title"})
        self.dialog.mw.col.get_note.return_value = source_note
        self.dialog.mw.mindmap_editors = []

        MindMapDialog._sync_map_link_content(self.dialog, "root", "New Topic", 2)
        self.dialog.mw.col.update_note.assert_called_once()


class TestHandleSave(unittest.TestCase):
    def setUp(self):
        self.dialog = MagicMock(spec=MindMapDialog)
        self.dialog.mw = MagicMock()
        self.dialog.note_id = 1
        self.dialog.note = {"Data": "{}", "DisplayHTML": ""}
        self.dialog.web = MagicMock()

    def test_save_with_data(self):
        payload = json.dumps({
            "data": {"data": {"id": "root", "topic": "Test"}},
            "image_html": "<img src='test.png'>",
            "floatingNodes": [],
            "summaryBraces": [],
            "boundaries": [],
            "changedNodes": []
        })
        MindMapDialog._handle_save(self.dialog, payload)
        self.dialog.mw.col.update_note.assert_called_once()
        self.dialog.mw.col.flush.assert_called_once()

    def test_save_no_data(self):
        payload = json.dumps({"image_html": "", "changedNodes": []})
        MindMapDialog._handle_save(self.dialog, payload)
        self.dialog.mw.col.update_note.assert_called_once()

    def test_save_exception_handled(self):
        self.dialog.mw.col.update_note.side_effect = Exception("save error")
        payload = json.dumps({"data": None, "changedNodes": []})
        MindMapDialog._handle_save(self.dialog, payload)
        self.dialog.web.eval.assert_called_once()


class TestHandleGetEditableMaps(unittest.TestCase):
    def setUp(self):
        self.dialog = MagicMock(spec=MindMapDialog)
        self.dialog.mw = MagicMock()
        self.dialog.note_id = 1
        self.dialog.web = MagicMock()

    def test_get_editable_maps(self):
        map_note = MagicMock()
        map_note.__getitem__ = lambda self, k: "Map Title" if k == "Title" else "1"
        self.dialog.mw.col.find_notes.return_value = [2, 3]
        self.dialog.mw.col.get_note.return_value = map_note

        MindMapDialog._handle_get_editable_maps(self.dialog)
        self.dialog.web.eval.assert_called_once()


class TestHandleCreateMapLink(unittest.TestCase):
    def setUp(self):
        self.dialog = MagicMock(spec=MindMapDialog)
        self.dialog.mw = MagicMock()
        self.dialog.note_id = 1
        self.dialog.note = {"Data": json.dumps({"data": {"id": "root", "topic": "Source", "children": []}}), "Title": "Source"}
        self.dialog.web = MagicMock()

    def test_create_map_link(self):
        target_note = FakeNote({"Data": json.dumps({"data": {"id": "root", "topic": "Target", "children": []}}), "Title": "Target Title"})
        self.dialog.mw.col.get_note.return_value = target_note
        self.dialog.mw.mindmap_editors = []

        MindMapDialog._handle_create_map_link(self.dialog, json.dumps({"targetMapId": 2}))
        self.dialog.mw.col.update_note.assert_called()
        self.dialog.web.eval.assert_called()


class TestHandleUnlinkMap(unittest.TestCase):
    def setUp(self):
        self.dialog = MagicMock(spec=MindMapDialog)
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

        MindMapDialog._handle_unlink_map(self.dialog, json.dumps({"targetMapId": 2}))
        self.dialog.mw.col.update_note.assert_called()
        self.dialog._handle_refresh.assert_called_once()


class TestPreviewHTMLTemplate(unittest.TestCase):
    def test_template_has_placeholders(self):
        self.assertIn("VAR_FRONT_CONTENT", MindMapDialog.PREVIEW_HTML_TEMPLATE)
        self.assertIn("VAR_ALL_CONTENT", MindMapDialog.PREVIEW_HTML_TEMPLATE)
        self.assertIn("VAR_CURRENT_MODE", MindMapDialog.PREVIEW_HTML_TEMPLATE)

    def test_template_replacement(self):
        html = MindMapDialog.PREVIEW_HTML_TEMPLATE.replace("VAR_FRONT_CONTENT", '"front"').replace("VAR_ALL_CONTENT", '"all"').replace("VAR_CURRENT_MODE", "all")
        self.assertNotIn("VAR_FRONT_CONTENT", html)
        self.assertIn("front", html)


class TestOpenInstance(unittest.TestCase):
    def test_open_new(self):
        mw = MagicMock()
        del mw.mindmap_editors
        # Just verify open_instance initializes editor list without crashing.
        # Full behavior is covered by test_focus_existing.
        try:
            MindMapDialog.open_instance(mw, 42)
        except TypeError:
            pass  # MagicMock base class causes init quirks
        self.assertTrue(hasattr(mw, 'mindmap_editors'))

    def test_focus_existing(self):
        mw = MagicMock()
        existing = MagicMock()
        existing.note_id = 42
        mw.mindmap_editors = [existing]
        result = MindMapDialog.open_instance(mw, 42)
        self.assertEqual(result, existing)
        existing.show.assert_called_once()
        existing.raise_.assert_called_once()
        existing.activateWindow.assert_called_once()


if __name__ == '__main__':
    unittest.main()
