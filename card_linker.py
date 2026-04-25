import json
import logging
import re
import uuid
from contextlib import contextmanager

from aqt import mw
from aqt.qt import QCursor, QMenu, QTimer
from aqt.utils import showInfo, tooltip

logger = logging.getLogger(__name__)

# --- Module-level compiled regex patterns ---
MINDMAP_LINK_RE = re.compile(
    r'<div\s+id="mindmap-link"\s+data-mid="(\d+)"\s+data-nid="([^"]+)"\s+style="display:none;">\s*</div>',
    re.IGNORECASE,
)
DATA_MID_RE = re.compile(r'data-mid="(\d+)"', re.IGNORECASE)
DATA_NID_RE = re.compile(r'data-nid="([^"]+)"', re.IGNORECASE)
BR_RE = re.compile(r'<br\s*/?>', re.IGNORECASE)
HTML_TAG_RE = re.compile(r'<[^<]+?>')
MINDMAP_LINK_DIV_RE = re.compile(
    r'<div[^>]*id="mindmap-link"[^>]*>.*?</div>\s*',
    re.DOTALL | re.IGNORECASE,
)

# --- JavaScript templates ---
RESET_BUTTON_JS = """
(function() {
    var btn = document.getElementById('mindmap_link_btn');
    if (!btn) {
        var buttons = document.querySelectorAll('button');
        for (var i = 0; i < buttons.length; i++) {
            var text = buttons[i].textContent.trim();
            if (text.includes('📌') || text === 'MM') {
                btn = buttons[i];
                break;
            }
        }
    }
    if (btn) {
        btn.innerHTML = 'MM';
        btn.style.backgroundColor = '';
        btn.style.color = '';
        btn.title = 'Link to Mind Map';
    }
})();
"""

UPDATE_BUTTON_JS_TEMPLATE = """
(function() {{
    var btn = document.getElementById('mindmap_link_btn');
    if (!btn) {{
        var buttons = document.querySelectorAll('button');
        for (var i = 0; i < buttons.length; i++) {{
            var text = buttons[i].textContent.trim();
            if (text === 'MM' || text.includes('📌')) {{
                btn = buttons[i];
                break;
            }}
        }}
    }}
    if (btn) {{
        btn.innerHTML = '📌 {display_title}';
        btn.style.backgroundColor = '#e3f2fd';
        btn.style.color = '#1976d2';
        btn.title = 'Linked to: {full_title}';
    }}
}})();
"""

LINK_HTML_TEMPLATE = """
<div id="mindmap-link"
     data-mid="{mindmap_id}"
     data-nid="{node_id}"
     style="display:none;">
</div>
"""


# --- Synchronization flags ---

class _SyncFlags:
    """Simple container for sync flags with context-manager support."""

    def __init__(self):
        self.syncing_from_card = False
        self.syncing_from_node = False

    @contextmanager
    def card_sync(self):
        self.syncing_from_card = True
        try:
            yield
        finally:
            self.syncing_from_card = False


_sync_flags = _SyncFlags()


# --- Utility functions (P0) ---

def extract_first_line(html_text):
    """Extract the first line of plain text from HTML."""
    if not html_text:
        return ""
    text = BR_RE.sub('\n', html_text)
    text = HTML_TAG_RE.sub('', text)
    return text.split('\n')[0].strip()


def build_node_index(root):
    """Build a flat dict mapping node_id -> node for O(1) lookups."""
    index = {}
    def _build(node):
        if isinstance(node, dict):
            node_id = node.get('id')
            if node_id is not None:
                index[node_id] = node
            for child in node.get('children', []):
                _build(child)
    _build(root)
    return index


def find_node_by_id(root, node_id):
    """Recursively find a node by ID in a mind map tree."""
    if isinstance(root, dict):
        if root.get('id') == node_id:
            return root
        for child in root.get('children', []):
            found = find_node_by_id(child, node_id)
            if found:
                return found
    return None


def parse_mindmap_link(field_content):
    """Parse a mindmap-link div and return (mindmap_id, node_id) or None."""
    match = MINDMAP_LINK_RE.search(field_content)
    if match:
        return int(match.group(1)), match.group(2)
    return None


