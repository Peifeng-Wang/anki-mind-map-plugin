from .constants import (
    BR_RE,
    DATA_MID_RE,
    DATA_NID_RE,
    HTML_TAG_RE,
    LINK_HTML_TEMPLATE,
    MINDMAP_LINK_DIV_RE,
    MINDMAP_LINK_RE,
    RESET_BUTTON_JS,
    UPDATE_BUTTON_JS_TEMPLATE,
    _SyncFlags,
    _sync_flags,
)
from .core import (
    delete_node_from_mindmap,
    delete_nodes_from_mindmap,
    link_existing_card_to_mindmap,
    on_note_added,
    sync_card_to_mindmap,
)
from .editor import (
    add_editor_button,
    clear_mindmap_selection,
    on_editor_btn_click,
    on_editor_load_note,
    reset_mindmap_button,
    update_mindmap_button,
)
from .mindmap_ops import find_parent_for_new_node, get_special_boundary_info
from .utils import (
    build_node_index,
    extract_first_line,
    find_node_by_id,
    get_root_node,
    parse_mindmap_link,
    select_link_field,
)
from .validation import (
    on_notes_will_be_deleted,
    remove_link_from_card,
    validate_and_cleanup_mindmap,
)


def init_card_linker():
    from anki import hooks
    from aqt import gui_hooks

    gui_hooks.editor_did_init_buttons.append(add_editor_button)
    gui_hooks.editor_did_load_note.append(on_editor_load_note)
    gui_hooks.add_cards_did_add_note.append(on_note_added)
    hooks.note_will_flush.append(sync_card_to_mindmap)
    hooks.notes_will_be_deleted.append(on_notes_will_be_deleted)
