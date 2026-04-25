"""
Unified mind map export utility functions
Avoid duplicating export logic across multiple files
"""
import json
import os
import shutil
import traceback
from datetime import datetime
from aqt.qt import QFileDialog


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


def _get_documents_path(default_filename):
    return os.path.join(os.path.expanduser("~"), "Documents", default_filename)


def _write_json_file(filename, data):
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def _copy_standalone_viewer(filename):
    try:
        addon_dir = os.path.dirname(__file__)
        viewer_source = os.path.join(addon_dir, "web", "standalone_viewer.html")
        export_dir = os.path.dirname(filename)
        viewer_dest = os.path.join(export_dir, "MindMap_Viewer.html")

        if os.path.exists(viewer_source):
            shutil.copy2(viewer_source, viewer_dest)
            return viewer_dest
    except Exception as e:
        print(f"Failed to copy viewer: {e}")

    return None


def _print_export_failure(message, exception):
    print(f"{message}: {exception}")
    traceback.print_exc()


def export_mindmap_to_json(parent_widget, mw, note_id, title=None):
    """
    Export single mind map to JSON file and copy visualization viewer
    
    Args:
        parent_widget: Parent window (for file dialog)
        mw: Anki main window
        note_id: Mind map note ID
        title: Mind map title (optional, read from note if not provided)
    
    Returns:
        tuple: (success: bool, filename: str or None, viewer_path: str or None)
    """
    try:
        # Get mind map note
        note = mw.col.get_note(note_id)

        if title is None:
            title = note['Title']

        mindmap_info = _build_mindmap_info(note, title=title)

        # Prepare export data
        backup_data = {
            "export_date": datetime.now().isoformat(),
            "title": mindmap_info["title"],
            "uuid": mindmap_info["uuid"],
            "data": mindmap_info["data"],
            "allow_new_cards": mindmap_info["allow_new_cards"]
        }

        # Generate safe filename
        safe_title = "".join(c for c in title if c.isalnum() or c in (' ', '_', '-'))
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        default_filename = f"mindmap_{safe_title}_{timestamp}.json"

        # Show save dialog
        filename, _ = QFileDialog.getSaveFileName(
            parent_widget,
            f"Export Mind Map: {title}",
            _get_documents_path(default_filename),
            "JSON Files (*.json)"
        )

        if not filename:
            return False, None, None

        # Save JSON file
        _write_json_file(filename, backup_data)

        # Copy standalone viewer
        viewer_path = _copy_standalone_viewer(filename)

        return True, filename, viewer_path

    except Exception as e:
        _print_export_failure("Export failed", e)
        return False, None, None


def export_all_mindmaps(parent_widget, mw):
    """
    Export all mind maps to single JSON file
    
    Args:
        parent_widget: Parent window (for file dialog)
        mw: Anki main window
    
    Returns:
        tuple: (success: bool, filename: str or None, viewer_path: str or None, count: int)
    """
    try:
        # Find all mind map notes
        ids = mw.col.find_notes('"note:MindMap Master"')

        if not ids:
            return False, None, None, 0

        # Get Anki version
        try:
            anki_ver = str(mw.col.version())
        except:
            anki_ver = "unknown"

        # Collect all mind map data
        backup_data = {
            "export_date": datetime.now().isoformat(),
            "anki_version": anki_ver,
            "mindmaps": []
        }

        for nid in ids:
            note = mw.col.get_note(nid)
            backup_data["mindmaps"].append(_build_mindmap_info(note, note_id=nid))

        # Generate filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        default_filename = f"anki_mindmaps_backup_{timestamp}.json"

        # Show save dialog
        filename, _ = QFileDialog.getSaveFileName(
            parent_widget,
            "Save Mind Maps Backup",
            _get_documents_path(default_filename),
            "JSON Files (*.json)"
        )

        if not filename:
            return False, None, None, 0

        # Save JSON file
        _write_json_file(filename, backup_data)

        # Copy standalone viewer
        viewer_path = _copy_standalone_viewer(filename)

        return True, filename, viewer_path, len(ids)

    except Exception as e:
        _print_export_failure("Export all failed", e)
        return False, None, None, 0