def select_link_field(note):
    """Select the best field to append a mindmap link to."""
    for candidate in ('Back', 'Back Extra', 'Extra'):
        if candidate in note:
            return candidate
    if len(note.fields) > 1:
        return list(note.keys())[-1]
    return None


def get_root_node(mindmap_data):
    """Return the root node from either a full data dict or a raw node tree."""
    if isinstance(mindmap_data, dict) and 'data' in mindmap_data:
        return mindmap_data['data']
    return mindmap_data


# --- Editor Integration ---

def sync_card_to_mindmap(note):
    """Sync first line from card front to mindmap node when card is updated."""
    if _sync_flags.syncing_from_node:
        return

    mindmap_id = None
    node_id = None
    for field_name in note.keys():
        link = parse_mindmap_link(note[field_name])
        if link:
            mindmap_id, node_id = link
            break

    if not mindmap_id or not node_id:
        return

    if 'Front' not in note:
        return

    first_line = extract_first_line(note['Front'])
    if not first_line:
        return

    try:
        with _sync_flags.card_sync():
            mindmap_note = mw.col.get_note(mindmap_id)
            data = json.loads(mindmap_note['Data'])
            root = get_root_node(data)
            node = find_node_by_id(root, node_id)
            if node:
                old_topic = node.get('topic', '')
                if old_topic != first_line:
                    node['topic'] = first_line
                    mindmap_note['Data'] = json.dumps(data)
                    mw.col.update_note(mindmap_note)
                    logger.info("Synced card to mindmap: '%s' -> '%s'", old_topic, first_line)
    except Exception as exc:
        logger.exception("Error syncing card to mindmap: %s", exc)


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


def remove_link_from_card(note, field_name):
    """Remove mindmap-link div from card field."""
    try:
        field_content = note[field_name]
        new_content = MINDMAP_LINK_DIV_RE.sub('', field_content)
        if new_content != field_content:
            note[field_name] = new_content
            mw.col.update_note(note)
            logger.info("Removed invalid mindmap link from card %s", note.id)
    except Exception as exc:
        logger.exception("Error removing link from card: %s", exc)


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
    ids = mw.col.find_notes('"note:MindMap Master"')
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


# --- get_special_boundary_info refactor (P1) ---

def _extract_boundaries(mindmap_data):
    """Extract the boundaries list from various possible locations."""
    if not isinstance(mindmap_data, dict):
        logger.debug("mindmap_data is not a dict")
        return None

    if 'boundaries' in mindmap_data:
        return mindmap_data['boundaries']

    data_section = mindmap_data.get('data')
    if isinstance(data_section, dict) and 'boundaries' in data_section:
        return data_section['boundaries']

    for key, value in mindmap_data.items():
        if isinstance(value, list) and 'boundary' in key.lower():
            return value

    return None


def _find_special_boundary(boundaries):
    """Return the first special boundary with valid nodeIds, or None."""
    if not isinstance(boundaries, list):
        return None
    for boundary in boundaries:
        if not isinstance(boundary, dict):
            continue
        is_special = boundary.get('isSpecial') or boundary.get('is_special')
        node_ids = boundary.get('nodeIds') or boundary.get('node_ids')
        if is_special and node_ids:
            return boundary
    return None


def _validate_boundary_node_ids(node_ids, root, node_index=None):
    """Return a list of node IDs that actually exist in the mindmap tree."""
    valid = []
    for node_id in node_ids:
        if not isinstance(node_id, str):
            logger.warning("node ID %s is not a string, type: %s", node_id, type(node_id))
            continue
        if node_index is not None:
            found = node_id in node_index
        else:
            found = find_node_by_id(root, node_id) is not None
        if found:
            valid.append(node_id)
        else:
            logger.debug("Node %s NOT FOUND in mindmap", node_id)
    return valid


