import logging

logger = logging.getLogger(__name__)


def traverse_nodes(node, callback):
    """Recursively traverse all nodes and apply callback."""
    if not isinstance(node, dict):
        return
    callback(node)
    for child in node.get('children', []):
        traverse_nodes(child, callback)


def find_node(root, node_id):
    """Recursively find a node by id. Returns the node or None."""
    if not isinstance(root, dict):
        return None
    if root.get('id') == node_id:
        return root
    for child in root.get('children', []):
        found = find_node(child, node_id)
        if found:
            return found
    return None


def remove_node(root, node_id):
    """Recursively remove a node by id. Returns True if removed."""
    if not isinstance(root, dict):
        return False
    children = root.get('children', [])
    for i, child in enumerate(list(children)):
        if isinstance(child, dict) and child.get('id') == node_id:
            children.pop(i)
            return True
        if remove_node(child, node_id):
            return True
    return False


def update_node(root, node_id, updater):
    """Recursively find a node and apply updater(dict) to it. Returns True if updated."""
    node = find_node(root, node_id)
    if node:
        updater(node)
        return True
    return False


def collect_node_info(root):
    """Collect all node ids and noteId mappings from the tree."""
    existing_node_ids = set()
    nodes_with_note_ids = {}

    def callback(node):
        if 'id' in node:
            existing_node_ids.add(node['id'])
            if 'noteId' in node:
                nodes_with_note_ids[node['id']] = node['noteId']

    traverse_nodes(root, callback)
    return existing_node_ids, nodes_with_note_ids


def remove_nodes_by_ids(root, node_ids, on_delete=None):
    """Iteratively rebuild children lists, removing nodes whose id is in node_ids.

    Returns the number of nodes deleted. Optional on_delete(child) is called
    for each removed node.
    """
    if not isinstance(root, dict) or not node_ids:
        return 0

    deleted_count = 0
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
                        if on_delete is not None:
                            on_delete(child)
                    else:
                        new_children.append(child)
                if len(new_children) != len(children):
                    node['children'] = new_children
    return deleted_count
