"""
Display mind map association indicator in review interface
"""
import json
import re
import traceback

from aqt import mw, gui_hooks


MINDMAP_COMMAND_PREFIX = "open_mindmap:"
INDICATOR_ID = "mindmap-indicator"
MINDMAP_ID_RE = re.compile(r'data-mid="(\d+)"')
NODE_ID_RE = re.compile(r'data-nid="([^"]+)"')
CLEAR_INDICATOR_JS = f"""
(function() {{
    var existing = document.getElementById('{INDICATOR_ID}');
    if (existing) {{
        existing.remove();
    }}
}})();
"""


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


def _build_pycmd_param(mindmap_id, node_id, mindmap_title):
    """Build the pycmd payload used by the review indicator."""
    if not mindmap_id or not mindmap_title:
        return ""

    pycmd_param = f"{MINDMAP_COMMAND_PREFIX}{mindmap_id}"
    if node_id:
        pycmd_param += f":{node_id}"
    return pycmd_param


def _build_indicator_js(mindmap_title, pycmd_param):
    """Build JavaScript that replaces the review indicator."""
    display_title = (mindmap_title or "").replace("\n", " ")
    safe_title = json.dumps(display_title)
    safe_pycmd = json.dumps(pycmd_param or "")

    return f"""
(function() {{
    // Remove existing indicator
    var existing = document.getElementById('{INDICATOR_ID}');
    if (existing) {{
        existing.remove();
    }}
    
    // Only add if there's a mind map
    if ({safe_title} === "") {{
        return;
    }}
    
    var indicator = document.createElement('div');
    indicator.id = '{INDICATOR_ID}';
    indicator.style.cssText = 'position:fixed;top:10px;right:10px;background:linear-gradient(135deg,#667eea 0%,#764ba2 100%);color:white;padding:8px 15px;border-radius:20px;font-size:13px;font-weight:500;box-shadow:0 2px 10px rgba(0,0,0,0.2);cursor:pointer;z-index:10000;display:flex;align-items:center;gap:6px;transition:all 0.3s ease;user-select:none;';
    indicator.title = 'Click to open mind map';
    indicator.onclick = function() {{ pycmd({safe_pycmd}); }};
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
    span.textContent={safe_title};
    indicator.appendChild(span);
    
    document.body.appendChild(indicator);
}})();
"""


def _render_indicator(mindmap_title="", pycmd_param=""):
    """Render or remove the review indicator in the current reviewer webview."""
    if mw.reviewer and mw.reviewer.web:
        if not mindmap_title:
            mw.reviewer.web.eval(CLEAR_INDICATOR_JS)
            return

        mw.reviewer.web.eval(_build_indicator_js(mindmap_title, pycmd_param))


def show_mindmap_indicator():
    """Show mind map indicator for current card in reviewer"""
    if not mw.reviewer or not mw.reviewer.card:
        return

    card = mw.reviewer.card
    note = card.note()

    link = _find_mindmap_link(note)
    if not link:
        _render_indicator()
        return

    field_name, mindmap_id, node_id = link
    mindmap_title, should_cleanup_link = _resolve_mindmap_link(mindmap_id, node_id)

    if should_cleanup_link:
        print(f"Node {node_id} no longer exists, cleaning up card link in review")
        from . import card_linker
        card_linker.remove_link_from_card(note, field_name)
        _render_indicator()
        return

    pycmd_param = _build_pycmd_param(mindmap_id, node_id, mindmap_title)
    _render_indicator(mindmap_title, pycmd_param)


def on_reviewer_pycmd(handled, cmd, _):
    """Handle command from clicking mind map indicator in review"""
    if cmd.startswith(MINDMAP_COMMAND_PREFIX):
        try:
            parts = cmd.split(":", 2)
            mindmap_id = int(parts[1])
            node_id = parts[2] if len(parts) > 2 else None

            # Open mind map
            from . import mindmap_opener
            mindmap_opener.open_mindmap(mindmap_id, node_id)
        except Exception as e:
            print(f"Error opening mindmap from reviewer: {e}")
            traceback.print_exc()
        return (True, None)
    return handled


# Register hooks - use reviewer-specific hooks
gui_hooks.reviewer_did_show_question.append(lambda _: show_mindmap_indicator())
gui_hooks.reviewer_did_show_answer.append(lambda _: show_mindmap_indicator())
gui_hooks.webview_did_receive_js_message.append(on_reviewer_pycmd)
