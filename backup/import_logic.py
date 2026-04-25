"""Import business logic for the backup tool."""
import json
import os
import traceback
import uuid

from aqt.qt import QFileDialog
from aqt.utils import showInfo, tooltip

from .localization import IMPORT_SUFFIX, get_texts

DEFAULT_DECK_ID = 0
JSON_FILE_FILTER = "JSON Files (*.json)"


def _documents_path():
    return os.path.join(os.path.expanduser("~"), "Documents")


def _select_backup_file(parent_widget, lang):
    filename, _ = QFileDialog.getOpenFileName(
        parent_widget,
        get_texts(lang)["choose_backup"],
        _documents_path(),
        JSON_FILE_FILTER,
    )
    return filename


def _load_backup_json(filename):
    with open(filename, "r", encoding="utf-8") as f:
        return json.load(f)


def _extract_mindmaps(backup_data):
    if not isinstance(backup_data, dict):
        return []
    if "mindmaps" in backup_data:
        mindmaps = backup_data["mindmaps"]
        return mindmaps if isinstance(mindmaps, list) else []
    return [backup_data]


def _import_one_mindmap(mw, mindmap_data, model):
    title = mindmap_data.get("title", "Imported Mind Map")
    uid = mindmap_data.get("uuid", str(uuid.uuid4()))

    note = mw.col.new_note(model)
    note["Title"] = title + IMPORT_SUFFIX
    note["UUID"] = uid
    note["AllowNewCards"] = mindmap_data.get("allow_new_cards", "1")
    note["Data"] = json.dumps(mindmap_data.get("data", {}))
    note["DisplayHTML"] = f"<h1>{title}</h1><p>(Imported from backup)</p>"

    mw.col.add_note(note, DEFAULT_DECK_ID)


def _import_mindmap_batch(mw, mindmaps, get_model):
    imported_count = 0
    model = None
    for mindmap_data in mindmaps:
        if not isinstance(mindmap_data, dict):
            continue
        try:
            if model is None:
                model = get_model()
            _import_one_mindmap(mw, mindmap_data, model)
            imported_count += 1
        except Exception as e:
            print(f"Error importing mind map {mindmap_data.get('title', 'unknown')}: {e}")
    return imported_count


def import_mindmaps(mw, parent_widget, current_lang, get_model, format_import_preview):
    """Import mind maps from a backup file."""
    try:
        filename = _select_backup_file(parent_widget, current_lang)
        if not filename:
            return

        backup_data = _load_backup_json(filename)
        mindmaps = _extract_mindmaps(backup_data)
        imported_count = _import_mindmap_batch(mw, mindmaps, get_model)

        parent_widget.preview.setHtml(format_import_preview(imported_count))
        tooltip(f"成功导入 {imported_count} 个思维导图")
    except Exception as e:
        showInfo(get_texts(current_lang)["import_failed"].format(error=e))
        traceback.print_exc()
