"""Filesystem & viewer I/O helpers"""
import filecmp
import json
import logging
import os
import shutil

logger = logging.getLogger(__name__)


def _get_documents_path(default_filename):
    return os.path.join(os.path.expanduser("~"), "Documents", default_filename)


def _write_json_file(filename, data):
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def _viewer_copy_is_current(viewer_source, viewer_dest):
    try:
        source_stat = os.stat(viewer_source)
        dest_stat = os.stat(viewer_dest)
    except OSError:
        return False

    if source_stat.st_size != dest_stat.st_size:
        return False
    if source_stat.st_mtime_ns != dest_stat.st_mtime_ns:
        return False
    if source_stat.st_mode != dest_stat.st_mode:
        return False

    try:
        return filecmp.cmp(viewer_source, viewer_dest, shallow=False)
    except OSError:
        return False


def _copy_standalone_viewer(filename):
    try:
        addon_dir = os.path.dirname(os.path.dirname(__file__))
        viewer_source = os.path.join(addon_dir, "web", "standalone_viewer.html")
        export_dir = os.path.dirname(filename)
        viewer_dest = os.path.join(export_dir, "MindMap_Viewer.html")

        if os.path.exists(viewer_source):
            if _viewer_copy_is_current(viewer_source, viewer_dest):
                return viewer_dest
            shutil.copy2(viewer_source, viewer_dest)
            return viewer_dest
    except Exception:
        logger.exception("Failed to copy viewer")

    return None
