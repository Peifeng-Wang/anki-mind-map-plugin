import json
import re
from aqt import mw
from aqt.qt import *
from aqt import gui_hooks
from aqt.utils import showInfo, tooltip

# Flags to prevent sync loop
_syncing_from_card = False
_syncing_from_node = False

# --- Editor Integration ---

def sync_card_to_mindmap(note):
    """Sync first line from card front to mindmap node when card is updated"""
    global _syncing_from_card, _syncing_from_node
    
    # Prevent sync loop
    if _syncing_from_node:
        return
    
    # Check if note has mind map link
    mindmap_id = None
    node_id = None
    
    for field_name in note.keys():
        field_content = note[field_name]
        # Find mindmap-link div
        pattern = r'<div id="mindmap-link"\s+data-mid="(\d+)"\s+data-nid="([^"]+)"\s+style="display:none;">\s*</div>'
        match = re.search(pattern, field_content)
        if match:
            mindmap_id = int(match.group(1))
            node_id = match.group(2)
            break
    
    if not mindmap_id or not node_id:
        return  # No link, no need to sync
    
    # Get first line of card front
    if 'Front' not in note:
        return
    
    front_text = note['Front']
    # Process HTML
    front_text = re.sub(r'<br\s*/?>', '\n', front_text, flags=re.IGNORECASE)
    clean_text = re.sub('<[^<]+?>', '', front_text)
    first_line = clean_text.split('\n')[0].strip()
    
    if not first_line:
        return
    
    # Update mind map
    try:
        _syncing_from_card = True
        
        mm_note = mw.col.get_note(mindmap_id)
        data_str = mm_note['Data']
        data = json.loads(data_str)
        
        # Recursively find and update node
        def update_node(node):
            if isinstance(node, dict):
                if node.get('id') == node_id:
                    old_topic = node.get('topic', '')
                    if old_topic != first_line:
                        node['topic'] = first_line
                        print(f"Synced card to mindmap: '{old_topic}' -> '{first_line}'")
                        return True
                if 'children' in node:
                    for child in node['children']:
                        if update_node(child):
                            return True
            return False
        
        if 'data' in data:
            if update_node(data['data']):
                mm_note['Data'] = json.dumps(data)
                mw.col.update_note(mm_note)
                
    except Exception as e:
        print(f"Error syncing card to mindmap: {e}")
    finally:
        _syncing_from_card = False

def on_editor_load_note(editor):
    """Check mindmap association and update button when editor loads a note"""
    
    # Check if card already has linked mind map (for existing cards)
    if editor.note and editor.note.id:
        # Existing card - always read actual link state from card data
        # Don't use editor.mindmap_selection to avoid showing wrong association in browser
        try:
            # Find mindmap-link div in all fields
            for field_name in editor.note.keys():
                field_content = editor.note[field_name]
                if 'mindmap-link' in field_content and 'data-mid=' in field_content:
                    # Extract mind map ID and node ID
                    match_mid = re.search(r'data-mid="(\d+)"', field_content)
                    match_nid = re.search(r'data-nid="([^"]+)"', field_content)
                    
                    if match_mid and match_nid:
                        mindmap_id = int(match_mid.group(1))
                        node_id = match_nid.group(1)
                        
                        # Validate: Check if mindmap still exists
                        try:
                            mm_note = mw.col.get_note(mindmap_id)
                            mindmap_title = mm_note['Title']
                            
                            # Validate: Check if node still exists in mindmap
                            data_str = mm_note['Data']
                            data = json.loads(data_str)
                            
                            node_exists = False
                            def check_node_exists(node):
                                nonlocal node_exists
                                if isinstance(node, dict):
                                    if node.get('id') == node_id:
                                        node_exists = True
                                        return
                                    if 'children' in node:
                                        for child in node['children']:
                                            check_node_exists(child)
                            
                            if 'data' in data:
                                check_node_exists(data['data'])
                            
                            if not node_exists:
                                # Node was deleted from mindmap, cleanup card link
                                print(f"Node {node_id} no longer exists in mindmap {mindmap_id}, cleaning up card link")
                                remove_link_from_card(editor.note, field_name)
                                reset_mindmap_button(editor)
                                return
                            
                            # Link is valid, show it
                            editor.mindmap_selection = {
                                'id': mindmap_id,
                                'title': mindmap_title
                            }
                            editor.note.mindmap_selection = editor.mindmap_selection
                            
                            # Delay button update to ensure button is rendered
                            from aqt.qt import QTimer
                            QTimer.singleShot(300, lambda: update_mindmap_button(editor, mindmap_title))
                            
                            print(f"Loaded existing mindmap link: {mindmap_title}")
                            return
                            
                        except Exception as e:
                            # Mindmap was deleted, cleanup card link
                            print(f"Mindmap {mindmap_id} no longer exists, cleaning up card link: {e}")
                            remove_link_from_card(editor.note, field_name)
                            reset_mindmap_button(editor)
                            return
                    break
            
            # If no association found, clear any leftover selection state in editor
            if hasattr(editor, 'mindmap_selection'):
                delattr(editor, 'mindmap_selection')
            if hasattr(editor.note, 'mindmap_selection'):
                delattr(editor.note, 'mindmap_selection')
            # Reset button display
            reset_mindmap_button(editor)
            
        except Exception as e:
            print(f"Error checking for existing mindmap link: {e}")
    else:
        # New card (no ID) - can keep editor's selection state for batch adding
        if hasattr(editor, 'mindmap_selection') and editor.mindmap_selection:
            if editor.note:
                editor.note.mindmap_selection = editor.mindmap_selection
                print(f"Preserved mindmap selection for new note: {editor.mindmap_selection['title']}")
                # Update button display
                from aqt.qt import QTimer
                QTimer.singleShot(300, lambda: update_mindmap_button(editor, editor.mindmap_selection['title']))
                return

