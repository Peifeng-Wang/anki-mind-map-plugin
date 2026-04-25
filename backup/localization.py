"""i18n constants and language persistence for the backup tool."""

CONFIG_KEY_LANGUAGE = "backup_language"
DEFAULT_LANGUAGE = "en"
IMPORT_SUFFIX = " (导入)"

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


def _normalize_language(lang):
    return lang if lang in TEXTS else DEFAULT_LANGUAGE


def _load_language(mw):
    config = mw.addonManager.getConfig(__name__) or {}
    return _normalize_language(config.get(CONFIG_KEY_LANGUAGE, DEFAULT_LANGUAGE))


def _save_language(mw, lang):
    config = mw.addonManager.getConfig(__name__) or {}
    config[CONFIG_KEY_LANGUAGE] = lang
    mw.addonManager.writeConfig(__name__, config)


def get_texts(lang):
    return TEXTS[_normalize_language(lang)]
