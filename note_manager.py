import json
from aqt import mw
from anki.models import NotetypeDict

from .notes.config import (
    ALLOW_NEW_CARDS_MIGRATION_MESSAGE,
    CARD_TEMPLATE_AFMT,
    CARD_TEMPLATE_NAME,
    CARD_TEMPLATE_QFMT,
    DEFAULT_ALLOW_NEW_CARDS,
    DEFAULT_DECK_ID,
    FIELD_ALLOW_NEW_CARDS,
    FIELD_DATA,
    FIELD_DISPLAY_HTML,
    FIELD_TITLE,
    FIELD_UUID,
    MODEL_FIELDS,
    MODEL_NAME,
)
from .notes.model import (
    _create_mindmap_model,
    _ensure_mindmap_model_schema,
    _get_or_create_mindmap_model,
    _model_has_field,
    get_or_create_mindmap_model,
)


def create_new_mindmap_note(title: str, uuid_str: str) -> int:
    """
    Creates a new MindMap note and returns its ID.
    """
    return _create_new_mindmap_note(mw.col, title, uuid_str)


def _create_new_mindmap_note(col, title: str, uuid_str: str) -> int:
    model = _get_or_create_mindmap_model(col)
    return _create_new_mindmap_note_with_model(col, model, title, uuid_str)


def _create_new_mindmap_note_with_model(
    col, model: NotetypeDict, title: str, uuid_str: str
) -> int:
    note = col.new_note(model)
    _populate_mindmap_note_fields(note, title, uuid_str)

    col.add_note(note, DEFAULT_DECK_ID)
    return note.id


def _populate_mindmap_note_fields(note, title: str, uuid_str: str) -> None:
    note[FIELD_TITLE] = title
    note[FIELD_UUID] = uuid_str
    note[FIELD_ALLOW_NEW_CARDS] = DEFAULT_ALLOW_NEW_CARDS
    note[FIELD_DATA] = json.dumps(_build_initial_mindmap_data(title))
    note[FIELD_DISPLAY_HTML] = _build_display_html(title)


def _build_initial_mindmap_data(title: str) -> dict:
    return {
        "meta": {
            "name": title,
            "author": "anki",
            "version": "0.2"
        },
        "format": "node_tree",
        "data": {
            "id": "root",
            "topic": title
        }
    }


def _build_display_html(title: str) -> str:
    return f"<h1>{title}</h1><p>(Open MindMap Editor to view)</p>"