def get_special_boundary_info(mindmap_data, node_index=None):
    """Find special boundary in mindmap data and return its node IDs."""
    try:
        boundaries = _extract_boundaries(mindmap_data)
        if boundaries is None:
            logger.debug("No boundaries found")
            return None
        if not isinstance(boundaries, list) or not boundaries:
            logger.debug("Boundaries is empty or not a list")
            return None

        special_boundary = _find_special_boundary(boundaries)
        if not special_boundary:
            logger.debug("No special boundaries found")
            return None

        node_ids = special_boundary.get('nodeIds') or special_boundary.get('node_ids', [])
        if not isinstance(node_ids, list):
            logger.debug("nodeIds is not a list")
            return None

        root = get_root_node(mindmap_data)
        valid_ids = _validate_boundary_node_ids(node_ids, root, node_index)
        if not valid_ids:
            logger.warning("None of the special boundary node IDs exist in the mindmap")
            return None

        logger.debug("Returning %s valid node IDs from special boundary", len(valid_ids))
        return valid_ids

    except Exception as exc:
        logger.exception("Error getting special boundary info: %s", exc)
    return None


def find_parent_for_new_node(mindmap_data, special_node_ids=None, node_index=None):
    """Find the appropriate parent node for a new linked card node."""
    root = get_root_node(mindmap_data)
    if not root:
        logger.debug("find_parent_for_new_node: No root node found")
        return None, -1

    if not special_node_ids:
        logger.debug("find_parent_for_new_node: No special_node_ids, using root")
        return root, -1

    for node_id in special_node_ids:
        node = node_index.get(node_id) if node_index else find_node_by_id(root, node_id)
        if node:
            logger.debug("find_parent_for_new_node: Selected node from special boundary: %s", node.get('id'))
            return node, -1
        else:
            logger.debug("WARNING: Node ID %s not found in mindmap", node_id)

    logger.debug("find_parent_for_new_node: No valid nodes in special boundary, using root")
    return root, -1


# --- link_existing_card_to_mindmap refactor (P1) ---

def _update_existing_node(card_note, mindmap_data, existing_node_id, first_line, node_index=None):
    """Update an existing mindmap node with the card's noteId and topic."""
    if node_index is not None:
        node = node_index.get(existing_node_id)
    else:
        root = get_root_node(mindmap_data)
        node = find_node_by_id(root, existing_node_id)
    if node:
        node['noteId'] = card_note.id
        node['topic'] = first_line
        return True
    return False


def _create_new_node_in_mindmap(card_note, mindmap_data, special_node_ids, node_index=None):
    """Create a new node in the mindmap for the card and return its ID."""
    new_node_id = f"node_{uuid.uuid4().hex[:8]}"
    first_line = extract_first_line(card_note.get('Front', ''))
    if not first_line:
        first_line = "Linked Card"

    new_node = {
        "id": new_node_id,
        "topic": first_line,
        "direction": "right",
        "expanded": True,
        "noteId": card_note.id,
    }

    parent, _ = find_parent_for_new_node(mindmap_data, special_node_ids, node_index)
    if not parent:
        parent = get_root_node(mindmap_data)
    if 'children' not in parent:
        parent['children'] = []
    parent['children'].append(new_node)
    return new_node_id


