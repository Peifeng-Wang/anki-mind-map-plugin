"""
Display mind map association indicator in review interface
"""
from aqt import mw, gui_hooks
import re

def show_mindmap_indicator():
    """Show mind map indicator for current card in reviewer"""
    if not mw.reviewer or not mw.reviewer.card:
        return
    
    card = mw.reviewer.card
    note = card.note()
    
    # Check for mind map associations
    mindmap_id = None
    mindmap_title = None
    node_id = None
    
    for field_name in note.keys():
        field_content = note[field_name]
        if 'mindmap-link' in field_content and 'data-mid=' in field_content:
            # Extract mind map ID
            match = re.search(r'data-mid="(\d+)"', field_content)
            if match:
                mindmap_id = int(match.group(1))
                
                # Extract node ID
                node_match = re.search(r'data-nid="([^"]+)"', field_content)
                if node_match:
                    node_id = node_match.group(1)
                
                # Validate: Get mind map title and check node exists
                try:
                    import json
                    mm_note = mw.col.get_note(mindmap_id)
                    mindmap_title = mm_note['Title']
                    
                    # Validate node exists in mindmap
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
                        # Node was deleted, cleanup card link
                        print(f"Node {node_id} no longer exists, cleaning up card link in review")
                        from . import card_linker
                        card_linker.remove_link_from_card(note, field_name)
                        return  # Don't show indicator
                    
                except:
                    # Mindmap was deleted, don't show indicator
                    pass
                break
    
    # Build pycmd parameter
    pycmd_param = ""
    if mindmap_id and mindmap_title:
        pycmd_param = f"open_mindmap:{mindmap_id}"
        if node_id:
            pycmd_param += f":{node_id}"
    
    # Escape values for JavaScript
    safe_title = mindmap_title.replace("\\", "\\\\").replace("'", "\\'").replace('"', '\\"').replace("\n", " ") if mindmap_title else ""
    safe_pycmd = pycmd_param.replace("\\", "\\\\").replace("'", "\\'").replace('"', '\\"')
    
    # JavaScript to manage indicator
    js_code = f"""
(function() {{
    // Remove existing indicator
    var existing = document.getElementById('mindmap-indicator');
    if (existing) {{
        existing.remove();
    }}
    
    // Only add if there's a mind map
    if ("{safe_title}" === "") {{
        return;
    }}
    
    var indicator = document.createElement('div');
    indicator.id = 'mindmap-indicator';
    indicator.style.cssText = 'position:fixed;top:10px;right:10px;background:linear-gradient(135deg,#667eea 0%,#764ba2 100%);color:white;padding:8px 15px;border-radius:20px;font-size:13px;font-weight:500;box-shadow:0 2px 10px rgba(0,0,0,0.2);cursor:pointer;z-index:10000;display:flex;align-items:center;gap:6px;transition:all 0.3s ease;user-select:none;';
    indicator.title = 'Click to open mind map';
    indicator.onclick = function() {{ pycmd("{safe_pycmd}"); }};
    indicator.onmouseover = function() {{ this.style.transform='scale(1.05)';this.style.boxShadow='0 4px 15px rgba(0,0,0,0.3)'; }};
    indicator.onmouseout = function() {{ this.style.transform='scale(1)';this.style.boxShadow='0 2px 10px rgba(0,0,0,0.2)'; }};
    
    var svg = document.createElementNS('http://www.w3.org/2000/svg','svg');
    svg.setAttribute('width','16');
    svg.setAttribute('height','16');
    svg.setAttribute('viewBox','0 0 24 24');
    svg.setAttribute('fill','none');
    svg.setAttribute('stroke','currentColor');
    svg.setAttribute('stroke-width','2');
    
    [[12,12,3],[5,7,2],[19,7,2],[5,17,2],[19,17,2]].forEach(function(c){{
        var circle=document.createElementNS('http://www.w3.org/2000/svg','circle');
        circle.setAttribute('cx',c[0]);circle.setAttribute('cy',c[1]);circle.setAttribute('r',c[2]);
        svg.appendChild(circle);
    }});
    
    ['M9.5 10.5L7 8','M14.5 10.5L17 8','M9.5 13.5L7 16','M14.5 13.5L17 16'].forEach(function(d){{
        var path=document.createElementNS('http://www.w3.org/2000/svg','path');
        path.setAttribute('d',d);
        svg.appendChild(path);
    }});
    
    indicator.appendChild(svg);
    
    var span=document.createElement('span');
    span.style.cssText='max-width:150px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;';
    span.textContent="{safe_title}";
    indicator.appendChild(span);
    
    document.body.appendChild(indicator);
}})();
"""
    
    # Execute JavaScript in reviewer's web view
    if mw.reviewer and mw.reviewer.web:
        mw.reviewer.web.eval(js_code)


def on_reviewer_pycmd(handled, cmd, _):
    """Handle command from clicking mind map indicator in review"""
    if cmd.startswith('open_mindmap:'):
        parts = cmd.split(':')
        mindmap_id = int(parts[1])
        node_id = parts[2] if len(parts) > 2 else None
        
        # Open mind map
        try:
            from . import mindmap_opener
            mindmap_opener.open_mindmap(mindmap_id, node_id)
        except Exception as e:
            print(f"Error opening mindmap from reviewer: {e}")
            import traceback
            traceback.print_exc()
        return (True, None)
    return handled

# Register hooks - use reviewer-specific hooks
gui_hooks.reviewer_did_show_question.append(lambda _: show_mindmap_indicator())
gui_hooks.reviewer_did_show_answer.append(lambda _: show_mindmap_indicator())
gui_hooks.webview_did_receive_js_message.append(on_reviewer_pycmd)
