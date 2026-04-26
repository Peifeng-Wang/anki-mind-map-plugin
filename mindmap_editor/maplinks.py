import json
import logging
import uuid

from .tree_utils import remove_node

logger = logging.getLogger(__name__)


def handle_get_editable_maps(dialog):
    """Get list of editable mind maps for the selection dialog, including linked status"""
    try:
        maps_list = []
        ids = dialog.mw.col.find_notes('"note:MindMap Master"')

        # Get current linked maps from source root
        linked_map_ids = set()
        try:
            data_str = dialog.note['Data']
            source_data = json.loads(data_str)
            source_root = source_data.get('data', {})
            linked_maps = source_root.get('linkedMaps', [])
            for link in linked_maps:
                linked_map_ids.add(link.get('targetMapId'))
        except Exception as e:
            logger.exception("Error getting linked maps")

        for nid in ids:
            # Skip current map
            if nid == dialog.note_id:
                continue
            note = dialog.mw.col.get_note(nid)
            # Only include active (editable) maps
            try:
                allow_new = note['AllowNewCards']
            except KeyError:
                allow_new = '1'
            if allow_new == '1':
                maps_list.append({
                    'id': nid,
                    'title': note['Title'],
                    'isLinked': nid in linked_map_ids
                })
        # Send list to JavaScript
        js_code = f"if(typeof onEditableMapsReceived === 'function') onEditableMapsReceived({json.dumps(maps_list)});"
        dialog.web.eval(js_code)
    except Exception as e:
        logger.exception("Error getting editable maps")


def handle_create_map_link(dialog, params_json: str):
    """Create a bidirectional link between this map's root and another map"""
    try:
        params = json.loads(params_json)
        target_map_id = params.get('targetMapId')

        if not target_map_id:
            logger.error("No target map ID provided")
            return

        # Load current map data
        data_str = dialog.note['Data']
        source_data = json.loads(data_str)
        source_root = source_data.get('data', {})
        root_topic = source_root.get('topic', 'Linked Node')

        # Generate new node ID for the linked node in target map
        linked_node_id = f"maplink_{uuid.uuid4().hex[:8]}"

        # Load target map
        target_note = dialog.mw.col.get_note(target_map_id)
        target_data_str = target_note['Data']
        target_data = json.loads(target_data_str)
        target_root = target_data.get('data', {})

        # Create linked node in target map (copy style from source root)
        linked_node = {
            "id": linked_node_id,
            "topic": root_topic,
            "direction": "right",
            "expanded": True,
            "isMapLink": True,
            "sourceMapId": dialog.note_id,
            "sourceNodeId": "root"
        }

        # Copy style properties from source root to linked node
        style_props = ['background-color', 'foreground-color', 'width', 'height',
                      'font-size', 'font-weight', 'font-style']
        for prop in style_props:
            if prop in source_root:
                linked_node[prop] = source_root[prop]

        # Add to target root's children
        if 'children' not in target_root:
            target_root['children'] = []
        target_root['children'].append(linked_node)

        # Save target map
        target_note['Data'] = json.dumps(target_data)
        dialog.mw.col.update_note(target_note)

        # Update source root with link info (include title for display)
        if 'linkedMaps' not in source_root:
            source_root['linkedMaps'] = []
        source_root['linkedMaps'].append({
            "targetMapId": target_map_id,
            "targetMapTitle": target_note['Title'],
            "linkedNodeId": linked_node_id
        })

        # Save source map
        dialog.note['Data'] = json.dumps(source_data)
        dialog.mw.col.update_note(dialog.note)

        # Notify JavaScript of success
        dialog.web.eval(f"if(typeof onMapLinkCreated === 'function') onMapLinkCreated({json.dumps(target_map_id)}, {json.dumps(linked_node_id)});")
        dialog.web.eval("if(typeof showToast === 'function') showToast('Link created!');")

        # Refresh source map to show updated link indicator
        dialog._handle_refresh()

        # Refresh target map window if open to show the new linked node
        from .main_dialog import MindMapDialog
        if MindMapDialog._refresh_editor_if_open(dialog.mw, target_map_id):
            logger.info(f"Refreshed target map window {target_map_id}")

        logger.info(f"Created map link: {dialog.note_id} -> {target_map_id} (node: {linked_node_id})")

    except Exception as e:
        logger.exception("Error creating map link")
        import traceback
        traceback.print_exc()
        dialog.web.eval(f"if(typeof showToast === 'function') showToast({json.dumps(f'Error: {e}')});")