def link_existing_card_to_mindmap(card_note, mindmap_id, mindmap_title):
    """Link an existing card to a mindmap by creating/updating a node with noteId."""
    try:
        first_line = extract_first_line(card_note.get('Front', ''))
        if not first_line:
            first_line = "Linked Card"

        has_existing_link = False
        existing_node_id = None
        for field_name in card_note.keys():
            field_content = card_note[field_name]
            if f'data-mid="{mindmap_id}"' in field_content:
                match = DATA_NID_RE.search(field_content)
                if match:
                    existing_node_id = match.group(1)
                    has_existing_link = True
                break

        mindmap_note = mw.col.get_note(mindmap_id)
        data = json.loads(mindmap_note['Data'])
        root = get_root_node(data)
        node_index = build_node_index(root)
        boundaries = data.get('boundaries', [])
        special_node_ids = get_special_boundary_info(data, node_index)
        logger.debug("link_existing_card_to_mindmap: special_node_ids = %s", special_node_ids)

        if has_existing_link and existing_node_id:
            if _update_existing_node(card_note, data, existing_node_id, first_line, node_index):
                if boundaries:
                    data['boundaries'] = boundaries
                mindmap_note['Data'] = json.dumps(data)
                mw.col.update_note(mindmap_note)
        else:
            new_node_id = _create_new_node_in_mindmap(card_note, data, special_node_ids, node_index)
            if boundaries:
                data['boundaries'] = boundaries
                logger.debug("link_existing_card_to_mindmap: Saving %s boundaries", len(boundaries))
            mindmap_note['Data'] = json.dumps(data)
            mw.col.update_note(mindmap_note)
            logger.info("link_existing_card_to_mindmap: Mindmap saved with new node")

            field_to_update = select_link_field(card_note)
            if field_to_update:
                link_html = LINK_HTML_TEMPLATE.format(mindmap_id=mindmap_id, node_id=new_node_id)
                card_note[field_to_update] += link_html
                mw.col.update_note(card_note)

        tooltip(f"Linked existing card to '{mindmap_title}'")

    except Exception as exc:
        logger.exception("Error linking card to mindmap: %s", exc)
        showInfo(f"Error linking card to mindmap: {exc}")


def delete_nodes_from_mindmap(mindmap_id, node_ids):
    """Delete one or more nodes from a mindmap in a single update."""
    if not node_ids:
        return
    try:
        mindmap_note = mw.col.get_note(mindmap_id)
    except Exception as exc:
        logger.warning("Mindmap %s not found, skipping node deletion: %s", mindmap_id, exc)
        return

    data = json.loads(mindmap_note['Data'])
    root = get_root_node(data)
    deleted_count = 0

    # Iterative bottom-up rebuild of children lists
    stack = [(root, False)]
    while stack:
        node, visited = stack.pop()
        if not isinstance(node, dict):
            continue
        if not visited:
            stack.append((node, True))
            for child in node.get('children', []):
                stack.append((child, False))
        else:
            children = node.get('children', [])
            if children:
                new_children = []
                for child in children:
                    if isinstance(child, dict) and child.get('id') in node_ids:
                        deleted_count += 1
                        logger.info("Deleted node %s from mindmap %s", child.get('id'), mindmap_id)
                    else:
                        new_children.append(child)
                if len(new_children) != len(children):
                    node['children'] = new_children

    if deleted_count > 0:
        mindmap_note['Data'] = json.dumps(data)
        mw.col.update_note(mindmap_note)
        logger.info("Successfully deleted %s nodes from mindmap %s", deleted_count, mindmap_id)
    else:
        logger.info("Nodes %s not found in mindmap %s", node_ids, mindmap_id)


def delete_node_from_mindmap(mindmap_id, node_id):
    """Delete a single node from mindmap when card link is removed."""
    delete_nodes_from_mindmap(mindmap_id, {node_id})


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


# --- Note Creation Hook ---

def on_note_added(note):
    if not hasattr(note, 'mindmap_selection') or not note.mindmap_selection:
        return

    mindmap_id = note.mindmap_selection['id']
    first_line = extract_first_line(note.get('Front', ''))
    if not first_line:
        first_line = "New Card"

    try:
        mindmap_note = mw.col.get_note(mindmap_id)
        data = json.loads(mindmap_note['Data'])
        root = get_root_node(data)
        node_index = build_node_index(root)
        boundaries = data.get('boundaries', [])
        special_node_ids = get_special_boundary_info(data, node_index)

        new_node_id = f"node_{uuid.uuid4().hex[:8]}"
        new_node = {
            "id": new_node_id,
            "topic": first_line,
            "direction": "right",
            "expanded": True,
            "noteId": note.id,
        }

        parent, _ = find_parent_for_new_node(data, special_node_ids, node_index)
        if not parent:
            parent = root
        if 'children' not in parent:
            parent['children'] = []
        parent['children'].append(new_node)

        if boundaries:
            data['boundaries'] = boundaries
            logger.debug("on_note_added: Saving %s boundaries with mindmap", len(boundaries))

        mindmap_note['Data'] = json.dumps(data)
        mw.col.update_note(mindmap_note)
        logger.info("on_note_added: Mindmap saved with new node")

        field_to_update = select_link_field(note)
        if field_to_update:
            link_html = LINK_HTML_TEMPLATE.format(mindmap_id=mindmap_id, node_id=new_node_id)
            note[field_to_update] += link_html
            mw.col.update_note(note)

        tooltip(f"Added node '{first_line}' to Mind Map")

    except Exception as exc:
        logger.exception("Error linking to mind map: %s", exc)
        showInfo(f"Error linking to mind map: {exc}")


