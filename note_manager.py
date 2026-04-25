import json
from aqt import mw
from anki.models import NotetypeDict

MODEL_NAME = "MindMap Master"
FIELD_TITLE = "Title"
FIELD_DATA = "Data"
FIELD_DISPLAY_HTML = "DisplayHTML"
FIELD_UUID = "UUID"
FIELD_ALLOW_NEW_CARDS = "AllowNewCards"
MODEL_FIELDS = (
    FIELD_TITLE,
    FIELD_DATA,
    FIELD_DISPLAY_HTML,
    FIELD_UUID,
    FIELD_ALLOW_NEW_CARDS,
)
CARD_TEMPLATE_NAME = "Card 1"
CARD_TEMPLATE_QFMT = "{{Title}}<br>{{DisplayHTML}}"
CARD_TEMPLATE_AFMT = "{{FrontSide}}"
DEFAULT_ALLOW_NEW_CARDS = "1"
DEFAULT_DECK_ID = 0
ALLOW_NEW_CARDS_MIGRATION_MESSAGE = (
    "Added AllowNewCards field to existing MindMap Master model"
)


def get_or_create_mindmap_model() -> NotetypeDict:
    """
    Retrieves the MindMap Master note type, creating it if it doesn't exist.
    """
    return _get_or_create_mindmap_model(mw.col)


def _get_or_create_mindmap_model(col) -> NotetypeDict:
    model = col.models.by_name(MODEL_NAME)

    if model:
        _ensure_mindmap_model_schema(col, model)
        return model

    return _create_mindmap_model(col)


def _ensure_mindmap_model_schema(col, model: NotetypeDict) -> None:
    """Apply compatible schema migrations to an existing mind map note type."""
    if not _model_has_field(model, FIELD_ALLOW_NEW_CARDS):
        col.models.add_field(model, col.models.new_field(FIELD_ALLOW_NEW_CARDS))
        col.models.save(model)
        print(ALLOW_NEW_CARDS_MIGRATION_MESSAGE)


def _model_has_field(model: NotetypeDict, field_name: str) -> bool:
    return any(field["name"] == field_name for field in model["flds"])


def _create_mindmap_model(col) -> NotetypeDict:
    model = col.models.new(MODEL_NAME)

    for field_name in MODEL_FIELDS:
        col.models.add_field(model, col.models.new_field(field_name))

    template = col.models.new_template(CARD_TEMPLATE_NAME)
    template["qfmt"] = CARD_TEMPLATE_QFMT
    template["afmt"] = CARD_TEMPLATE_AFMT
    col.models.add_template(model, template)

    col.models.add(model)
    return model


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
