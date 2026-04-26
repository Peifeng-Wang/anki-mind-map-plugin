import logging

from aqt import mw
from aqt.qt import QCursor, QMenu, QTimer
from aqt.utils import tooltip

from .constants import DATA_MID_RE, DATA_NID_RE, MINDMAP_LINK_DIV_RE, MINDMAP_NOTE_TYPE_QUERY, RESET_BUTTON_JS, UPDATE_BUTTON_JS_TEMPLATE
from .core import delete_node_from_mindmap, link_existing_card_to_mindmap
from .utils import parse_mindmap_link
from .validation import remove_link_from_card

logger = logging.getLogger(__name__)


# --- on_editor_load_note sub-functions (P1) ---

def _extract_link_from_note(note):
    """Return (field_name, mindmap_id, node_id) if a valid link exists, else None."""
    for field_name in note.keys():
        field_content = note[field_name]
        if 'mindmap-link' not in field_content or 'data-mid=' not in field_content:
            continue
        match_mid = DATA_MID_RE.search(field_content)
        match_nid = DATA_NID_RE.search(field_content)
        if match_mid and match_nid:
            return field_name, int(match_mid.group(1)), match_nid.group(1)
    return None


def _validate_mindmap_link(mindmap_id, node_id):
    """Return (mindmap_note, mindmap_title, node_exists) or raises on failure."""
    from .utils import find_node_by_id, get_root_node
    import json

    mindmap_note = mw.col.get_note(mindmap_id)
    mindmap_title = mindmap_note['Title']
    data = json.loads(mindmap_note['Data'])
    root = get_root_node(data)
    node_exists = find_node_by_id(root, node_id) is not None
    return mindmap_note, mindmap_title, node_exists


def _apply_link_state(editor, mindmap_id, mindmap_title):
    """Store the validated link state on editor/note and update the button."""
    editor.mindmap_selection = {'id': mindmap_id, 'title': mindmap_title}
    if editor.note:
        editor.note.mindmap_selection = editor.mindmap_selection
    QTimer.singleShot(300, lambda: update_mindmap_button(editor, mindmap_title))
    logger.info("Loaded existing mindmap link: %s", mindmap_title)


def _clear_link_state(editor):
    """Remove any leftover link state from editor and note."""
    if hasattr(editor, 'mindmap_selection'):
        delattr(editor, 'mindmap_selection')
    if editor.note and hasattr(editor.note, 'mindmap_selection'):
        delattr(editor.note, 'mindmap_selection')
    reset_mindmap_button(editor)


def on_editor_load_note(editor):
    """Check mindmap association and update button when editor loads a note."""
    if not (editor.note and editor.note.id):
        # New card: preserve editor selection if present
        if hasattr(editor, 'mindmap_selection') and editor.mindmap_selection:
            if editor.note:
                editor.note.mindmap_selection = editor.mindmap_selection
                logger.info("Preserved mindmap selection for new note: %s", editor.mindmap_selection['title'])
                QTimer.singleShot(300, lambda: update_mindmap_button(editor, editor.mindmap_selection['title']))
        return

    try:
        link_info = _extract_link_from_note(editor.note)
        if not link_info:
            _clear_link_state(editor)
            return

        field_name, mindmap_id, node_id = link_info
        try:
            _, mindmap_title, node_exists = _validate_mindmap_link(mindmap_id, node_id)
        except Exception as exc:
            logger.warning("Mindmap %s no longer exists, cleaning up card link: %s", mindmap_id, exc)
            remove_link_from_card(editor.note, field_name)
            reset_mindmap_button(editor)
            return

        if not node_exists:
            logger.info("Node %s no longer exists in mindmap %s, cleaning up card link", node_id, mindmap_id)
            remove_link_from_card(editor.note, field_name)
            reset_mindmap_button(editor)
            return

        _apply_link_state(editor, mindmap_id, mindmap_title)

    except Exception as exc:
        logger.exception("Error checking for existing mindmap link: %s", exc)


