from aqt.qt import *
from aqt.utils import showInfo, getText, askUser, tooltip
from .notes.creation import create_new_mindmap_note
from .mindmap_editor import MindMapDialog
import json
import os
import uuid

from .manager.note_utils import (
    FIELD_TITLE,
    FIELD_ALLOW_NEW_CARDS,
    ALLOW_NEW_CARDS_ENABLED,
    ALLOW_NEW_CARDS_DISABLED,
    ACTIVE_ICON,
    INACTIVE_ICON,
    NOTE_QUERY,
    get_note_title,
    get_allow_new_cards,
    load_note_data,
    save_note_data,
    sync_root_title,
)
from .manager.linked_cleanup import (
    cleanup_linked_nodes_on_delete,
    remove_linked_node,
)


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
        if hasattr(self.list_widget, "setUpdatesEnabled"):
            self.list_widget.setUpdatesEnabled(False)
        try:
            self.list_widget.clear()
            self.notes = []

            ids = self.mw.col.find_notes(NOTE_QUERY)
            for nid in ids:
                note = self.mw.col.get_note(nid)
                title = get_note_title(note)
                allow_new = get_allow_new_cards(note)
                status_icon = ACTIVE_ICON if allow_new == ALLOW_NEW_CARDS_ENABLED else INACTIVE_ICON
                display_text = f"{status_icon} {title}"

                self.notes.append((title, nid))
                self.list_widget.addItem(display_text)
        finally:
            if hasattr(self.list_widget, "setUpdatesEnabled"):
                self.list_widget.setUpdatesEnabled(True)

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
            sync_root_title(note, new_title)
            self.mw.col.update_note(note)
            self.refresh_list()

    def on_delete(self):
        nid = self.get_selected_nid()
        if not nid:
            return

        title = self._get_selected_title()

        if askUser(f"Are you sure you want to delete '{title}'? This cannot be undone."):
            # Before deleting, clean up linked nodes in other maps
            cleanup_linked_nodes_on_delete(self.mw, nid)
            self.mw.col.remove_notes([nid])
            self.refresh_list()

    def _get_note_title(self, note):
        return get_note_title(note)

    def _get_allow_new_cards(self, note):
        return get_allow_new_cards(note)

    def _load_note_data(self, note):
        return load_note_data(note)

    def _save_note_data(self, note, data):
        save_note_data(note, data)

    def _remove_linked_node(self, map_data, linked_node_id):
        remove_linked_node(map_data, linked_node_id)

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
        from .export.export_mindmap import export_mindmap_to_json

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
