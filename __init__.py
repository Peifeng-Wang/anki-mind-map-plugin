from aqt import mw, gui_hooks
from aqt.qt import *
from aqt.utils import tooltip
from typing import Any
from .card_linker.constants import MINDMAP_NOTE_TYPE_QUERY
from .mindmap_manager import MindMapManager
from .usage_guide import show_usage

# Ensure newly-added config keys appear for users with an existing overridden config.
def _deep_merge_defaults(user_value: Any, default_value: Any) -> tuple[Any, bool]:
    """Merge default_value into user_value without overwriting existing user values."""
    if isinstance(default_value, dict):
        if not isinstance(user_value, dict):
            return default_value, True
        changed = False
        for key, def_val in default_value.items():
            if key not in user_value:
                user_value[key] = def_val
                changed = True
            else:
                merged, was_changed = _deep_merge_defaults(user_value[key], def_val)
                user_value[key] = merged
                changed = changed or was_changed
        return user_value, changed

    # For non-dict defaults, only fill in when missing at the dict level.
    return user_value, False


def _ensure_config_defaults() -> None:
    try:
        defaults = mw.addonManager.addonConfigDefaults(__name__) or {}
    except Exception:
        # Fallback for older Anki builds.
        try:
            import json
            from pathlib import Path

            defaults_path = Path(__file__).with_name("config.json")
            defaults = json.loads(defaults_path.read_text(encoding="utf-8"))
        except Exception:
            defaults = {}

    if not isinstance(defaults, dict) or not defaults:
        return

    try:
        user_config = mw.addonManager.getConfig(__name__) or {}
        merged, changed = _deep_merge_defaults(user_config, defaults)
        if changed:
            mw.addonManager.writeConfig(__name__, merged)
    except Exception:
        # Avoid breaking startup if config can't be accessed yet.
        return


_ensure_config_defaults()

# Ensure model is up-to-date when collection loads (one-time migration)
def on_collection_loaded(col):
    _ensure_config_defaults()
    from .note_manager import get_or_create_mindmap_model
    get_or_create_mindmap_model()

gui_hooks.collection_did_load.append(on_collection_loaded)

def on_open_manager():
    # We keep a reference to avoid GC
    mw.mindmap_manager = MindMapManager(mw)
    mw.mindmap_manager.show()

def open_last_mindmap():
    """Open the last used mind map, or the first available one"""
    from .mindmap_editor import MindMapDialog

    # Get last used mind map ID from config
    config = mw.addonManager.getConfig(__name__)
    if not config:
        config = {}
    
    last_id = config.get('last_mindmap_id')
    
    # Try to open last used mind map
    if last_id:
        try:
            note = mw.col.get_note(last_id)
            MindMapDialog.open_instance(mw, last_id)
            return
        except Exception:
            pass  # Last mind map doesn't exist, continue to open first one
    
    # If no last used or it doesn't exist, open first mind map
    ids = mw.col.find_notes(MINDMAP_NOTE_TYPE_QUERY)
    if not ids:
        tooltip("No mind maps found. Create one first from Tools > Mind Map > Mind Map Manager")
        return
    
    # Open first mind map
    first_id = ids[0]
    MindMapDialog.open_instance(mw, first_id)

# Setup Menu
action_manager = QAction("Mind Map Manager", mw)
action_manager.triggered.connect(on_open_manager)

action_usage = QAction("Usage Guide", mw)
action_usage.triggered.connect(show_usage)

action_backup = QAction("Backup & Recovery", mw)
from .mindmap_backup import show_backup_dialog
action_backup.triggered.connect(show_backup_dialog)

action_quick = QAction("Quick Open Mind Map", mw)
action_quick.triggered.connect(open_last_mindmap)
# Get shortcut from config, default to Ctrl+M
config = mw.addonManager.getConfig(__name__) or {}
shortcut_key = config.get('quick_open_shortcut', 'Ctrl+M')
action_quick.setShortcut(QKeySequence(shortcut_key))
# Show shortcut in menu item text
action_quick.setText(f"Quick Open Mind Map ({shortcut_key})")

menu = mw.form.menuTools.addMenu("Mind Map")
menu.addAction(action_manager)
menu.addAction(action_usage)
menu.addAction(action_backup)
menu.addSeparator()
menu.addAction(action_quick)

from .card_linker import init_card_linker
init_card_linker()

# Import review indicator for mind map associations
from . import review_indicator

