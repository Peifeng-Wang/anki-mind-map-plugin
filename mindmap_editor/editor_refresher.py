import logging

logger = logging.getLogger(__name__)


def refresh_editor_if_open(mw, note_id):
    for editor in getattr(mw, 'mindmap_editors', []):
        if editor.note_id == note_id:
            editor._handle_refresh()
            return True
    return False
