import importlib
import json
import os
import sys
import types
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PACKAGE_NAME = "mindmap_plugin_under_test"


class Signal:
    def __init__(self):
        self.handlers = []

    def connect(self, handler):
        self.handlers.append(handler)


class FakeWidget:
    def __init__(self, *args, **kwargs):
        self.args = args
        self.children = []
        self.stylesheet = ""
        self.text = args[0] if args and isinstance(args[0], str) else ""
        self.html = ""
        self.placeholder = ""
        self.readonly = False
        self.maximum_height = None
        self.clicked = Signal()
        self.itemDoubleClicked = Signal()
        self._current_row = -1
        self.items = []

    def setWindowTitle(self, value):
        self.window_title = value

    def resize(self, width, height):
        self.size = (width, height)

    def addWidget(self, widget):
        self.children.append(widget)

    def addLayout(self, layout):
        self.children.append(layout)

    def addStretch(self):
        self.children.append("stretch")

    def setReadOnly(self, value):
        self.readonly = value

    def setMaximumHeight(self, value):
        self.maximum_height = value

    def setStyleSheet(self, value):
        self.stylesheet = value

    def setText(self, value):
        self.text = value

    def setHtml(self, value):
        self.html = value

    def setPlaceholderText(self, value):
        self.placeholder = value

    def setOpenExternalLinks(self, value):
        self.open_external_links = value

    def setSearchPaths(self, value):
        self.search_paths = value

    def clear(self):
        self.items.clear()

    def addItem(self, value):
        self.items.append(value)

    def currentRow(self):
        return self._current_row

    def setCurrentRow(self, value):
        self._current_row = value

    def exec(self):
        return None

    def close(self):
        self.closed = True


class FakeFileDialog:
    save_filename = ""
    open_filename = ""

    @staticmethod
    def getSaveFileName(*args):
        return FakeFileDialog.save_filename, ""

    @staticmethod
    def getOpenFileName(*args):
        return FakeFileDialog.open_filename, ""


class HookList(list):
    pass


class FakeAddonManager:
    def __init__(self):
        self.config = {}
        self.writes = []

    def getConfig(self, name):
        return dict(self.config)

    def writeConfig(self, name, config):
        self.writes.append((name, dict(config)))
        self.config = dict(config)


class FakeNote(dict):
    def __init__(self, note_id=0, **fields):
        super().__init__(fields)
        self.id = note_id

    def keys(self):
        return super().keys()


class FakeModels:
    def __init__(self, existing=None):
        self.existing = existing
        self.saved = []
        self.added = []

    def by_name(self, name):
        return self.existing

    def new(self, name):
        return {"name": name, "flds": [], "tmpls": []}

    def new_field(self, name):
        return {"name": name}

    def add_field(self, model, field):
        model["flds"].append(field)

    def new_template(self, name):
        return {"name": name}

    def add_template(self, model, template):
        model["tmpls"].append(template)

    def add(self, model):
        self.added.append(model)
        self.existing = model

    def save(self, model):
        self.saved.append(model)


class FakeCollection:
    def __init__(self, notes=None, models=None):
        self.notes = notes or {}
        self.models = models or FakeModels()
        self.added_notes = []
        self.updated_notes = []
        self.removed_notes = []

    def get_note(self, note_id):
        return self.notes[note_id]

    def find_notes(self, query):
        return list(self.notes)

    def version(self):
        return 42

    def new_note(self, model):
        return FakeNote(999)

    def add_note(self, note, deck_id):
        note.deck_id = deck_id
        self.added_notes.append(note)

    def update_note(self, note):
        self.updated_notes.append(note)

    def remove_notes(self, note_ids):
        self.removed_notes.extend(note_ids)


class FakeMainWindow:
    def __init__(self):
        self.addonManager = FakeAddonManager()
        self.col = FakeCollection()
        self.reviewer = None
        self.mindmap_editors = []


def install_anki_stubs():
    fake_mw = FakeMainWindow()
    from _aqt_stub import install_aqt_stub

    def _utils_factory():
        utils = types.ModuleType("aqt.utils")
        utils.messages = []
        utils.tooltips = []
        utils.showInfo = lambda message: utils.messages.append(message)
        utils.tooltip = lambda message: utils.tooltips.append(message)
        utils.getText = lambda *args, **kwargs: ("", False)
        utils.askUser = lambda *args, **kwargs: False
        return utils

    _, _, utils, hooks = install_aqt_stub(
        fake_mw=fake_mw,
        widget_factory=FakeWidget,
        file_dialog=FakeFileDialog,
        hook_list_cls=HookList,
        hook_names=(
            "reviewer_did_show_question",
            "reviewer_did_show_answer",
            "webview_did_receive_js_message",
        ),
        utils_factory=_utils_factory,
    )
    qt = sys.modules["aqt.qt"]
    qt.QTimer = types.SimpleNamespace(singleShot=lambda ms, cb: None)
    return fake_mw, utils, hooks