def remove_link_from_card(note, field_name):
    """Remove mindmap-link div from card field"""
    try:
        field_content = note[field_name]
        new_content = re.sub(
            r'<div[^>]*id="mindmap-link"[^>]*>.*?</div>\s*',
            '',
            field_content,
            flags=re.DOTALL | re.IGNORECASE
        )
        if new_content != field_content:
            note[field_name] = new_content
            mw.col.update_note(note)
            print(f"Removed invalid mindmap link from card {note.id}")
    except Exception as e:
        print(f"Error removing link from card: {e}")


def clear_mindmap_selection(editor):
    """Clear mindmap selection from editor and remove association link from card"""
    # Clear editor properties
    if hasattr(editor, 'mindmap_selection'):
        delattr(editor, 'mindmap_selection')
    
    # Clear note properties
    if editor.note and hasattr(editor.note, 'mindmap_selection'):
        delattr(editor.note, 'mindmap_selection')
    
    # Remove mindmap-link div from all card fields AND delete corresponding node in mindmap
    if editor.note and editor.note.id:
        try:
            modified = False
            mindmap_id = None
            node_id = None
            
            # First, find the mindmap and node ID before removing the link
            for field_name in editor.note.keys():
                field_content = editor.note[field_name]
                if 'mindmap-link' in field_content:
                    # Extract mindmap ID and node ID
                    pattern = r'<div id="mindmap-link"\s+data-mid="(\d+)"\s+data-nid="([^"]+)"\s+style="display:none;">\s*</div>'
                    match = re.search(pattern, field_content)
                    if match:
                        mindmap_id = int(match.group(1))
                        node_id = match.group(2)
                        break
            
            # Remove mindmap-link div from all fields
            for field_name in editor.note.keys():
                field_content = editor.note[field_name]
                if 'mindmap-link' in field_content:
                    # Remove mindmap-link div
                    new_content = re.sub(
                        r'<div[^>]*id="mindmap-link"[^>]*>.*?</div>\s*',
                        '',
                        field_content,
                        flags=re.DOTALL | re.IGNORECASE
                    )
                    if new_content != field_content:
                        editor.note[field_name] = new_content
                        modified = True
            
            # Delete the corresponding node in mindmap if we found the IDs
            if mindmap_id and node_id:
                delete_node_from_mindmap(mindmap_id, node_id)
            
            # Update note if modified
            if modified:
                mw.col.update_note(editor.note)
                print("Removed mindmap link from card")
                from aqt.utils import tooltip
                tooltip("Removed mindmap link from card")
        except Exception as e:
            print(f"Error removing mindmap link: {e}")
    
    # Reset button display
    reset_mindmap_button(editor)

