"""
MindMap Backup and Recovery Tool
Provides export/import functionality to ensure data safety.
"""
import html
import json
import os
import traceback
import uuid

from aqt import mw
from aqt.qt import QFileDialog, QDialog, QHBoxLayout, QPushButton, QTextEdit, QVBoxLayout
from aqt.utils import showInfo, tooltip


CONFIG_KEY_LANGUAGE = "backup_language"
DEFAULT_LANGUAGE = "en"
IMPORT_SUFFIX = " (导入)"
DEFAULT_DECK_ID = 0
JSON_FILE_FILTER = "JSON Files (*.json)"

BUTTON_ACTIVE_STYLE = "background-color: #4CAF50; color: white; font-weight: bold;"
EXPORT_ALL_STYLE = "padding: 10px; font-size: 14px; background: #28a745; color: white;"
EXPORT_SELECTED_STYLE = "padding: 10px; font-size: 14px; background: #007bff; color: white;"
IMPORT_STYLE = "padding: 10px; font-size: 14px; background: #ffc107; color: black;"

TEXTS = {
    "en": {
        "language_cn": "中文",
        "info": """
            <h3>Mind Map Backup Tool</h3>
            <p><b>Export All Mind Maps</b>: Export all mind maps as JSON files with an HTML viewer.</p>
            <p><b>Import Mind Maps</b>: Restore mind maps from JSON backup files.</p>
            """,
        "export_all": "Export All Mind Maps",
        "export_selected": "Export Selected Mind Map",
        "import": "Import Mind Maps",
        "close": "Close",
        "preview_placeholder": "Backup preview will be displayed here...",
        "no_mindmaps": "No mind map data found.",
        "export_failed": "Export cancelled or failed.",
        "select_mindmap": "Please select a mind map.",
        "choose_backup": "Choose Backup File",
        "import_failed": "Import failed: {error}",
        "export_selected_failed": "Export failed: {error}",
        "imported_suffix": IMPORT_SUFFIX,
    },
    "cn": {
        "language_cn": "中文",
        "info": """
            <h3>思维导图备份工具</h3>
            <p><b>导出所有思维导图</b>：将所有思维导图数据导出为 JSON 文件，并附带 HTML 查看器。</p>
            <p><b>导入思维导图</b>：从 JSON 备份文件恢复思维导图数据。</p>
            """,
        "export_all": "导出所有思维导图",
        "export_selected": "导出选定的思维导图",
        "import": "导入思维导图",
        "close": "关闭",
        "preview_placeholder": "备份预览将显示在这里...",
        "no_mindmaps": "没有找到思维导图数据。",
        "export_failed": "导出已取消或失败。",
        "select_mindmap": "请选择一个思维导图。",
        "choose_backup": "选择备份文件",
        "import_failed": "导入失败：{error}",
        "export_selected_failed": "导出失败：{error}",
        "imported_suffix": IMPORT_SUFFIX,
    },
}


def _documents_path():
    return os.path.join(os.path.expanduser("~"), "Documents")


def _escape(value):
    return html.escape(str(value), quote=True)


