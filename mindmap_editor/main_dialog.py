import json
import logging
import os

from aqt import mw
from aqt.qt import (
    QDialog, QVBoxLayout, QShortcut, QKeySequence, QUrl, Qt,
)
from aqt.webview import AnkiWebView

logger = logging.getLogger(__name__)


class MindMapDialog(QDialog):
    def __init__(self, mw, note_id, focus_node_id=None):
        super().__init__(None)
        self.setWindowFlags(Qt.WindowType.Window)
        self.mw = mw
        self.note_id = note_id
        self.focus_node_id = focus_node_id
        self.note = mw.col.get_note(note_id)
        self.setWindowTitle(f"Mind Map Editor - {self.note['Title']}")
        self.resize(1024, 768)

        # Cache config and save last opened mind map
        config = mw.addonManager.getConfig(__name__) or {}
        self._config = config
        config['last_mindmap_id'] = note_id
        mw.addonManager.writeConfig(__name__, config)

        # Validate and clean up orphaned links before opening
        from .. import card_linker
        card_linker.validate_and_cleanup_mindmap(self.note)
        from .cleanup import cleanup_orphaned_links
        cleanup_orphaned_links(self)

        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)

        # Initialize WebView
        self.web = AnkiWebView(parent=self)
        self.web.set_bridge_command(self._on_bridge_cmd, self)
        self.layout.addWidget(self.web)

        # Load the editor assets
        addon_dir = os.path.dirname(os.path.dirname(__file__))

        try:
            data_json = self.note['Data']
            if not data_json:
                data_json = "{}"

            from .assets import build_editor_html
            html = build_editor_html(self, config, data_json, focus_node_id)

            # Set base URL
            base_url = QUrl.fromLocalFile(os.path.join(addon_dir, "web", "index.html"))
            self.web.setHtml(html, base_url)

            self.undo_shortcut = QShortcut(QKeySequence("Ctrl+Z"), self)
            self.undo_shortcut.activated.connect(lambda: self.web.eval("window.undo();"))

            self.redo_shortcut = QShortcut(QKeySequence("Ctrl+Y"), self)
            self.redo_shortcut.activated.connect(lambda: self.web.eval("window.redo();"))

            self.redo_shortcut_alt = QShortcut(QKeySequence("Ctrl+Shift+Z"), self)
            self.redo_shortcut_alt.activated.connect(lambda: self.web.eval("window.redo();"))

            # Formatting shortcuts for node edit mode (configurable via add-on config.json -> hotkeys).
            hotkeys = self._config.get("hotkeys", {}) if isinstance(self._config, dict) else {}

            def _bind_formatting_hotkey(config_key: str, action: str) -> None:
                seq_str = hotkeys.get(config_key)
                if not isinstance(seq_str, str) or not seq_str.strip():
                    return

                shortcut = QShortcut(QKeySequence(seq_str), self)
                shortcut.setContext(Qt.ShortcutContext.WidgetWithChildrenShortcut)
                shortcut.activated.connect(
                    lambda a=action: self.web.eval(
                        f"window.applyTextFormatting && window.applyTextFormatting({json.dumps(a)});"
                    )
                )
                setattr(self, f"{config_key}_shortcut", shortcut)

            _bind_formatting_hotkey("bold", "bold")
            _bind_formatting_hotkey("italic", "italic")
            _bind_formatting_hotkey("inline_code", "inline_code")
            _bind_formatting_hotkey("code_block", "code_block")

        except Exception as e:
            self.web.setHtml(f"<h1>Error loading assets: {e}</h1>")

    @classmethod
    def open_instance(cls, mw, note_id, focus_node_id=None):
        """Unified window management: open or focus existing mindmap window"""
        # Initialize editor list
        if not hasattr(mw, 'mindmap_editors'):
            mw.mindmap_editors = []

        # Check if already open
        for editor in mw.mindmap_editors:
            if editor.note_id == note_id:
                editor.show()
                editor.raise_()
                editor.activateWindow()
                # Focus on specific node if needed
                if focus_node_id:
                    editor.web.eval(f"if(typeof focusNode === 'function') focusNode({json.dumps(focus_node_id or '')});")
                return editor

        # Create new window
        dialog = cls(mw, note_id, focus_node_id)
        mw.mindmap_editors.append(dialog)
        dialog.show()

        # Remove from list when window closes
        dialog.finished.connect(lambda: mw.mindmap_editors.remove(dialog) if dialog in mw.mindmap_editors else None)

        return dialog

    # ---------- Config helpers ----------
    def _get_config(self, key: str, default=None):
        if not hasattr(self, '_config'):
            self._config = self.mw.addonManager.getConfig(__name__) or {}
        return self._config.get(key, default)

    def _set_config(self, key: str, value):
        if not hasattr(self, '_config'):
            self._config = self.mw.addonManager.getConfig(__name__) or {}
        self._config[key] = value
        self.mw.addonManager.writeConfig(__name__, self._config)

    # ---------- Editor refresh notification ----------
    @staticmethod
    def _refresh_editor_if_open(mw, note_id):
        for editor in getattr(mw, 'mindmap_editors', []):
            if editor.note_id == note_id:
                editor._handle_refresh()
                return True
        return False

    def _on_bridge_cmd(self, cmd: str) -> None:
        handlers = {
            "save:": self._handle_save,
            "update_config:": self._handle_update_config,
            "close": lambda _: self.close(),
            "jump_to_card:": self._handle_jump_to_card,
            "refresh_data": lambda _: self._handle_refresh(),
            "toggle_fullscreen": lambda _: self._handle_toggle_fullscreen(),
            "get_editable_maps": lambda _: self._handle_get_editable_maps(),
            "create_map_link:": self._handle_create_map_link,
            "jump_to_map:": self._handle_jump_to_map,
            "delete_map_link:": self._handle_delete_map_link,
            "unlink_map:": self._handle_unlink_map,
        }
        for prefix, handler in handlers.items():
            if cmd.startswith(prefix):
                payload = cmd[len(prefix):] if prefix.endswith(":") else cmd
                handler(payload)
                return
        logger.warning(f"Unknown command: {cmd}")

    def _handle_update_config(self, params: str):
        """Handle configuration updates from UI"""
        try:
            key, value = params.split('=', 1)
            self._set_config(key, value)
        except Exception as e:
            logger.exception("Error updating config")

    def _handle_jump_to_card(self, note_id_str):
        try:
            nid = int(note_id_str)
            mode = self._get_config('jump_mode', 'preview')

            if mode == 'browser':
                from aqt import dialogs
                browser = dialogs.open("Browser", self.mw)
                browser.search_for(f"nid:{nid}")
            else:
                from .card_preview import _open_card_preview
                _open_card_preview(self, nid)

        except ValueError:
            logger.warning(f"Invalid note ID: {note_id_str}")
        except Exception as e:
            from aqt.utils import showInfo
            showInfo(f"Error jumping to card: {e}")

    def _handle_toggle_fullscreen(self):
        """Toggle fullscreen mode"""
        if self.isFullScreen():
            self.showNormal()
        else:
            self.showFullScreen()

    def _handle_save(self, payload_json: str):
        try:
            payload = json.loads(payload_json)
            data = payload.get("data")
            image_html = payload.get("image_html")
            floating_nodes = payload.get("floatingNodes", [])
            summary_braces = payload.get("summaryBraces", [])
            boundary_data = payload.get("boundaries", [])
            changed_nodes = payload.get("changedNodes", [])

            logger.debug(f"DEBUG: Received changed_nodes: {changed_nodes}")

            # Combine mind map data with floating nodes, summary braces, and boundaries
            if data:
                if isinstance(data, dict):
                    data['floatingNodes'] = floating_nodes
                    data['summaryBraces'] = summary_braces
                    data['boundaries'] = boundary_data
                # Log data to save before saving (for debugging)
                new_data_json = json.dumps(data)
                logger.debug(f"DEBUG: About to save data, length: {len(new_data_json)}, root topic: {data.get('data', {}).get('topic', 'N/A')}")

                self.note['Data'] = new_data_json

            if image_html:
                self.note['DisplayHTML'] = f"<div class='mindmap-static'>{image_html}</div>"

            # Save note
            self.mw.col.update_note(self.note)

            # Sync changed nodes to linked cards
            if changed_nodes:
                logger.debug("DEBUG: Syncing %s changed nodes to cards", len(changed_nodes))
                from .sync import sync_nodes_to_cards, sync_map_linked_nodes
                sync_nodes_to_cards(self, changed_nodes)
                sync_map_linked_nodes(self, changed_nodes)
            else:
                logger.debug("DEBUG: No changed nodes to sync")

            self.web.eval("if(typeof showToast === 'function') showToast('Saved!');")

        except Exception as e:
            logger.exception("Error saving")
            self.web.eval(f"if(typeof showToast === 'function') showToast({json.dumps(f'Error: {e}')});")

    def _handle_refresh(self):
        """Refresh mindmap data"""
        try:
            logger.debug(f"DEBUG: Refresh requested for note {self.note_id}")

            # Force reload latest data from database
            # Clear possible cache first
            self.mw.col.flush()

            # Completely re-fetch note (don't use self.note)
            fresh_note = self.mw.col.get_note(self.note_id)
            data_str = fresh_note['Data']

            logger.debug(f"DEBUG: Loaded fresh data, length: {len(data_str)}")

            # Parse to check root topic
            try:
                import json
                parsed_data = json.loads(data_str)
                root_topic = parsed_data.get('data', {}).get('topic', 'N/A')
                logger.debug(f"DEBUG: Root topic in fresh data: {root_topic}")
            except Exception:
                pass

            # Update self.note with latest data
            self.note = fresh_note

            # Send to JavaScript
            js_code = f"if(typeof reloadMapData === 'function') reloadMapData({data_str});"
            self.web.eval(js_code)
            logger.debug("DEBUG: Refresh command sent to JavaScript")
        except Exception as e:
            logger.exception("Error refreshing")

    def _handle_get_editable_maps(self):
        from .maplinks import handle_get_editable_maps
        handle_get_editable_maps(self)

    def _handle_create_map_link(self, payload):
        from .maplinks import handle_create_map_link
        handle_create_map_link(self, payload)

    def _handle_jump_to_map(self, payload):
        from .maplinks import handle_jump_to_map
        handle_jump_to_map(self, payload)

    def _handle_delete_map_link(self, payload):
        from .maplinks import handle_delete_map_link
        handle_delete_map_link(self, payload)

    def _handle_unlink_map(self, payload):
        from .maplinks import handle_unlink_map
        handle_unlink_map(self, payload)

    def closeEvent(self, event):
        event.accept()
