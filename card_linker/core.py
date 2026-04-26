import json
import logging
import uuid

from aqt import mw
from aqt.utils import showInfo, tooltip

from .constants import DATA_NID_RE, LINK_HTML_TEMPLATE, _sync_flags
from .mindmap_ops import find_parent_for_new_node, get_special_boundary_info
from .utils import build_node_index, extract_first_line, find_node_by_id, get_root_node, parse_mindmap_link, select_link_field

from ..core.tree_utils import remove_nodes_by_ids

logger = logging.getLogger(__name__)


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

    def _log(child):
        logger.info("Deleted node %s from mindmap %s", child.get('id'), mindmap_id)

    deleted_count = remove_nodes_by_ids(root, set(node_ids), on_delete=_log)

    if deleted_count > 0:
        mindmap_note['Data'] = json.dumps(data)
        mw.col.update_note(mindmap_note)
        logger.info("Successfully deleted %s nodes from mindmap %s", deleted_count, mindmap_id)
    else:
        logger.info("Nodes %s not found in mindmap %s", node_ids, mindmap_id)


def delete_node_from_mindmap(mindmap_id, node_id):
    """Delete a single node from mindmap when card link is removed."""
    delete_nodes_from_mindmap(mindmap_id, {node_id})


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
