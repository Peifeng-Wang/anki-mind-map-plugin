import json
import logging
import re

from ..core.tree_utils import traverse_nodes, find_node

logger = logging.getLogger(__name__)

_BR_RE = re.compile(r'<br\s*/?>', re.IGNORECASE)
_HTML_TAG_RE = re.compile(r'<[^<]+?>')


def sync_nodes_to_cards(dialog, changed_nodes):
    """Sync changed node content to linked cards"""
    # Import cycle prevention flag
    from .. import card_linker

    for node_info in changed_nodes:
        node_id = node_info.get('id')
        new_topic = node_info.get('topic', '')
        note_id = node_info.get('noteId')

        if not note_id or not new_topic:
            continue

        try:
            with card_linker.node_sync():
                # Get linked card
                card_note = dialog.mw.col.get_note(note_id)

                # Check if card has Front field
                if 'Front' not in card_note:
                    continue

                # Get current front content
                front_content = card_note['Front']

                # Extract first line using pre-compiled regex
                front_text = _BR_RE.sub('\n', front_content)
                clean_text = _HTML_TAG_RE.sub('', front_text)
                lines = clean_text.split('\n')
                first_line = lines[0].strip() if lines else ''

                # Update if first line differs from node content
                if first_line != new_topic:
                    # Replace first line, keep rest
                    # Need to preserve HTML format
                    if _BR_RE.search(front_content):
                        # Has newline
                        parts = _BR_RE.split(front_content, maxsplit=1)
                        if len(parts) > 1:
                            card_note['Front'] = new_topic + '<br>' + parts[1]
                        else:
                            card_note['Front'] = new_topic
                    else:
                        # No newline, replace entire
                        card_note['Front'] = new_topic

                    dialog.mw.col.update_note(card_note)
                    logger.info("Synced mindmap node to card: '%s' -> '%s'", first_line, new_topic)

        except Exception as e:
            logger.exception("Error syncing node %s to card %s", node_id, note_id)


def sync_map_linked_nodes(dialog, changed_nodes):
    """Sync changes from map-linked nodes to their source maps"""
    # Load current map data to check for map link properties
    try:
        data_str = dialog.note['Data']
        current_data = json.loads(data_str)
    except Exception as e:
        logger.exception("Error loading current map data for sync")
        return

    # Build index of nodes with map link properties
    map_link_nodes = {}

    def collect_callback(node):
        if isinstance(node, dict):
            node_id = node.get('id')
            if node.get('isMapLink') and node.get('sourceMapId'):
                map_link_nodes[node_id] = {
                    'sourceMapId': node.get('sourceMapId'),
                    'sourceNodeId': node.get('sourceNodeId', 'root')
                }

    if 'data' in current_data:
        traverse_nodes(current_data['data'], collect_callback)

    # Also check root node for linkedMaps (sync content from root to linked nodes)
    root_node = current_data.get('data', {})
    root_linked_maps = root_node.get('linkedMaps', [])

    for node_info in changed_nodes:
        node_id = node_info.get('id')
        new_topic = node_info.get('topic', '')

        if not node_id or not new_topic:
            continue

        # Case 1: This is a map-linked node - sync to source map's root
        if node_id in map_link_nodes:
            link_info = map_link_nodes[node_id]
            source_map_id = link_info['sourceMapId']
            sync_map_link_content(dialog, node_id, new_topic, source_map_id)

        # Case 2: This is the root node with linkedMaps - sync to all linked nodes
        if node_id == 'root' and root_linked_maps:
            for link in root_linked_maps:
                target_map_id = link.get('targetMapId')
                linked_node_id = link.get('linkedNodeId')
                if target_map_id and linked_node_id:
                    sync_to_linked_node(dialog, target_map_id, linked_node_id, new_topic)


def sync_to_linked_node(dialog, target_map_id, linked_node_id, new_topic):
    """Sync content from root to a linked node in another map"""
    try:
        target_note = dialog.mw.col.get_note(target_map_id)
        target_data_str = target_note['Data']
        target_data = json.loads(target_data_str)

        target_root = target_data.get('data')
        if target_root:
            node = find_node(target_root, linked_node_id)
            if node and node.get('topic') != new_topic:
                node['topic'] = new_topic
                target_note['Data'] = json.dumps(target_data)
                dialog.mw.col.update_note(target_note)
                logger.info("Synced root content to linked node %s in map %s", linked_node_id, target_map_id)

                # Notify open target map window to refresh if exists
                from .main_dialog import MindMapDialog
                MindMapDialog._refresh_editor_if_open(dialog.mw, target_map_id)
    except Exception as e:
        logger.exception("Error syncing to linked node")


def sync_map_link_content(dialog, node_id, new_topic, source_map_id):
    """Sync content changes from a linked node to the source map's root"""
    try:
        source_note = dialog.mw.col.get_note(source_map_id)
        source_data_str = source_note['Data']
        source_data = json.loads(source_data_str)
        source_root = source_data.get('data', {})

        # Update source root topic
        if source_root.get('topic') != new_topic:
            source_root['topic'] = new_topic
            source_note['Data'] = json.dumps(source_data)

            # Also update Title field
            source_note['Title'] = new_topic

            dialog.mw.col.update_note(source_note)
            logger.info(f"Synced linked node content to source map {source_map_id}: '{new_topic}'")

            # Notify open source map window to refresh if exists
            from .main_dialog import MindMapDialog
            MindMapDialog._refresh_editor_if_open(dialog.mw, source_map_id)
    except Exception as e:
        logger.exception("Error syncing map link content")