def reset_mindmap_button(editor):
    """Reset mindmap button to default state"""
    js_code = """
    (function() {
        var btn = document.getElementById('mindmap_link_btn');
        if (!btn) {
            // Fallback: find by button text
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
    try:
        editor.web.eval(js_code)
    except Exception as e:
        print(f"Error resetting button: {e}")

def on_editor_btn_click(editor):
    # Get all mind maps
    ids = mw.col.find_notes('"note:MindMap Master"')
    if not ids:
        tooltip("No Mind Maps found. Create one first from Tools > Mind Map > Mind Map Manager")
        return
    
    # Create menu
    menu = QMenu(editor.parentWindow)
    menu.setTitle("Select Mind Map")
    
    # Add "No Association" option
    clear_action = menu.addAction("❌")
    clear_action.setData(None)  # Use None to identify clear operation
    menu.addSeparator()  # Add separator line
    
    # Filter and add only active mind maps
    active_count = 0
    for nid in ids:
        note = mw.col.get_note(nid)
        # Check if this mind map allows new cards (default to "1" if field doesn't exist)
        try:
            allow_new = note['AllowNewCards']
        except KeyError:
            allow_new = '1'  # Default to active if field doesn't exist
        
        if allow_new == "1":  # Only show active mind maps
            title = note['Title']
            action = menu.addAction(title)
            action.setData(nid)  # Store note ID in action
            active_count += 1
    
    if active_count == 0:
        # No active mind maps, show info
        info_action = menu.addAction("(No active mind maps)")
        info_action.setEnabled(False)
    
    # Show menu at button position (or cursor)
    # Get cursor position as fallback
    cursor_pos = QCursor.pos()
    action = menu.exec(cursor_pos)
    
    if action:
        nid = action.data()
        
        if nid is None:  # User selected "No Association"
            clear_mindmap_selection(editor)
            tooltip("Removed mindmap link from card")
        else:  # User selected a mind map
            note = mw.col.get_note(nid)
            editor.mindmap_selection = {
                'id': nid,
                'title': note['Title']
            }
            tooltip(f"Selected Mind Map: {note['Title']}")
            # Store on the note object so we can access it in note_added
            editor.note.mindmap_selection = editor.mindmap_selection
            
            # Update button text to show selected mindmap
            update_mindmap_button(editor, note['Title'])
            
            # If this is an existing card (has ID), link it immediately
            if editor.note.id:
                link_existing_card_to_mindmap(editor.note, nid, note['Title'])

def update_mindmap_button(editor, mindmap_title):
    """Update the MM button to show the selected mindmap name"""
    # Truncate long titles
    display_title = mindmap_title if len(mindmap_title) <= 15 else mindmap_title[:12] + "..."
    
    # Escape quotes in title for JavaScript
    safe_display = display_title.replace("'", "\\'").replace('"', '\\"')
    safe_full = mindmap_title.replace("'", "\\'").replace('"', '\\"')
    
    # Update button text via JavaScript using the button ID
    js_code = f"""
    (function() {{
        console.log('Looking for mindmap button...');
        // Try multiple selectors to find the button
        var btn = document.getElementById('mindmap_link_btn');
        if (!btn) {{
            console.log('Button not found by ID, searching by text...');
            // Fallback: find by button text
            var buttons = document.querySelectorAll('button');
            console.log('Found ' + buttons.length + ' buttons total');
            for (var i = 0; i < buttons.length; i++) {{
                var text = buttons[i].textContent.trim();
                console.log('Button ' + i + ': ' + text);
                if (text === 'MM' || text.includes('📌')) {{
                    btn = buttons[i];
                    console.log('Found mindmap button at index ' + i);
                    break;
                }}
            }}
        }}
        
        if (btn) {{
            console.log('Updating button text to: 📌 {safe_display}');
            btn.innerHTML = '📌 {safe_display}';
            btn.style.backgroundColor = '#e3f2fd';
            btn.style.color = '#1976d2';
            btn.title = 'Linked to: {safe_full}';
        }} else {{
            console.log('ERROR: Mindmap button not found!');
        }}
    }})();
    """
    try:
        editor.web.eval(js_code)
        print(f"Button update JavaScript executed for: {mindmap_title}")
    except Exception as e:
        print(f"Error updating button: {e}")
        # Fallback: just show tooltip
        pass

def get_special_boundary_info(mindmap_data):
    """Find special boundary in mindmap data and return its node IDs"""
    try:
        # Check if mindmap_data is a dictionary
        if not isinstance(mindmap_data, dict):
            print("get_special_boundary_info: mindmap_data is not a dict")
            return None
        
        # Debug: print the structure of mindmap_data
        print("=== get_special_boundary_info: Analyzing mindmap_data structure ===")
        print(f"Top-level keys: {list(mindmap_data.keys())}")
        
        boundaries = None
        
        # Try to get boundaries from different possible locations
        # First, check if boundaries is directly in mindmap_data
        if 'boundaries' in mindmap_data:
            boundaries = mindmap_data['boundaries']
            print(f"Found boundaries in mindmap_data['boundaries']: {len(boundaries) if isinstance(boundaries, list) else 'not a list'}")
        # If not found, check inside 'data' key
        elif 'data' in mindmap_data and isinstance(mindmap_data['data'], dict):
            if 'boundaries' in mindmap_data['data']:
                boundaries = mindmap_data['data']['boundaries']
                print(f"Found boundaries in mindmap_data['data']['boundaries']: {len(boundaries) if isinstance(boundaries, list) else 'not a list'}")
            else:
                print("No 'boundaries' key found in mindmap_data['data']")
                # Check what's actually in 'data'
                print(f"Keys in mindmap_data['data']: {list(mindmap_data['data'].keys()) if isinstance(mindmap_data['data'], dict) else 'not a dict'}")
        else:
            print("mindmap_data structure not recognized")
            # Try to find boundaries by scanning all values
            for key, value in mindmap_data.items():
                if isinstance(value, list) and key.lower().find('boundary') != -1:
                    boundaries = value
                    print(f"Found boundaries in key '{key}': {len(value)} items")
                    break
        
        if boundaries is None:
            print("No boundaries found at all")
            return None
        
        if not isinstance(boundaries, list):
            print(f"Boundaries is not a list, type: {type(boundaries)}")
            return None
        
        if len(boundaries) == 0:
            print("boundaries list is empty")
            return None
        
        print(f"Total boundaries found: {len(boundaries)}")
        
        # Find special boundary
        special_boundaries = []
        for i, boundary in enumerate(boundaries):
            # Check if boundary is a dictionary
            if not isinstance(boundary, dict):
                print(f"Boundary {i} is not a dict, type: {type(boundary)}")
                continue
                
            # Check if boundary is special and has nodeIds
            is_special = boundary.get('isSpecial', False)
            # Also check for is_special with different capitalization
            if not is_special:
                is_special = boundary.get('is_special', False)
            
            has_nodeIds = 'nodeIds' in boundary and boundary['nodeIds']
            # Also check for node_ids with different capitalization
            if not has_nodeIds and 'node_ids' in boundary and boundary['node_ids']:
                has_nodeIds = True
                boundary['nodeIds'] = boundary['node_ids']
            
            color = boundary.get('color', '')
            node_ids = boundary.get('nodeIds', [])
            
            print(f"Boundary {i}: isSpecial={is_special}, has_nodeIds={has_nodeIds}, "
                  f"nodeIds count={len(node_ids) if isinstance(node_ids, list) else 'not list'}, "
                  f"color={color[:50] if color else 'none'}")
            
            if is_special and has_nodeIds:
                special_boundaries.append(boundary)
                print(f"  -> This is a SPECIAL boundary!")
        
        if not special_boundaries:
            print("No special boundaries found")
            return None
        
        print(f"Found {len(special_boundaries)} special boundaries")
        
        # Use the first special boundary
        special_boundary = special_boundaries[0]
        node_ids = special_boundary.get('nodeIds', [])
        
        if not isinstance(node_ids, list):
            print(f"nodeIds is not a list, type: {type(node_ids)}")
            return None
        
        print(f"Found special boundary with {len(node_ids)} node IDs: {node_ids[:10]}{'...' if len(node_ids) > 10 else ''}")
        
        # Validate that node IDs are strings
        valid_node_ids = []
        for node_id in node_ids:
            if isinstance(node_id, str):
                valid_node_ids.append(node_id)
            else:
                print(f"Warning: node ID {node_id} is not a string, type: {type(node_id)}")
        
        if not valid_node_ids:
            print("No valid string node IDs found in special boundary")
            return None
        
        # Additional debug: check if these node IDs exist in the mindmap
        print("=== Validating special boundary node IDs in mindmap ===")
        # Function to find node by ID
        def find_node_by_id(node, target_id):
            if isinstance(node, dict):
                if node.get('id') == target_id:
                    return node
                if 'children' in node:
                    for child in node['children']:
                        found = find_node_by_id(child, target_id)
                        if found:
                            return found
            return None
        
        # Get root node
        root = None
        if 'data' in mindmap_data:
            root = mindmap_data['data']
        else:
            root = mindmap_data
        
        existing_node_ids = []
        for node_id in valid_node_ids:
            node = find_node_by_id(root, node_id)
            if node:
                existing_node_ids.append(node_id)
                print(f"  ✓ Node {node_id} exists in mindmap: '{node.get('topic', '')[:50]}'")
            else:
                print(f"  ✗ Node {node_id} NOT FOUND in mindmap")
        
        if not existing_node_ids:
            print("WARNING: None of the special boundary node IDs exist in the mindmap!")
            return None
        
        print(f"Returning {len(existing_node_ids)} valid node IDs from special boundary")
        return existing_node_ids
        
    except Exception as e:
        print(f"Error getting special boundary info: {e}")
        import traceback
        traceback.print_exc()
    return None

def find_parent_for_new_node(mindmap_data, special_node_ids=None):
    """Find the appropriate parent node for new linked card node.
    If special boundary exists, use the first node in boundary as parent.
    Otherwise return root node."""
    
    def find_node_by_id(node, node_id):
        """Recursively find node by ID"""
        if isinstance(node, dict):
            if node.get('id') == node_id:
                return node
            if 'children' in node:
                for child in node['children']:
                    found = find_node_by_id(child, node_id)
                    if found:
                        return found
        return None
    
    # Get root node from mindmap_data
    if isinstance(mindmap_data, dict) and 'data' in mindmap_data:
        # Full mindmap data structure
        root = mindmap_data.get('data')
        full_data = mindmap_data
    else:
        # Just the node tree
        root = mindmap_data
        full_data = {'data': mindmap_data} if mindmap_data else {}
    
    if not root:
        print("find_parent_for_new_node: No root node found")
        return root, -1
    
    # If no special boundary or no node IDs, return root
    if not special_node_ids or len(special_node_ids) == 0:
        print("find_parent_for_new_node: No special_node_ids, using root")
        return root, -1
    
    print(f"find_parent_for_new_node: Processing {len(special_node_ids)} special node IDs")
    print(f"Special node IDs: {special_node_ids[:10]}{'...' if len(special_node_ids) > 10 else ''}")
    
    # Find the first valid node in special boundary
    for node_id in special_node_ids:
        node = find_node_by_id(root, node_id)
        if node:
            print(f"find_parent_for_new_node: Selected first valid node from special boundary: {node.get('id')}")
            print(f"  Node topic: '{node.get('topic', '')[:50]}'")
            # Return this node as parent
            return node, -1
        else:
            print(f"  WARNING: Node ID {node_id} not found in mindmap!")
    
    # If no valid nodes found in special boundary, use root
    print("find_parent_for_new_node: No valid nodes found in special boundary, using root")
    return root, -1

def link_existing_card_to_mindmap(card_note, mindmap_id, mindmap_title):
    """Link an existing card to a mindmap by creating/updating a node with noteId"""
    try:
        # Get first line from card's Front field
        if 'Front' in card_note:
            front_text = card_note['Front']
            front_text = re.sub(r'<br\s*/?>', '\n', front_text, flags=re.IGNORECASE)
            clean_text = re.sub('<[^<]+?>', '', front_text)
            first_line = clean_text.split('\n')[0].strip()
            if not first_line:
                first_line = "Linked Card"
        else:
            first_line = "Linked Card"
        
        # Check if card already has a link to this mindmap
        has_existing_link = False
        existing_node_id = None
        for field_name in card_note.keys():
            field_content = card_note[field_name]
            if f'data-mid="{mindmap_id}"' in field_content:
                # Extract node ID from existing link
                match = re.search(r'data-nid="([^"]+)"', field_content)
                if match:
                    existing_node_id = match.group(1)
                    has_existing_link = True
                break
        
        # Load mindmap data
        mm_note = mw.col.get_note(mindmap_id)
        data_str = mm_note['Data']
        data = json.loads(data_str)
        
        # Preserve boundaries if they exist in the data
        boundaries = data.get('boundaries', [])
        
        # Check for special boundary
        special_node_ids = get_special_boundary_info(data)
        print(f"on_note_added: special_node_ids = {special_node_ids}")
        
        if has_existing_link and existing_node_id:
            # Update existing node to add noteId
            def update_node_with_noteid(node):
                if isinstance(node, dict):
                    if node.get('id') == existing_node_id:
                        node['noteId'] = card_note.id
                        node['topic'] = first_line  # Also update topic
                        return True
                    if 'children' in node:
                        for child in node['children']:
                            if update_node_with_noteid(child):
                                return True
                return False
            
            # Get node tree from data
            if 'data' in data:
                node_tree = data['data']
            else:
                node_tree = data
                
            if update_node_with_noteid(node_tree):
                # Save the entire data structure with preserved boundaries
                if boundaries:
                    data['boundaries'] = boundaries
                mm_note['Data'] = json.dumps(data)
                mw.col.update_note(mm_note)
        else:
            # Create new node
            import uuid
            new_node_id = f"node_{uuid.uuid4().hex[:8]}"
            
            new_node = {
                "id": new_node_id,
                "topic": first_line,
                "direction": "right",
                "expanded": True,
                "noteId": card_note.id  # Link back to card
            }
            
            # Find appropriate parent based on special boundary
            parent, insert_index = find_parent_for_new_node(data, special_node_ids)
            
            if not parent:
                # If can't find parent, use root
                if 'data' in data:
                    parent = data['data']
                else:
                    parent = data
                insert_index = -1
            
            if 'children' not in parent:
                parent['children'] = []
            
            # Append as child
            parent['children'].append(new_node)
            
            # Save mindmap - ensure we save the entire data structure with boundaries
            # Also ensure boundaries are properly formatted for saving
            if boundaries:
                data['boundaries'] = boundaries
                print(f"link_existing_card_to_mindmap: Saving {len(boundaries)} boundaries with mindmap")
        
            # Debug: Check if special boundary is preserved
            if boundaries:
                for i, b in enumerate(boundaries):
                    if b.get('isSpecial'):
                        print(f"  Boundary {i} isSpecial={b.get('isSpecial')}, color={b.get('color', '')[:50]}")
        
            mm_note['Data'] = json.dumps(data)
            mw.col.update_note(mm_note)
            print(f"link_existing_card_to_mindmap: Mindmap saved with new node")
            
            # Add link div to card if not exists
            field_to_update = None
            if 'Back' in card_note:
                field_to_update = 'Back'
            elif 'Back Extra' in card_note:
                field_to_update = 'Back Extra'
            elif 'Extra' in card_note:
                field_to_update = 'Extra'
            elif len(card_note.fields) > 1:
                field_to_update = list(card_note.keys())[-1]
            
            if field_to_update:
                link_html = f"""