class MindMapBackupDialog(QDialog):
    def __init__(self, mw):
        super().__init__(mw)
        self.mw = mw
        self.current_lang = self._load_language()

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

    def _load_language(self):
        config = self.mw.addonManager.getConfig(__name__) or {}
        return self._normalize_language(config.get(CONFIG_KEY_LANGUAGE, DEFAULT_LANGUAGE))

    def _save_language(self, lang):
        config = self.mw.addonManager.getConfig(__name__) or {}
        config[CONFIG_KEY_LANGUAGE] = lang
        self.mw.addonManager.writeConfig(__name__, config)

    def _normalize_language(self, lang):
        return lang if lang in TEXTS else DEFAULT_LANGUAGE

    def _texts(self):
        return TEXTS[self.current_lang]

    def switch_language(self, lang):
        self.current_lang = self._normalize_language(lang)
        self._save_language(self.current_lang)
        self.update_ui_text()

    def update_ui_text(self):
        texts = self._texts()

        self.btn_en.setStyleSheet(BUTTON_ACTIVE_STYLE if self.current_lang == "en" else "")
        self.btn_cn.setStyleSheet(BUTTON_ACTIVE_STYLE if self.current_lang == "cn" else "")

        self.info.setHtml(texts["info"])
        self.btn_export_all.setText(texts["export_all"])
        self.btn_export_selected.setText(texts["export_selected"])
        self.btn_import.setText(texts["import"])
        self.btn_close.setText(texts["close"])
        self.preview.setPlaceholderText(texts["preview_placeholder"])

    def get_english_text(self):
        return TEXTS["en"]

    def get_chinese_text(self):
        return TEXTS["cn"]

    def export_all_mindmaps(self):
        """Export all mind maps to a single JSON file."""
        from .export_utils import export_all_mindmaps

        success, filename, viewer_path, count = export_all_mindmaps(self, self.mw)

        if not success:
            showInfo(self._texts()["no_mindmaps"] if count == 0 else self._texts()["export_failed"])
            return

        self.preview.setHtml(self._format_export_all_preview(filename, viewer_path, count))
        tooltip(f"成功导出 {count} 个思维导图")

    def _format_export_all_preview(self, filename, viewer_path, count):
        viewer_line = ""
        viewer_help = ""
        if viewer_path:
            viewer_line = f"查看器：{_escape(viewer_path)}<br><br>"
            viewer_help = """
                <b>如何查看思维导图：</b><br>
                1. 双击 <code>MindMap_Viewer.html</code> 在浏览器中打开。<br>
                2. 点击“选择 JSON 备份文件”，选择刚导出的 JSON 文件。<br>
                3. 即可在浏览器中查看可视化思维导图。<br><br>
            """

        return f"""
            <b>导出成功！</b><br><br>
            JSON 文件：{_escape(filename)}<br>
            {viewer_line}
            {viewer_help}
            导出了 {count} 个思维导图。<br><br>
            <b>重要提示：</b><br>
            - JSON 文件包含所有原始数据。<br>
            - HTML 查看器可离线使用，不依赖 Anki 或插件。<br>
        """

    def export_selected(self):
        """Export a specific mind map."""
        try:
            from .export_utils import export_mindmap_to_json
            from .mindmap_manager import MindMapManager

            manager = MindMapManager(self.mw)
            manager.exec()

            nid = manager.get_selected_nid()
            if not nid:
                showInfo(self._texts()["select_mindmap"])
                return

            note = self.mw.col.get_note(nid)
            title = note["Title"]

            success, filename, viewer_path = export_mindmap_to_json(self, self.mw, nid, title)
            if not success:
                showInfo(self._texts()["export_failed"])
                return

            self.preview.setHtml(self._format_export_selected_preview(filename, viewer_path, title))
            tooltip(f"成功导出思维导图：{title}")
        except Exception as e:
            showInfo(self._texts()["export_selected_failed"].format(error=e))
            traceback.print_exc()

    def _format_export_selected_preview(self, filename, viewer_path, title):
        viewer_line = ""
        if viewer_path:
            viewer_line = f"""
                查看器：{_escape(viewer_path)}<br><br>
                <b>双击 MindMap_Viewer.html 即可在浏览器中查看。</b><br>
            """

        return f"""
            <b>导出成功！</b><br><br>
            JSON 文件：{_escape(filename)}<br>
            {viewer_line}
            <br>
            思维导图：{_escape(title)}<br>
        """

    def import_mindmaps(self):
        """Import mind maps from a backup file."""
        try:
            filename = self._select_backup_file()
            if not filename:
                return

            backup_data = self._load_backup_json(filename)
            mindmaps = self._extract_mindmaps(backup_data)
            imported_count = self._import_mindmap_batch(mindmaps)

            self.preview.setHtml(self._format_import_preview(imported_count))
            tooltip(f"成功导入 {imported_count} 个思维导图")
        except Exception as e:
            showInfo(self._texts()["import_failed"].format(error=e))
            traceback.print_exc()

    def _select_backup_file(self):
        filename, _ = QFileDialog.getOpenFileName(
            self,
            self._texts()["choose_backup"],
            _documents_path(),
            JSON_FILE_FILTER,
        )
        return filename

    def _load_backup_json(self, filename):
        with open(filename, "r", encoding="utf-8") as f:
            return json.load(f)

    def _extract_mindmaps(self, backup_data):
        if not isinstance(backup_data, dict):
            return []
        if "mindmaps" in backup_data:
            mindmaps = backup_data["mindmaps"]
            return mindmaps if isinstance(mindmaps, list) else []
        return [backup_data]

    def _import_mindmap_batch(self, mindmaps):
        imported_count = 0
        model = None
        for mindmap_data in mindmaps:
            if not isinstance(mindmap_data, dict):
                continue
            try:
                if model is None:
                    from .note_manager import get_or_create_mindmap_model

                    model = get_or_create_mindmap_model()
                self._import_one_mindmap(mindmap_data, model)
                imported_count += 1
            except Exception as e:
                print(f"Error importing mind map {mindmap_data.get('title', 'unknown')}: {e}")
        return imported_count

    def _import_one_mindmap(self, mindmap_data, model):
        title = mindmap_data.get("title", "Imported Mind Map")
        uid = mindmap_data.get("uuid", str(uuid.uuid4()))

        note = self.mw.col.new_note(model)
        note["Title"] = title + IMPORT_SUFFIX
        note["UUID"] = uid
        note["AllowNewCards"] = mindmap_data.get("allow_new_cards", "1")
        note["Data"] = json.dumps(mindmap_data.get("data", {}))
        note["DisplayHTML"] = f"<h1>{title}</h1><p>(Imported from backup)</p>"

        self.mw.col.add_note(note, DEFAULT_DECK_ID)

    def _format_import_preview(self, imported_count):
        return f"""
            <b>导入成功！</b><br><br>
            导入了 {imported_count} 个思维导图。<br><br>
            请在 Mind Map Manager 中查看导入的思维导图。
        """


def show_backup_dialog():
    """Show the backup dialog."""
    dialog = MindMapBackupDialog(mw)
    dialog.exec()