def clear_mindmap_selection(editor):
    """Clear mindmap selection and remove association link from card."""
    if hasattr(editor, 'mindmap_selection'):
        delattr(editor, 'mindmap_selection')
    if editor.note and hasattr(editor.note, 'mindmap_selection'):
        delattr(editor.note, 'mindmap_selection')

    if editor.note and editor.note.id:
        try:
            modified = False
            mindmap_id = None
            node_id = None

            for field_name in editor.note.keys():
                field_content = editor.note[field_name]
                if 'mindmap-link' in field_content:
                    if mindmap_id is None:
                        link = parse_mindmap_link(field_content)
                        if link:
                            mindmap_id, node_id = link
                    new_content = MINDMAP_LINK_DIV_RE.sub('', field_content)
                    if new_content != field_content:
                        editor.note[field_name] = new_content
                        modified = True

            if mindmap_id and node_id:
                delete_node_from_mindmap(mindmap_id, node_id)

            if modified:
                mw.col.update_note(editor.note)
                logger.info("Removed mindmap link from card")
                tooltip("Removed mindmap link from card")
        except Exception as exc:
            logger.exception("Error removing mindmap link: %s", exc)

    reset_mindmap_button(editor)


def reset_mindmap_button(editor):
    """Reset mindmap button to default state."""
    try:
        editor.web.eval(RESET_BUTTON_JS)
    except Exception as exc:
        logger.exception("Error resetting button: %s", exc)


def on_editor_btn_click(editor):
    ids = mw.col.find_notes(MINDMAP_NOTE_TYPE_QUERY)
    if not ids:
        tooltip("No Mind Maps found. Create one first from Tools > Mind Map > Mind Map Manager")
        return

    menu = QMenu(editor.parentWindow)
    menu.setTitle("Select Mind Map")

    clear_action = menu.addAction("❌")
    clear_action.setData(None)
    menu.addSeparator()

    active_count = 0
    for nid in ids:
        note = mw.col.get_note(nid)
        try:
            allow_new = note['AllowNewCards']
        except KeyError:
            allow_new = '1'
        if allow_new == "1":
            title = note['Title']
            action = menu.addAction(title)
            action.setData(nid)
            active_count += 1

    if active_count == 0:
        info_action = menu.addAction("(No active mind maps)")
        info_action.setEnabled(False)

    cursor_pos = QCursor.pos()
    action = menu.exec(cursor_pos)

    if not action:
        return

    nid = action.data()
    if nid is None:
        clear_mindmap_selection(editor)
        tooltip("Removed mindmap link from card")
    else:
        note = mw.col.get_note(nid)
        editor.mindmap_selection = {'id': nid, 'title': note['Title']}
        tooltip(f"Selected Mind Map: {note['Title']}")
        if editor.note:
            editor.note.mindmap_selection = editor.mindmap_selection
        update_mindmap_button(editor, note['Title'])
        if editor.note and editor.note.id:
            link_existing_card_to_mindmap(editor.note, nid, note['Title'])


def update_mindmap_button(editor, mindmap_title):
    """Update the MM button to show the selected mindmap name."""
    display_title = mindmap_title if len(mindmap_title) <= 15 else mindmap_title[:12] + "..."
    safe_display = display_title.replace("'", "\\'").replace('"', '\\"')
    safe_full = mindmap_title.replace("'", "\\'").replace('"', '\\"')

    js_code = UPDATE_BUTTON_JS_TEMPLATE.format(display_title=safe_display, full_title=safe_full)
    try:
        editor.web.eval(js_code)
        logger.info("Button update executed for: %s", mindmap_title)
    except Exception as exc:
        logger.exception("Error updating button: %s", exc)


def add_editor_button(buttons, editor):
    btn = editor.addButton(
        icon=None,
        cmd="mindmap_link",
        func=lambda e=editor: on_editor_btn_click(e),
        tip="Link to Mind Map",
        label="MM",
        id="mindmap_link_btn",
    )
    buttons.append(btn)
    if not hasattr(editor, '_mindmap_btn_added'):
        editor._mindmap_btn_added = True
    return buttons