<div id="mindmap-link" 
     data-mid="{mindmap_id}" 
     data-nid="{new_node_id}" 
     style="display:none;">
</div>
"""
                card_note[field_to_update] += link_html
                mw.col.update_note(card_note)
        
        tooltip(f"Linked existing card to '{mindmap_title}'")
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        showInfo(f"Error linking card to mindmap: {e}")

def delete_node_from_mindmap(mindmap_id, node_id):
    """Delete a node from mindmap when card link is removed"""
    try:
        # Get mindmap note
        try:
            mm_note = mw.col.get_note(mindmap_id)
        except Exception as e:
            print(f"Mindmap {mindmap_id} not found, skipping node deletion: {e}")
            return
        
        data_str = mm_note['Data']
        data = json.loads(data_str)
        
        deleted_count = 0
        
        # Recursive function to find and delete node
        def delete_node(node, parent_children=None, index=None):
            nonlocal deleted_count
            if isinstance(node, dict):
                # Check if this is the node to delete
                if node.get('id') == node_id:
                    if parent_children is not None and index is not None:
                        parent_children.pop(index)
                        deleted_count += 1
                        print(f"Deleted node {node_id} from mindmap {mindmap_id}")
                        return True
                # Recursively check children
                if 'children' in node:
                    for i in range(len(node['children']) - 1, -1, -1):
                        delete_node(node['children'][i], node['children'], i)
            return False
        
        # Delete node from mindmap data
        if 'data' in data:
            delete_node(data['data'])
            
            # Save mindmap if node was deleted
            if deleted_count > 0:
                mm_note['Data'] = json.dumps(data)
                mw.col.update_note(mm_note)
                print(f"Successfully deleted node {node_id} from mindmap {mindmap_id}")
            else:
                print(f"Node {node_id} not found in mindmap {mindmap_id}")
                
    except Exception as e:
        print(f"Error deleting node {node_id} from mindmap {mindmap_id}: {e}")

def add_editor_button(buttons, editor):
    # Store reference to the button index for later updates
    btn = editor.addButton(
        icon=None,
        cmd="mindmap_link",
        func=lambda e=editor: on_editor_btn_click(e),
        tip="Link to Mind Map",
        label="MM",
        id="mindmap_link_btn"  # Add ID for easier selection
    )
    buttons.append(btn)
    
    # Store editor reference for button updates
    if not hasattr(editor, '_mindmap_btn_added'):
        editor._mindmap_btn_added = True
    
    return buttons

# --- Note Creation Hook ---

def on_note_added(note):
    if not hasattr(note, 'mindmap_selection') or not note.mindmap_selection:
        return
        
    mindmap_id = note.mindmap_selection['id']
    
    # Get the first line of the Front field
    if 'Front' in note:
        front_text = note['Front']
        # Replace <br> tags with newlines before processing
        front_text = re.sub(r'<br\s*/?>', '\n', front_text, flags=re.IGNORECASE)
        # Strip other HTML tags for clean text
        clean_text = re.sub('<[^<]+?>', '', front_text)
        first_line = clean_text.split('\n')[0].strip()
        if not first_line:
            first_line = "New Card"
    else:
        first_line = "New Card"
        
    # Update Mind Map
    try:
        mm_note = mw.col.get_note(mindmap_id)
        data_str = mm_note['Data']
        data = json.loads(data_str)
        
        # Preserve boundaries if they exist in the data
        boundaries = data.get('boundaries', [])
        
        # Check for special boundary
        special_node_ids = get_special_boundary_info(data)
        
        # Generate new node ID
        import uuid
        new_node_id = f"node_{uuid.uuid4().hex[:8]}"
        
        # Create new node
        new_node = {
            "id": new_node_id,
            "topic": first_line,
            "direction": "right", # Default to right
            "expanded": True,
            "noteId": note.id # Link to the card
        }
        
        # Find appropriate parent based on special boundary
        parent, insert_index = find_parent_for_new_node(data, special_node_ids)
        
        if not parent:
            # If can't find parent, use root
            if 'data' in data:
                parent = data['data']
            else:
                parent = data
            insert_index = -1
        
        if 'children' not in parent:
            parent['children'] = []
        
        # Append as child
        parent['children'].append(new_node)
        
        # Save Mind Map - ensure we save the entire data structure with boundaries
        # Also ensure boundaries are properly formatted for saving
        if boundaries:
            data['boundaries'] = boundaries
            print(f"on_note_added: Saving {len(boundaries)} boundaries with mindmap")
        
        # Debug: Check if special boundary is preserved
        if boundaries:
            for i, b in enumerate(boundaries):
                if b.get('isSpecial'):
                    print(f"  Boundary {i} isSpecial={b.get('isSpecial')}, color={b.get('color', '')[:50]}")
        
        mm_note['Data'] = json.dumps(data)
        mw.col.update_note(mm_note)
        print(f"on_note_added: Mindmap saved with new node")
        
        # Add Link to Card
        field_to_update = None
        if 'Back' in note:
            field_to_update = 'Back'
        elif 'Back Extra' in note:
            field_to_update = 'Back Extra'
        elif 'Extra' in note:
            field_to_update = 'Extra'
        elif len(note.fields) > 1:
            # Fallback to the last field if it's not the first one
            field_to_update = list(note.keys())[-1]
            
        if field_to_update:
            link_html = f"""
