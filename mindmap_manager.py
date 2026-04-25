from aqt.qt import *
from aqt.utils import showInfo, getText, askUser, tooltip
from .note_manager import create_new_mindmap_note
from .mindmap_editor import MindMapDialog
import json
import os
import uuid


NOTE_QUERY = '"note:MindMap Master"'
FIELD_TITLE = 'Title'
FIELD_DATA = 'Data'
FIELD_ALLOW_NEW_CARDS = 'AllowNewCards'
ALLOW_NEW_CARDS_ENABLED = "1"
ALLOW_NEW_CARDS_DISABLED = "0"
ACTIVE_ICON = "✓"
INACTIVE_ICON = "✗"


class MindMapManager(QDialog):
    def __init__(self, mw):
        super().__init__(mw)
        self.mw = mw
        self.notes = []
        self._setup_ui()
        self.refresh_list()

    def _setup_ui(self):
        self.setWindowTitle("Mind Map Manager")
        self.resize(600, 400)

        self.layout = QVBoxLayout(self)

        # List Widget
        self.list_widget = QListWidget()
        self.list_widget.itemDoubleClicked.connect(self.on_open)
        self.layout.addWidget(self.list_widget)

        # Buttons
        btn_layout = QHBoxLayout()

        self._add_button(btn_layout, "New", self.on_new)
        self._add_button(btn_layout, "Open", self.on_open)
        self._add_button(btn_layout, "Rename", self.on_rename)
        self._add_button(btn_layout, "Delete", self.on_delete)
        self._add_button(btn_layout, "Toggle Active", self.on_toggle_active)

        btn_export = self._add_button(btn_layout, "Export", self.on_export)
        btn_export.setStyleSheet("background-color: #28a745; color: white; font-weight: bold;")

        self.layout.addLayout(btn_layout)

    def _add_button(self, layout, text, callback):
        button = QPushButton(text)
        button.clicked.connect(callback)
        layout.addWidget(button)
        return button

    def refresh_list(self):
        self.list_widget.clear()
        self.notes = []

        ids = self.mw.col.find_notes(NOTE_QUERY)
        for nid in ids:
            note = self.mw.col.get_note(nid)
            title = self._get_note_title(note)
            allow_new = self._get_allow_new_cards(note)
            status_icon = ACTIVE_ICON if allow_new == ALLOW_NEW_CARDS_ENABLED else INACTIVE_ICON
            display_text = f"{status_icon} {title}"

            self.notes.append((title, nid))
            self.list_widget.addItem(display_text)

    def get_selected_nid(self):
        row = self.list_widget.currentRow()
        if row < 0 or row >= len(self.notes):
            return None
        return self.notes[row][1]

    def _get_selected_title(self):
        row = self.list_widget.currentRow()
        if row < 0 or row >= len(self.notes):
            return None
        return self.notes[row][0]

    def _get_note_title(self, note):
        return note[FIELD_TITLE]

    def _get_allow_new_cards(self, note):
        try:
            return note[FIELD_ALLOW_NEW_CARDS]
        except KeyError:
            # Default to enabled if older notes do not have this field.
            return ALLOW_NEW_CARDS_ENABLED

    def _load_note_data(self, note):
        return json.loads(note[FIELD_DATA])

    def _save_note_data(self, note, data):
        note[FIELD_DATA] = json.dumps(data)

    def _sync_root_title(self, note, new_title):
        try:
            data = self._load_note_data(note)
            if data.get('nodeData') and data['nodeData'].get('id') == 'root':
                data['nodeData']['topic'] = new_title
                self._save_note_data(note, data)
        except Exception:
            pass

    def on_new(self):
        title, ok = getText("Enter a title for the new Mind Map:")
        if not ok or not title.strip():
            return

        try:
            uid = str(uuid.uuid4())
            note_id = create_new_mindmap_note(title, uid)
            self.refresh_list()
            # Select the new item
            # self.list_widget.setCurrentRow(self.list_widget.count() - 1)
            # Open it immediately?
            self.open_editor(note_id)
        except Exception as e:
            showInfo(f"Error creating mind map: {e}")

    def on_open(self):
        nid = self.get_selected_nid()
        if nid:
            self.open_editor(nid)

    def on_rename(self):
        nid = self.get_selected_nid()
        if not nid:
            return

        note = self.mw.col.get_note(nid)
        old_title = self._get_note_title(note)
        new_title, ok = getText("Rename Mind Map:", default=old_title)

        if ok and new_title.strip():
            note[FIELD_TITLE] = new_title
            self._sync_root_title(note, new_title)
            self.mw.col.update_note(note)
            self.refresh_list()

    def on_delete(self):
        nid = self.get_selected_nid()
        if not nid:
            return

        title = self._get_selected_title()

        if askUser(f"Are you sure you want to delete '{title}'? This cannot be undone."):
            # Before deleting, clean up linked nodes in other maps
            self._cleanup_linked_nodes_on_delete(nid)
            self.mw.col.remove_notes([nid])
            self.refresh_list()

    def _cleanup_linked_nodes_on_delete(self, source_map_id):
        """Remove linked nodes in other maps that point to this map"""
        try:
            source_note = self.mw.col.get_note(source_map_id)
            source_data = self._load_note_data(source_note)
            linked_maps = self._get_linked_maps(source_data)

            for link in linked_maps:
                target_map_id = link.get('targetMapId')
                linked_node_id = link.get('linkedNodeId')

                if not target_map_id or not linked_node_id:
                    continue

                try:
                    target_note, target_data = self._load_target_map(target_map_id)
                    self._remove_linked_node(target_data, linked_node_id)

                    self._save_note_data(target_note, target_data)
                    self.mw.col.update_note(target_note)

                    print(f"Removed linked node {linked_node_id} from map {target_map_id}")
                    self._refresh_editor_if_open(target_map_id)

                except Exception as e:
                    print(f"Error cleaning up linked node in map {target_map_id}: {e}")

        except Exception as e:
            print(f"Error during cleanup on delete: {e}")

    def _get_linked_maps(self, map_data):
        source_root = map_data.get('data', {})
        return source_root.get('linkedMaps', [])

    def _load_target_map(self, target_map_id):
        target_note = self.mw.col.get_note(target_map_id)
        return target_note, self._load_note_data(target_note)

    def _remove_linked_node(self, map_data, linked_node_id):
        if 'data' in map_data:
            self._remove_node_by_id(map_data['data'], linked_node_id)

    def _remove_node_by_id(self, node, node_id, parent_children_list=None, index=None):
        if not isinstance(node, dict):
            return False

        if node.get('id') == node_id:
            if parent_children_list is not None and index is not None:
                parent_children_list.pop(index)
                return True

        if 'children' in node:
            for child_index, child in enumerate(list(node['children'])):
                if self._remove_node_by_id(child, node_id, node['children'], child_index):
                    return True

        return False

    def _refresh_editor_if_open(self, target_map_id):
        if hasattr(self.mw, 'mindmap_editors'):
            for editor in self.mw.mindmap_editors:
                if editor.note_id == target_map_id:
                    editor._handle_refresh()
                    break

    def on_toggle_active(self):
        """Toggle whether this mind map allows new card associations"""
        nid = self.get_selected_nid()
        if not nid:
            return

        note = self.mw.col.get_note(nid)

        # Try to get current value
        try:
            current_value = note[FIELD_ALLOW_NEW_CARDS]
        except KeyError:
            # Field doesn't exist yet - set default and save
            try:
                note[FIELD_ALLOW_NEW_CARDS] = ALLOW_NEW_CARDS_ENABLED
                self.mw.col.update_note(note)
                # Reload note to ensure field is synced
                note = self.mw.col.get_note(nid)
                current_value = note[FIELD_ALLOW_NEW_CARDS]
            except KeyError:
                # Still can't access field - something is wrong with model
                showInfo("Error: AllowNewCards field not found. Please restart Anki.")
                return

        # Toggle: 1 -> 0, 0 -> 1
        new_value = (
            ALLOW_NEW_CARDS_DISABLED
            if current_value == ALLOW_NEW_CARDS_ENABLED
            else ALLOW_NEW_CARDS_ENABLED
        )

        # Set new value
        try:
            note[FIELD_ALLOW_NEW_CARDS] = new_value
            self.mw.col.update_note(note)

            status = "Active" if new_value == ALLOW_NEW_CARDS_ENABLED else "Inactive"
            tooltip(f"Mind map set to: {status}")

            self.refresh_list()
        except KeyError:
            showInfo("Error updating field. Please restart Anki.")
            self.refresh_list()

    def on_export(self):
        """Export the selected mind map to JSON + HTML viewer"""
        nid = self.get_selected_nid()
        if not nid:
            showInfo("Please select a mind map to export")
            return

        # Use unified export function
        from .export_utils import export_mindmap_to_json

        note = self.mw.col.get_note(nid)
        title = self._get_note_title(note)

        success, filename, viewer_path = export_mindmap_to_json(self, self.mw, nid, title)

        if success:
            if viewer_path:
                tooltip(f"Exported '{title}' with viewer!\nLocation: {os.path.dirname(filename)}")
            else:
                tooltip(f"Exported '{title}'!\nLocation: {filename}")
        else:
            showInfo("Export cancelled or failed")

    def open_editor(self, note_id):
        # Use unified window management method
        MindMapDialog.open_instance(self.mw, note_id)
