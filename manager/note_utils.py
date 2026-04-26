import json

from ..card_linker.constants import MINDMAP_NOTE_TYPE_QUERY


FIELD_TITLE = 'Title'
FIELD_DATA = 'Data'
FIELD_ALLOW_NEW_CARDS = 'AllowNewCards'
ALLOW_NEW_CARDS_ENABLED = "1"
ALLOW_NEW_CARDS_DISABLED = "0"
ACTIVE_ICON = "✓"
INACTIVE_ICON = "✗"
NOTE_QUERY = MINDMAP_NOTE_TYPE_QUERY


def get_note_title(note):
    return note[FIELD_TITLE]


def get_allow_new_cards(note):
    try:
        return note[FIELD_ALLOW_NEW_CARDS]
    except KeyError:
        # Default to enabled if older notes do not have this field.
        return ALLOW_NEW_CARDS_ENABLED


def load_note_data(note):
    return json.loads(note[FIELD_DATA])


def save_note_data(note, data):
    note[FIELD_DATA] = json.dumps(data)


def sync_root_title(note, new_title):
    try:
        data = load_note_data(note)
        if data.get('nodeData') and data['nodeData'].get('id') == 'root':
            data['nodeData']['topic'] = new_title
            save_note_data(note, data)
    except Exception:
        pass
