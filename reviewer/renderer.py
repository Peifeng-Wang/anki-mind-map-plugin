"""Webview rendering for the review indicator."""
from aqt import mw

from .js import CLEAR_INDICATOR_JS, _build_indicator_js


MINDMAP_COMMAND_PREFIX = "open_mindmap:"


def _build_pycmd_param(mindmap_id, node_id, mindmap_title):
    """Build the pycmd payload used by the review indicator."""
    if not mindmap_id or not mindmap_title:
        return ""

    pycmd_param = f"{MINDMAP_COMMAND_PREFIX}{mindmap_id}"
    if node_id:
        pycmd_param += f":{node_id}"
    return pycmd_param


def _render_indicator(mindmap_title="", pycmd_param=""):
    """Render or remove the review indicator in the current reviewer webview."""
    if mw.reviewer and mw.reviewer.web:
        if not mindmap_title:
            mw.reviewer.web.eval(CLEAR_INDICATOR_JS)
            return

        mw.reviewer.web.eval(_build_indicator_js(mindmap_title, pycmd_param))
