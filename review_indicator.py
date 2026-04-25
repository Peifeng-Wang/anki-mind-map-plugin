"""
Display mind map association indicator in review interface
"""
import traceback

from aqt import mw, gui_hooks

from .reviewer.js import CLEAR_INDICATOR_JS, _build_indicator_js
from .reviewer.link_resolver import (
    MINDMAP_ID_RE,
    NODE_ID_RE,
    _find_mindmap_link,
    _node_exists,
    _resolve_mindmap_link,
)
from .reviewer.renderer import MINDMAP_COMMAND_PREFIX, _build_pycmd_param, _render_indicator


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
