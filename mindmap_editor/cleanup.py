import json
import logging
import re

from .tree_utils import traverse_nodes, collect_node_info

logger = logging.getLogger(__name__)

_ORPHANED_LINK_RE = re.compile(
    r'<div id="mindmap-link"\s+data-mid="(\d+)"\s+data-nid="([^"]+)"\s+style="display:none;">\s*</div>'
)


def cleanup_orphaned_links(dialog):
    """Remove links from cards that point to non-existent nodes, and remove noteId from nodes whose cards are deleted"""
    try:
        data_str = dialog.note['Data']
        if not data_str:
            return

        data = json.loads(data_str)
        root = data.get('data')
        if not root:
            return

        existing_node_ids, nodes_with_note_ids = collect_node_info(root)
        cleaned_card_count = clean_orphaned_card_links(dialog, existing_node_ids)
        orphaned_node_ids = find_orphaned_node_ids(dialog, nodes_with_note_ids)

        if orphaned_node_ids:
            remove_note_ids_from_nodes(root, orphaned_node_ids)
            deleted_count = delete_orphaned_nodes_from_data(data, root, orphaned_node_ids)
            if deleted_count > 0:
                dialog.note['Data'] = json.dumps(data)
                dialog.mw.col.update_note(dialog.note)
                logger.info(f"Deleted {deleted_count} orphaned nodes, cleaned up {len(orphaned_node_ids)} noteId references")

        if cleaned_card_count > 0 or orphaned_node_ids:
            logger.info(f"Cleanup complete: {cleaned_card_count} card links removed, {len(orphaned_node_ids)} orphaned references found")

    except Exception:
        logger.exception("Error during cleanup")


def clean_orphaned_card_links(dialog, existing_node_ids):
    """Remove mindmap-link divs from cards whose nodes no longer exist."""
    all_notes = dialog.mw.col.find_notes(f'data-mid="{dialog.note_id}"')
    cleaned_card_count = 0
    mindmap_id_str = str(dialog.note_id)

    for nid in all_notes:
        try:
            card_note = dialog.mw.col.get_note(nid)
            modified = False

            for field_name in card_note.keys():
                field_content = card_note[field_name]

                def check_and_remove(match):
                    nonlocal modified
                    mid = match.group(1)
                    node_id = match.group(2)
                    if mid == mindmap_id_str and node_id not in existing_node_ids:
                        modified = True
                        logger.info("Removing orphaned link to node %s from card %s", node_id, nid)
                        return ""
                    return match.group(0)

                new_content = _ORPHANED_LINK_RE.sub(check_and_remove, field_content)
                if new_content != field_content:
                    card_note[field_name] = new_content

            if modified:
                dialog.mw.col.update_note(card_note)
                cleaned_card_count += 1
        except Exception:
            logger.exception("Error cleaning card %s", nid)

    return cleaned_card_count


def find_orphaned_node_ids(dialog, nodes_with_note_ids):
    """Find node IDs whose linked cards no longer exist or no longer link back."""
    orphaned = []
    # Batch check existence with a single SQL query
    note_ids = list(nodes_with_note_ids.values())
    existing_ids = set()
    if note_ids:
        try:
            placeholders = ','.join('?' * len(note_ids))
            existing_ids = set(dialog.mw.col.db.list(
                f"select id from notes where id in ({placeholders})", *note_ids
            ))
        except Exception:
            pass

    for node_id, note_id in nodes_with_note_ids.items():
        if note_id not in existing_ids:
            orphaned.append(node_id)
            continue
        try:
            card_note = dialog.mw.col.get_note(note_id)
            has_link = any(
                f'data-mid="{dialog.note_id}"' in card_note[field_name]
                for field_name in card_note.keys()
            )
            if not has_link:
                orphaned.append(node_id)
        except Exception:
            orphaned.append(node_id)
    return orphaned


def remove_note_ids_from_nodes(root, orphaned_node_ids):
    """Remove noteId from nodes marked as orphaned."""
    def updater(node):
        if node.get('id') in orphaned_node_ids and 'noteId' in node:
            del node['noteId']
            logger.info(f"Removed orphaned noteId from node {node['id']}")
    traverse_nodes(root, updater)


def delete_orphaned_nodes_from_data(data, root, orphaned_node_ids):
    """Delete orphaned nodes from the tree. Returns number of deleted nodes."""
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
                    if isinstance(child, dict) and child.get('id') in orphaned_node_ids:
                        deleted_count += 1
                        logger.info("Deleted orphaned node %s", child.get('id'))
                    else:
                        new_children.append(child)
                if len(new_children) != len(children):
                    node['children'] = new_children

    return deleted_count