def handle_jump_to_map(dialog, params_json: str):
    """Jump to another mind map, optionally focusing on a specific node"""
    try:
        params = json.loads(params_json)
        target_map_id = params.get('targetMapId')
        focus_node_id = params.get('focusNodeId', None)

        if not target_map_id:
            logger.error("No target map ID provided")
            return

        # Use open_instance to open or focus the target map
        from .main_dialog import MindMapDialog
        MindMapDialog.open_instance(dialog.mw, target_map_id, focus_node_id)

    except Exception as e:
        logger.exception("Error jumping to map")


def handle_delete_map_link(dialog, params_json: str):
    """Handle deletion of a map link node - clean up the link in source map"""
    try:
        params = json.loads(params_json)
        source_map_id = params.get('sourceMapId')
        linked_node_id = params.get('linkedNodeId')

        if not source_map_id:
            logger.error("No source map ID provided")
            return

        # Load source map and remove the link reference
        try:
            source_note = dialog.mw.col.get_note(source_map_id)
            source_data_str = source_note['Data']
            source_data = json.loads(source_data_str)
            source_root = source_data.get('data', {})

            # Remove from linkedMaps array
            if 'linkedMaps' in source_root:
                source_root['linkedMaps'] = [
                    link for link in source_root['linkedMaps']
                    if link.get('linkedNodeId') != linked_node_id
                ]
                # Clean up empty array
                if not source_root['linkedMaps']:
                    del source_root['linkedMaps']

            # Save source map
            source_note['Data'] = json.dumps(source_data)
            dialog.mw.col.update_note(source_note)

            logger.info(f"Cleaned up map link in source map {source_map_id}")

            # Notify open source map window to refresh if exists
            from .main_dialog import MindMapDialog
            MindMapDialog._refresh_editor_if_open(dialog.mw, source_map_id)

        except Exception as e:
            logger.warning(f"Source map {source_map_id} no longer exists or error: {e}")

    except Exception as e:
        logger.exception("Error deleting map link")


def handle_unlink_map(dialog, params_json: str):
    """Remove a link from this map's root and delete the linked node in target map"""
    try:
        params = json.loads(params_json)
        target_map_id = params.get('targetMapId')

        if not target_map_id:
            logger.error("No target map ID provided")
            return

        # Load current map data
        data_str = dialog.note['Data']
        source_data = json.loads(data_str)
        source_root = source_data.get('data', {})

        # Find and remove the link to target map
        linked_node_id = None
        if 'linkedMaps' in source_root:
            for link in source_root['linkedMaps']:
                if link.get('targetMapId') == target_map_id:
                    linked_node_id = link.get('linkedNodeId')
                    break

            # Remove from linkedMaps array
            source_root['linkedMaps'] = [
                link for link in source_root['linkedMaps']
                if link.get('targetMapId') != target_map_id
            ]
            if not source_root['linkedMaps']:
                del source_root['linkedMaps']

        # Save source map
        dialog.note['Data'] = json.dumps(source_data)
        dialog.mw.col.update_note(dialog.note)

        # Delete the linked node from target map
        if linked_node_id:
            try:
                target_note = dialog.mw.col.get_note(target_map_id)
                target_data_str = target_note['Data']
                target_data = json.loads(target_data_str)

                target_root = target_data.get('data')
                if target_root:
                    remove_node(target_root, linked_node_id)

                # Save target map
                target_note['Data'] = json.dumps(target_data)
                dialog.mw.col.update_note(target_note)

                logger.info("Removed linked node %s from target map %s", linked_node_id, target_map_id)

                # Refresh target map window if open
                from .main_dialog import MindMapDialog
                MindMapDialog._refresh_editor_if_open(dialog.mw, target_map_id)

            except Exception as e:
                logger.exception("Error removing linked node from target map")

        # Refresh source map
        dialog._handle_refresh()

        dialog.web.eval("if(typeof showToast === 'function') showToast('Link removed');")
        logger.info(f"Unlinked map {target_map_id} from {dialog.note_id}")

    except Exception:
        logger.exception("Error unlinking map")
        import traceback
        traceback.print_exc()