<div id="mindmap-link" 
     data-mid="{mindmap_id}" 
     data-nid="{new_node_id}" 
     style="display:none;">
</div>
"""
            note[field_to_update] += link_html
            mw.col.update_note(note)
            
        tooltip(f"Added node '{first_line}' to Mind Map")
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        showInfo(f"Error linking to mind map: {e}")


def validate_and_cleanup_mindmap(mindmap_note):
    """Validate and cleanup nodes in mindmap - remove noteId if card doesn't exist"""
    try:
        data_str = mindmap_note['Data']
        data = json.loads(data_str)
        
        modified = False
        
        def cleanup_node(node):
            nonlocal modified
            if isinstance(node, dict):
                # Check if node has noteId
                if 'noteId' in node:
                    note_id = node['noteId']
                    # Check if card still exists
                    try:
                        card_note = mw.col.get_note(note_id)
                        # Card exists, no cleanup needed
                    except:
                        # Card was deleted, remove noteId
                        print(f"Card {note_id} no longer exists, removing noteId from node {node.get('id')}")
                        del node['noteId']
                        modified = True
                
                # Recursively check children
                if 'children' in node:
                    for child in node['children']:
                        cleanup_node(child)
        
        if 'data' in data:
            cleanup_node(data['data'])
        
        # Save if modified
        if modified:
            mindmap_note['Data'] = json.dumps(data)
            mw.col.update_note(mindmap_note)
            print(f"Cleaned up mindmap {mindmap_note.id}: removed {modified} invalid noteId references")
            
        # Also validate cross-mindmap links
        try:
            from .cross_link_manager import CrossLinkManager
            removed_cross, removed_back = CrossLinkManager.validate_links(mindmap_note.id)
            if removed_cross > 0 or removed_back > 0:
                print(f"Cleaned up {removed_cross} invalid cross-links and {removed_back} invalid back-links")
        except ImportError as e:
            print(f"CrossLinkManager not available: {e}")
        except Exception as e:
            print(f"Error validating cross-links: {e}")
            
    except Exception as e:
        print(f"Error validating mindmap: {e}")


def on_notes_will_be_deleted(col, ids):
    from aqt import mw
    for nid in ids:
        try:
            note = col.get_note(nid)
            for field_name in note.keys():
                field_content = note[field_name]
                if 'mindmap-link' in field_content and 'data-mid=' in field_content:
                    import re
                    pattern = r'<div id="mindmap-link"\s+data-mid="(\d+)"\s+data-nid="([^"]+)"\s+style="display:none;">\s*</div>'
                    match = re.search(pattern, field_content)
                    if match:
                        mindmap_id = int(match.group(1))
                        node_id = match.group(2)
                        delete_node_from_mindmap(mindmap_id, node_id)
                    break
        except Exception as e:
            print(f"Error processing note {nid} during deletion: {e}")

# --- Initialization ---

def init_card_linker():
    gui_hooks.editor_did_init_buttons.append(add_editor_button)
    gui_hooks.editor_did_load_note.append(on_editor_load_note)  # Added: sync selection state
    gui_hooks.add_cards_did_add_note.append(on_note_added) 
    
    # Register note update hook for bidirectional sync
    from anki import hooks
    hooks.note_will_flush.append(sync_card_to_mindmap)
    
    hooks.notes_will_be_deleted.append(on_notes_will_be_deleted)
