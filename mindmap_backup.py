"""MindMap Backup and Recovery Tool

Provides export/import functionality to ensure data safety.
This module is a facade/entry point that re-exports the dialog and helpers
so existing imports continue to work.
"""

# Re-export the dialog and entry-point function
from .backup.dialog_ui import MindMapBackupDialog, show_backup_dialog

# Re-export internal helpers that existing tests reference directly.
from .backup.import_logic import _extract_mindmaps, _import_one_mindmap
from .backup.export_preview import _format_export_selected_preview