# --- Validation & Cleanup ---

def validate_and_cleanup_mindmap(mindmap_note):
    """Validate and cleanup nodes in mindmap - remove noteId if card doesn't exist."""
    try:
        data = json.loads(mindmap_note['Data'])
        root = get_root_node(data)

        # Collect all noteIds in one pass
        note_ids = []
        def collect(node):
            if isinstance(node, dict):
                nid = node.get('noteId')
                if nid is not None:
                    note_ids.append(nid)
                for child in node.get('children', []):
                    collect(child)
        collect(root)

        # Batch check existence with a single SQL query
        existing_ids = set()
        if note_ids:
            placeholders = ','.join('?' * len(note_ids))
            existing_ids = set(mw.col.db.list(
                f"select id from notes where id in ({placeholders})", *note_ids
            ))

        # Remove orphaned noteIds
        modified = False
        removed_count = 0
        def cleanup(node):
            nonlocal modified, removed_count
            if isinstance(node, dict):
                nid = node.get('noteId')
                if nid is not None and nid not in existing_ids:
                    logger.info("Card %s no longer exists, removing noteId from node %s", nid, node.get('id'))
                    del node['noteId']
                    modified = True
                    removed_count += 1
                for child in node.get('children', []):
                    cleanup(child)
        cleanup(root)

        if modified:
            mindmap_note['Data'] = json.dumps(data)
            mw.col.update_note(mindmap_note)
            logger.info("Cleaned up mindmap %s: removed %s invalid noteId references", mindmap_note.id, removed_count)

        try:
            from .cross_link_manager import CrossLinkManager
            removed_cross, removed_back = CrossLinkManager.validate_links(mindmap_note.id)
            if removed_cross > 0 or removed_back > 0:
                logger.info("Cleaned up %s invalid cross-links and %s invalid back-links", removed_cross, removed_back)
        except ImportError as exc:
            logger.debug("CrossLinkManager not available: %s", exc)
        except Exception as exc:
            logger.exception("Error validating cross-links: %s", exc)

    except Exception as exc:
        logger.exception("Error validating mindmap: %s", exc)


def on_notes_will_be_deleted(col, ids):
    # First pass: collect all links grouped by mindmap_id
    deletions = {}  # mindmap_id -> set(node_ids)
    for nid in ids:
        try:
            note = col.get_note(nid)
            for field_name in note.keys():
                field_content = note[field_name]
                if 'mindmap-link' in field_content and 'data-mid=' in field_content:
                    link = parse_mindmap_link(field_content)
                    if link:
                        mindmap_id, node_id = link
                        deletions.setdefault(mindmap_id, set()).add(node_id)
                    break
        except Exception as exc:
            logger.exception("Error processing note %s during deletion: %s", nid, exc)

    # Second pass: batch delete from each mindmap
    for mindmap_id, node_ids in deletions.items():
        delete_nodes_from_mindmap(mindmap_id, node_ids)


# --- Initialization ---

def init_card_linker():
    from aqt import gui_hooks
    from anki import hooks
    gui_hooks.editor_did_init_buttons.append(add_editor_button)
    gui_hooks.editor_did_load_note.append(on_editor_load_note)
    gui_hooks.add_cards_did_add_note.append(on_note_added)
    hooks.note_will_flush.append(sync_card_to_mindmap)
    hooks.notes_will_be_deleted.append(on_notes_will_be_deleted)
