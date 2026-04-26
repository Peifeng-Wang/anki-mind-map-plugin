import logging

from aqt import mw

from .constants import MINDMAP_LINK_DIV_RE
from .utils import parse_mindmap_link

from ..mindmap_editor.tree_utils import traverse_nodes

logger = logging.getLogger(__name__)


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


def validate_and_cleanup_mindmap(mindmap_note):
    """Validate and cleanup nodes in mindmap - remove noteId if card doesn't exist."""
    try:
        import json
        from .utils import get_root_node

        data = json.loads(mindmap_note['Data'])
        root = get_root_node(data)

        # Collect all noteIds in one pass
        note_ids = []
        def collect(node):
            nid = node.get('noteId')
            if nid is not None:
                note_ids.append(nid)
        traverse_nodes(root, collect)

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
            nid = node.get('noteId')
            if nid is not None and nid not in existing_ids:
                logger.info("Card %s no longer exists, removing noteId from node %s", nid, node.get('id'))
                del node['noteId']
                modified = True
                removed_count += 1
        traverse_nodes(root, cleanup)

        if modified:
            mindmap_note['Data'] = json.dumps(data)
            mw.col.update_note(mindmap_note)
            logger.info("Cleaned up mindmap %s: removed %s invalid noteId references", mindmap_note.id, removed_count)

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
    from .core import delete_nodes_from_mindmap
    for mindmap_id, node_ids in deletions.items():
        delete_nodes_from_mindmap(mindmap_id, node_ids)
