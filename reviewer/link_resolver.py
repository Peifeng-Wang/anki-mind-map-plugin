"""Link discovery and validation for mind map review indicators."""
import json
import re

from aqt import mw


MINDMAP_ID_RE = re.compile(r'data-mid="(\d+)"')
NODE_ID_RE = re.compile(r'data-nid="([^"]+)"')


def _find_mindmap_link(note):
    """Return the first mind map link found in a note."""
    for field_name in note.keys():
        field_content = note[field_name]
        if "mindmap-link" not in field_content or "data-mid=" not in field_content:
            continue

        match = MINDMAP_ID_RE.search(field_content)
        if not match:
            continue

        node_match = NODE_ID_RE.search(field_content)
        node_id = node_match.group(1) if node_match else None
        return field_name, int(match.group(1)), node_id

    return None


def _node_exists(node, node_id):
    """Return whether node_id exists in a mind map node tree."""
    nodes_to_check = [node]
    while nodes_to_check:
        current_node = nodes_to_check.pop()
        if not isinstance(current_node, dict):
            continue

        if current_node.get("id") == node_id:
            return True

        children = current_node.get("children", [])
        if isinstance(children, list):
            nodes_to_check.extend(reversed(children))
        else:
            nodes_to_check.extend(reversed(list(children)))

    return False


def _resolve_mindmap_link(mindmap_id, node_id):
    """Return (mindmap_title, should_cleanup_link) for a linked mind map."""
    try:
        mm_note = mw.col.get_note(mindmap_id)
        mindmap_title = mm_note["Title"]
    except Exception:
        # Preserve existing behavior: deleted/unreadable mind maps are not shown.
        return None, False

    try:
        data = json.loads(mm_note["Data"])
        node_exists = False
        if "data" in data:
            node_exists = _node_exists(data["data"], node_id)

        if not node_exists:
            return mindmap_title, True
    except Exception:
        # Preserve existing behavior: title is still shown if only validation fails.
        pass

    return mindmap_title, False
