import logging
import re
from contextlib import contextmanager

logger = logging.getLogger(__name__)

# --- Module-level compiled regex patterns ---
MINDMAP_LINK_RE = re.compile(
    r'<div\s+id="mindmap-link"\s+data-mid="(\d+)"\s+data-nid="([^"]+)"\s+style="display:none;">\s*</div>',
    re.IGNORECASE,
)
DATA_MID_RE = re.compile(r'data-mid="(\d+)"', re.IGNORECASE)
DATA_NID_RE = re.compile(r'data-nid="([^"]+)"', re.IGNORECASE)
BR_RE = re.compile(r'<br\s*/?>', re.IGNORECASE)
HTML_TAG_RE = re.compile(r'<[^<]+?>')
MINDMAP_LINK_DIV_RE = re.compile(
    r'<div[^>]*id="mindmap-link"[^>]*>.*?</div>\s*',
    re.DOTALL | re.IGNORECASE,
)

# --- JavaScript templates ---
RESET_BUTTON_JS = """
(function() {
    var btn = document.getElementById('mindmap_link_btn');
    if (!btn) {
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

UPDATE_BUTTON_JS_TEMPLATE = """
(function() {{
    var btn = document.getElementById('mindmap_link_btn');
    if (!btn) {{
        var buttons = document.querySelectorAll('button');
        for (var i = 0; i < buttons.length; i++) {{
            var text = buttons[i].textContent.trim();
            if (text === 'MM' || text.includes('📌')) {{
                btn = buttons[i];
                break;
            }}
        }}
    }}
    if (btn) {{
        btn.innerHTML = '📌 {display_title}';
        btn.style.backgroundColor = '#e3f2fd';
        btn.style.color = '#1976d2';
        btn.title = 'Linked to: {full_title}';
    }}
}})();
"""

LINK_HTML_TEMPLATE = """
<div id="mindmap-link"
     data-mid="{mindmap_id}"
     data-nid="{node_id}"
     style="display:none;">
</div>
"""


# --- Synchronization flags ---

class _SyncFlags:
    """Simple container for sync flags with context-manager support."""

    def __init__(self):
        self.syncing_from_card = False
        self.syncing_from_node = False

    @contextmanager
    def card_sync(self):
        self.syncing_from_card = True
        try:
            yield
        finally:
            self.syncing_from_card = False


_sync_flags = _SyncFlags()
