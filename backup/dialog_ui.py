"""Qt dialog construction and wiring for the backup tool."""

from aqt.qt import QDialog, QHBoxLayout, QPushButton, QTextEdit, QVBoxLayout
from aqt.utils import showInfo, tooltip

from .localization import _load_language, _save_language, _normalize_language, get_texts
from .export_preview import _format_export_all_preview, _format_export_selected_preview
from .import_logic import import_mindmaps


def show_backup_dialog():
    from aqt import mw
    dialog = MindMapBackupDialog(mw)
    dialog.exec()

BUTTON_ACTIVE_STYLE = "background-color: #4CAF50; color: white; font-weight: bold;"
EXPORT_ALL_STYLE = "padding: 10px; font-size: 14px; background: #28a745; color: white;"
EXPORT_SELECTED_STYLE = "padding: 10px; font-size: 14px; background: #007bff; color: white;"
IMPORT_STYLE = "padding: 10px; font-size: 14px; background: #ffc107; color: black;"


class MindMapBackupDialog(QDialog):
    def __init__(self, mw):
        super().__init__(mw)
        self.mw = mw
        self.current_lang = _load_language(mw)

        self.setWindowTitle("Mind Map Backup & Recovery")
        self.resize(800, 600)
        self._setup_ui()
        self.update_ui_text()

    def _setup_ui(self):
        layout = QVBoxLayout(self)

        layout.addLayout(self._build_language_bar())

        self.info = QTextEdit()
        self.info.setReadOnly(True)
        self.info.setMaximumHeight(100)
        layout.addWidget(self.info)

        layout.addLayout(self._build_action_buttons())

        self.preview = QTextEdit()
        self.preview.setReadOnly(True)
        layout.addWidget(self.preview)

        self.btn_close = QPushButton()
        self.btn_close.clicked.connect(self.close)
        layout.addWidget(self.btn_close)

    def _build_language_bar(self):
        from .localization import TEXTS
        lang_layout = QHBoxLayout()
        self.btn_en = QPushButton("English")
        self.btn_cn = QPushButton(TEXTS["cn"]["language_cn"])
        self.btn_en.clicked.connect(lambda: self.switch_language("en"))
        self.btn_cn.clicked.connect(lambda: self.switch_language("cn"))
        lang_layout.addWidget(self.btn_en)
        lang_layout.addWidget(self.btn_cn)
        lang_layout.addStretch()
        return lang_layout

    def _build_action_buttons(self):
        btn_layout = QHBoxLayout()

        self.btn_export_all = QPushButton()
        self.btn_export_all.setStyleSheet(EXPORT_ALL_STYLE)
        self.btn_export_all.clicked.connect(self.export_all_mindmaps)
        btn_layout.addWidget(self.btn_export_all)

        self.btn_export_selected = QPushButton()
        self.btn_export_selected.setStyleSheet(EXPORT_SELECTED_STYLE)
        self.btn_export_selected.clicked.connect(self.export_selected)
        btn_layout.addWidget(self.btn_export_selected)

        self.btn_import = QPushButton()
        self.btn_import.setStyleSheet(IMPORT_STYLE)
        self.btn_import.clicked.connect(self.import_mindmaps)
        btn_layout.addWidget(self.btn_import)

        return btn_layout

    def switch_language(self, lang):
        self.current_lang = _normalize_language(lang)
        _save_language(self.mw, self.current_lang)
        self.update_ui_text()

    def update_ui_text(self):
        texts = get_texts(self.current_lang)

        self.btn_en.setStyleSheet(BUTTON_ACTIVE_STYLE if self.current_lang == "en" else "")
        self.btn_cn.setStyleSheet(BUTTON_ACTIVE_STYLE if self.current_lang == "cn" else "")

        self.info.setHtml(texts["info"])
        self.btn_export_all.setText(texts["export_all"])
        self.btn_export_selected.setText(texts["export_selected"])
        self.btn_import.setText(texts["import"])
        self.btn_close.setText(texts["close"])
        self.preview.setPlaceholderText(texts["preview_placeholder"])

    def get_english_text(self):
        from .localization import TEXTS
        return TEXTS["en"]

    def get_chinese_text(self):
        from .localization import TEXTS
        return TEXTS["cn"]

    def export_all_mindmaps(self):
        """Export all mind maps to a single JSON file."""
        from ..export_utils import export_all_mindmaps

        success, filename, viewer_path, count = export_all_mindmaps(self, self.mw)

        if not success:
            showInfo(get_texts(self.current_lang)["no_mindmaps"] if count == 0 else get_texts(self.current_lang)["export_failed"])
            return

        self.preview.setHtml(_format_export_all_preview(filename, viewer_path, count))
        tooltip(f"成功导出 {count} 个思维导图")

    def export_selected(self):
        """Export a specific mind map."""
        import traceback
        try:
            from ..export_utils import export_mindmap_to_json
            from ..mindmap_manager import MindMapManager

            manager = MindMapManager(self.mw)
            manager.exec()

            nid = manager.get_selected_nid()
            if not nid:
                showInfo(get_texts(self.current_lang)["select_mindmap"])
                return

            note = self.mw.col.get_note(nid)
            title = note["Title"]

            success, filename, viewer_path = export_mindmap_to_json(self, self.mw, nid, title)
            if not success:
                showInfo(get_texts(self.current_lang)["export_failed"])
                return

            self.preview.setHtml(_format_export_selected_preview(filename, viewer_path, title))
            tooltip(f"成功导出思维导图：{title}")
        except Exception as e:
            showInfo(get_texts(self.current_lang)["export_selected_failed"].format(error=e))
            traceback.print_exc()

    def import_mindmaps(self):
        """Import mind maps from a backup file."""
        from ..note_manager import get_or_create_mindmap_model

        def _format_import_preview(imported_count):
            return f"""
                <b>导入成功！</b><br><br>
                导入了 {imported_count} 个思维导图。<br><br>
                请在 Mind Map Manager 中查看导入的思维导图。
            """

        import_mindmaps(
            self.mw,
            self,
            self.current_lang,
            get_or_create_mindmap_model,
            _format_import_preview,
        )

    # Backwards-compat helpers that existing tests reference on the dialog instance.
    def _extract_mindmaps(self, backup_data):
        from .import_logic import _extract_mindmaps
        return _extract_mindmaps(backup_data)

    def _import_one_mindmap(self, mindmap_data, model):
        from .import_logic import _import_one_mindmap
        return _import_one_mindmap(self.mw, mindmap_data, model)

    def _format_export_selected_preview(self, filename, viewer_path, title):
        from .export_preview import _format_export_selected_preview
        return _format_export_selected_preview(filename, viewer_path, title)
