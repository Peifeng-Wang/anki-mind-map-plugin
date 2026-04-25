"""Single mind map export"""
from datetime import datetime
from aqt.qt import QFileDialog

from .note_data import _build_mindmap_info
from .file_io import _get_documents_path, _write_json_file, _copy_standalone_viewer
from .error_utils import _print_export_failure


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