def import_plugin_module(name):
    if PACKAGE_NAME not in sys.modules:
        package = types.ModuleType(PACKAGE_NAME)
        package.__path__ = [str(ROOT)]
        sys.modules[PACKAGE_NAME] = package
    full_name = f"{PACKAGE_NAME}.{name}"
    sys.modules.pop(full_name, None)
    return importlib.import_module(full_name)


class BackupModuleTests(unittest.TestCase):
    def setUp(self):
        self.mw, self.utils, self.hooks = install_anki_stubs()
        FakeFileDialog.save_filename = ""
        FakeFileDialog.open_filename = ""
        for key in list(sys.modules):
            if key.startswith(f"{PACKAGE_NAME}."):
                sys.modules.pop(key)

    # ------------------------------------------------------------------
    # localization.py
    # ------------------------------------------------------------------
    def test_localization_constants(self):
        loc = import_plugin_module("backup.localization")
        self.assertEqual(loc.CONFIG_KEY_LANGUAGE, "backup_language")
        self.assertEqual(loc.DEFAULT_LANGUAGE, "en")
        self.assertEqual(loc.IMPORT_SUFFIX, " (导入)")

    def test_normalize_language(self):
        loc = import_plugin_module("backup.localization")
        self.assertEqual(loc._normalize_language("en"), "en")
        self.assertEqual(loc._normalize_language("cn"), "cn")
        self.assertEqual(loc._normalize_language("fr"), "en")
        self.assertEqual(loc._normalize_language(None), "en")

    def test_load_and_save_language(self):
        loc = import_plugin_module("backup.localization")
        self.assertEqual(loc._load_language(self.mw), "en")
        loc._save_language(self.mw, "cn")
        self.assertEqual(self.mw.addonManager.config["backup_language"], "cn")
        self.assertEqual(loc._load_language(self.mw), "cn")

    def test_get_texts(self):
        loc = import_plugin_module("backup.localization")
        texts = loc.get_texts("cn")
        self.assertEqual(texts["close"], "关闭")
        texts_default = loc.get_texts("unknown")
        self.assertEqual(texts_default["close"], "Close")

    # ------------------------------------------------------------------
    # export_preview.py
    # ------------------------------------------------------------------
    def test_escape(self):
        ep = import_plugin_module("backup.export_preview")
        self.assertEqual(ep._escape("<script>"), "&lt;script&gt;")
        self.assertEqual(ep._escape('"x"'), "&quot;x&quot;")

    def test_format_export_all_preview_with_viewer(self):
        ep = import_plugin_module("backup.export_preview")
        preview = ep._format_export_all_preview("file.json", "viewer.html", 3)
        self.assertIn("file.json", preview)
        self.assertIn("viewer.html", preview)
        self.assertIn("3", preview)
        self.assertIn("如何查看思维导图", preview)

    def test_format_export_all_preview_without_viewer(self):
        ep = import_plugin_module("backup.export_preview")
        preview = ep._format_export_all_preview("file.json", None, 1)
        self.assertIn("file.json", preview)
        self.assertNotIn("viewer.html", preview)

    def test_format_export_selected_preview_with_viewer(self):
        ep = import_plugin_module("backup.export_preview")
        preview = ep._format_export_selected_preview("sel.json", "v.html", "Title")
        self.assertIn("sel.json", preview)
        self.assertIn("v.html", preview)
        self.assertIn("Title", preview)

    def test_format_export_selected_preview_without_viewer(self):
        ep = import_plugin_module("backup.export_preview")
        preview = ep._format_export_selected_preview("sel.json", None, "T")
        self.assertIn("sel.json", preview)
        self.assertNotIn("v.html", preview)

    # ------------------------------------------------------------------
    # import_logic.py
    # ------------------------------------------------------------------
    def test_select_backup_file(self):
        il = import_plugin_module("backup.import_logic")
        FakeFileDialog.open_filename = "/tmp/backup.json"
        result = il._select_backup_file(None, "en")
        self.assertEqual(result, "/tmp/backup.json")

    def test_load_backup_json(self):
        il = import_plugin_module("backup.import_logic")
        import tempfile
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False, encoding="utf-8") as f:
            json.dump({"mindmaps": [{"title": "A"}]}, f)
            name = f.name
        try:
            data = il._load_backup_json(name)
            self.assertEqual(data["mindmaps"][0]["title"], "A")
        finally:
            os.unlink(name)

    def test_extract_mindmaps(self):
        il = import_plugin_module("backup.import_logic")
        self.assertEqual(il._extract_mindmaps({"mindmaps": [{"title": "A"}]}), [{"title": "A"}])
        self.assertEqual(il._extract_mindmaps({"title": "Single"}), [{"title": "Single"}])
        self.assertEqual(il._extract_mindmaps([]), [])
        self.assertEqual(il._extract_mindmaps("bad"), [])
        self.assertEqual(il._extract_mindmaps({"mindmaps": "notalist"}), [])

    def test_import_one_mindmap(self):
        il = import_plugin_module("backup.import_logic")
        model = {"name": "MindMap Master", "flds": [], "tmpls": []}
        self.mw.col = FakeCollection()
        il._import_one_mindmap(
            self.mw,
            {"title": "Imported", "uuid": "u", "data": {"data": {}}, "allow_new_cards": "0"},
            model,
        )
        added = self.mw.col.added_notes[-1]
        self.assertEqual(added["Title"], "Imported (导入)")
        self.assertEqual(added["UUID"], "u")
        self.assertEqual(added["AllowNewCards"], "0")
        self.assertEqual(added.deck_id, 0)

    def test_import_mindmap_batch(self):
        il = import_plugin_module("backup.import_logic")
        model = {"name": "MindMap Master", "flds": [], "tmpls": []}
        self.mw.col = FakeCollection()
        calls = []

        def get_model():
            calls.append("get_model")
            return model

        count = il._import_mindmap_batch(self.mw, [{"title": "A"}, {"title": "B"}, "bad"], get_model)
        self.assertEqual(count, 2)
        self.assertEqual(len(calls), 1)

    def test_import_mindmaps_orchestration(self):
        il = import_plugin_module("backup.import_logic")
        import tempfile
        self.mw.col = FakeCollection()
        FakeFileDialog.open_filename = ""
        # no file selected -> should return without error
        il.import_mindmaps(self.mw, types.SimpleNamespace(preview=FakeWidget()), "en", lambda: None, lambda c: "")
        self.assertEqual(len(self.mw.col.added_notes), 0)

        # valid file selected
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False, encoding="utf-8") as f:
            json.dump({"mindmaps": [{"title": "X", "uuid": "u1", "data": {}}]}, f)
            name = f.name
        try:
            FakeFileDialog.open_filename = name
            preview = FakeWidget()
            il.import_mindmaps(
                self.mw,
                types.SimpleNamespace(preview=preview),
                "en",
                lambda: {"name": "M", "flds": [], "tmpls": []},
                lambda c: f"imported {c}",
            )
            self.assertEqual(len(self.mw.col.added_notes), 1)
            self.assertIn("imported 1", preview.html)
        finally:
            os.unlink(name)

    # ------------------------------------------------------------------
    # dialog_ui.py
    # ------------------------------------------------------------------
    def test_dialog_ui_initial_state(self):
        dui = import_plugin_module("backup.dialog_ui")
        dialog = dui.MindMapBackupDialog(self.mw)
        self.assertEqual(dialog.current_lang, "en")
        self.assertEqual(dialog.window_title, "Mind Map Backup & Recovery")
        self.assertEqual(dialog.size, (800, 600))

    def test_dialog_ui_switch_language(self):
        dui = import_plugin_module("backup.dialog_ui")
        dialog = dui.MindMapBackupDialog(self.mw)
        dialog.switch_language("cn")
        self.assertEqual(dialog.current_lang, "cn")
        self.assertEqual(self.mw.addonManager.config["backup_language"], "cn")
        dialog.switch_language("invalid")
        self.assertEqual(dialog.current_lang, "en")

    def test_dialog_ui_update_ui_text(self):
        dui = import_plugin_module("backup.dialog_ui")
        dialog = dui.MindMapBackupDialog(self.mw)
        dialog.update_ui_text()
        self.assertEqual(dialog.btn_close.text, "Close")
        self.assertIn("Mind Map Backup Tool", dialog.info.html)
        dialog.switch_language("cn")
        self.assertEqual(dialog.btn_close.text, "关闭")

    def test_dialog_ui_get_texts(self):
        dui = import_plugin_module("backup.dialog_ui")
        dialog = dui.MindMapBackupDialog(self.mw)
        self.assertEqual(dialog.get_english_text()["close"], "Close")
        self.assertEqual(dialog.get_chinese_text()["close"], "关闭")

    def test_dialog_ui_styles(self):
        dui = import_plugin_module("backup.dialog_ui")
        self.assertIn("#4CAF50", dui.BUTTON_ACTIVE_STYLE)
        self.assertIn("#28a745", dui.EXPORT_ALL_STYLE)


if __name__ == "__main__":
    unittest.main()
