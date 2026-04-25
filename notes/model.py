from .config import (
    ALLOW_NEW_CARDS_MIGRATION_MESSAGE,
    CARD_TEMPLATE_AFMT,
    CARD_TEMPLATE_NAME,
    CARD_TEMPLATE_QFMT,
    FIELD_ALLOW_NEW_CARDS,
    MODEL_FIELDS,
    MODEL_NAME,
)


def get_or_create_mindmap_model():
    """
    Retrieves the MindMap Master note type, creating it if it doesn't exist.
    """
    from aqt import mw

    return _get_or_create_mindmap_model(mw.col)


def _get_or_create_mindmap_model(col):
    model = col.models.by_name(MODEL_NAME)

    if model:
        _ensure_mindmap_model_schema(col, model)
        return model

    return _create_mindmap_model(col)


def _ensure_mindmap_model_schema(col, model) -> None:
    """Apply compatible schema migrations to an existing mind map note type."""
    if not _model_has_field(model, FIELD_ALLOW_NEW_CARDS):
        col.models.add_field(model, col.models.new_field(FIELD_ALLOW_NEW_CARDS))
        col.models.save(model)
        print(ALLOW_NEW_CARDS_MIGRATION_MESSAGE)


def _model_has_field(model, field_name: str) -> bool:
    return any(field["name"] == field_name for field in model["flds"])


def _create_mindmap_model(col):
    model = col.models.new(MODEL_NAME)

    for field_name in MODEL_FIELDS:
        col.models.add_field(model, col.models.new_field(field_name))

    template = col.models.new_template(CARD_TEMPLATE_NAME)
    template["qfmt"] = CARD_TEMPLATE_QFMT
    template["afmt"] = CARD_TEMPLATE_AFMT
    col.models.add_template(model, template)

    col.models.add(model)
    return model
