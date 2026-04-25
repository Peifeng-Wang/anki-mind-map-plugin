"""Note data extraction helpers"""
import json


def _get_optional_note_field(note, field_name, default):
    try:
        return note[field_name]
    except KeyError:
        return default


def _get_note_data(note):
    return json.loads(note['Data']) if note['Data'] else {}


def _build_mindmap_info(note, title=None, note_id=None):
    if title is None:
        title = note['Title']

    mindmap_info = {
        "title": title,
        "uuid": _get_optional_note_field(note, 'UUID', ''),
        "data": _get_note_data(note),
        "allow_new_cards": _get_optional_note_field(note, 'AllowNewCards', '1')
    }

    if note_id is not None:
        mindmap_info["note_id"] = note_id

    return mindmap_info
