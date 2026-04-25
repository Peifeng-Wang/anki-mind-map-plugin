from .note_utils import load_note_data, save_note_data


def cleanup_linked_nodes_on_delete(mw, source_map_id):
    """Remove linked nodes in other maps that point to this map"""
    try:
        source_note = mw.col.get_note(source_map_id)
        source_data = load_note_data(source_note)
        linked_maps = get_linked_maps(source_data)

        for link in linked_maps:
            target_map_id = link.get('targetMapId')
            linked_node_id = link.get('linkedNodeId')

            if not target_map_id or not linked_node_id:
                continue

            try:
                target_note, target_data = load_target_map(mw, target_map_id)
                remove_linked_node(target_data, linked_node_id)

                save_note_data(target_note, target_data)
                mw.col.update_note(target_note)

                print(f"Removed linked node {linked_node_id} from map {target_map_id}")
                refresh_editor_if_open(mw, target_map_id)

            except Exception as e:
                print(f"Error cleaning up linked node in map {target_map_id}: {e}")

    except Exception as e:
        print(f"Error during cleanup on delete: {e}")


def get_linked_maps(map_data):
    source_root = map_data.get('data', {})
    return source_root.get('linkedMaps', [])


def load_target_map(mw, target_map_id):
    target_note = mw.col.get_note(target_map_id)
    return target_note, load_note_data(target_note)


def remove_linked_node(map_data, linked_node_id):
    if 'data' in map_data:
        remove_node_by_id(map_data['data'], linked_node_id)


def remove_node_by_id(node, node_id, parent_children_list=None, index=None):
    if not isinstance(node, dict):
        return False

    if node.get('id') == node_id:
        if parent_children_list is not None and index is not None:
            parent_children_list.pop(index)
            return True

    if 'children' in node:
        for child_index, child in enumerate(node['children']):
            if remove_node_by_id(child, node_id, node['children'], child_index):
                return True

    return False


def refresh_editor_if_open(mw, target_map_id):
    if hasattr(mw, 'mindmap_editors'):
        for editor in mw.mindmap_editors:
            if editor.note_id == target_map_id:
                editor._handle_refresh()
                break
