import logging

from .constants import BR_RE, HTML_TAG_RE, MINDMAP_LINK_RE

try:
    from ..mindmap_editor.tree_utils import find_node, traverse_nodes
except ImportError:
    from mindmap_editor.tree_utils import find_node, traverse_nodes

logger = logging.getLogger(__name__)


def extract_first_line(html_text):
    """Extract the first line of plain text from HTML."""
    if not html_text:
        return ""
    text = BR_RE.sub('\n', html_text)
    text = HTML_TAG_RE.sub('', text)
    return text.split('\n')[0].strip()


def build_node_index(root):
    """Build a flat dict mapping node_id -> node for O(1) lookups."""
    index = {}

    def _add(node):
        node_id = node.get('id')
        if node_id is not None:
            index[node_id] = node

    traverse_nodes(root, _add)
    return index


def find_node_by_id(root, node_id):
    """Recursively find a node by ID in a mind map tree."""
    return find_node(root, node_id)


def parse_mindmap_link(field_content):
    """Parse a mindmap-link div and return (mindmap_id, node_id) or None."""
    match = MINDMAP_LINK_RE.search(field_content)
    if match:
        return int(match.group(1)), match.group(2)
    return None


def select_link_field(note):
    """Select the best field to append a mindmap link to."""
    for candidate in ('Back', 'Back Extra', 'Extra'):
        if candidate in note:
            return candidate
    if len(note.fields) > 1:
        return list(note.keys())[-1]
    return None


def get_root_node(mindmap_data):
    """Return the root node from either a full data dict or a raw node tree."""
    if isinstance(mindmap_data, dict) and 'data' in mindmap_data:
        return mindmap_data['data']
    return mindmap_data
