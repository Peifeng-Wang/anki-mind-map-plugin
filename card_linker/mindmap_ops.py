import logging

from .utils import find_node_by_id, get_root_node

logger = logging.getLogger(__name__)


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
