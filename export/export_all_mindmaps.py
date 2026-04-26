"""Bulk export"""
from datetime import datetime
from aqt.qt import QFileDialog

from .note_data import _build_mindmap_info
from .file_io import _get_documents_path, _write_json_file, _copy_standalone_viewer
from .error_utils import _print_export_failure


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
        try:
            from ..card_linker.constants import MINDMAP_NOTE_TYPE_QUERY
        except ImportError:
            from card_linker.constants import MINDMAP_NOTE_TYPE_QUERY
        # Find all mind map notes
        ids = mw.col.find_notes(MINDMAP_NOTE_TYPE_QUERY)

        if not ids:
            return False, None, None, 0

        # Get Anki version
        try:
            anki_ver = str(mw.col.version())
        except Exception:
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
