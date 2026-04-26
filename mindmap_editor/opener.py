"""Open a mind map dialog from any caller (e.g., reviewer)."""
from aqt import mw

from . import MindMapDialog


def open_mindmap(mindmap_id, node_id=None):
    """Open mind map by ID, optionally focusing on a specific node."""
    try:
        MindMapDialog.open_instance(mw, mindmap_id, node_id)
    except Exception as e:
        from aqt.utils import showInfo
        showInfo(f"Unable to open mind map: {e}")
