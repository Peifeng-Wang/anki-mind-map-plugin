import importlib
import json
import os
import sys
import tempfile
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
        include_input_helpers=True,
    )
    return fake_mw, utils, hooks


def import_plugin_module(name):
    if PACKAGE_NAME not in sys.modules:
        package = types.ModuleType(PACKAGE_NAME)
        package.__path__ = [str(ROOT)]
        sys.modules[PACKAGE_NAME] = package
    full_name = f"{PACKAGE_NAME}.{name}"
    sys.modules.pop(full_name, None)
    return importlib.import_module(full_name)


class PythonRefactorTests(unittest.TestCase):
    def setUp(self):
        self.mw, self.utils, self.hooks = install_anki_stubs()
        FakeFileDialog.save_filename = ""
        FakeFileDialog.open_filename = ""
        for key in list(sys.modules):
            if key.startswith(f"{PACKAGE_NAME}."):
                sys.modules.pop(key)

    def test_note_manager_model_creation_and_note_payload(self):
        model_module = import_plugin_module("notes.model")
        creation = import_plugin_module("notes.creation")
        config = import_plugin_module("notes.config")
        col = FakeCollection(models=FakeModels())

        model = model_module._get_or_create_mindmap_model(col)
        self.assertEqual([field["name"] for field in model["flds"]], list(config.MODEL_FIELDS))
        self.assertEqual(model["tmpls"][0]["name"], "Card 1")
        self.assertEqual(model["tmpls"][0]["qfmt"], "{{Title}}<br>{{DisplayHTML}}")

        note_id = creation._create_new_mindmap_note(col, "Map A", "uuid-1")
        self.assertEqual(note_id, 999)
        added = col.added_notes[-1]
        self.assertEqual(added["Title"], "Map A")
        self.assertEqual(added["UUID"], "uuid-1")
        self.assertEqual(added["AllowNewCards"], "1")
        self.assertEqual(added.deck_id, 0)
        data = json.loads(added["Data"])
        self.assertEqual(data["meta"]["name"], "Map A")
        self.assertEqual(data["data"]["id"], "root")

    def test_note_manager_existing_model_migration(self):
        model_module = import_plugin_module("notes.model")
        existing = {"name": "MindMap Master", "flds": [{"name": "Title"}], "tmpls": []}
        models = FakeModels(existing=existing)
        col = FakeCollection(models=models)

        model = model_module._get_or_create_mindmap_model(col)
        self.assertIs(model, existing)
        self.assertIn({"name": "AllowNewCards"}, existing["flds"])
        self.assertEqual(models.saved, [existing])

    def test_export_utils_single_and_all_export(self):
        export_mindmap = import_plugin_module("export.export_mindmap")
        export_all = import_plugin_module("export.export_all_mindmaps")
        note = FakeNote(1, Title="Map A", UUID="u1", Data=json.dumps({"data": {"id": "root"}}))
        self.mw.col = FakeCollection(notes={1: note})

        with tempfile.TemporaryDirectory() as tmpdir:
            filename = os.path.join(tmpdir, "single.json")
            FakeFileDialog.save_filename = filename
            success, saved, viewer = export_mindmap.export_mindmap_to_json(None, self.mw, 1)
            self.assertTrue(success)
            self.assertEqual(saved, filename)
            self.assertEqual(viewer, os.path.join(tmpdir, "MindMap_Viewer.html"))
            self.assertTrue(os.path.exists(viewer))
            with open(filename, encoding="utf-8") as f:
                payload = json.load(f)
            self.assertEqual(payload["title"], "Map A")
            self.assertEqual(payload["allow_new_cards"], "1")

            filename_all = os.path.join(tmpdir, "all.json")
            FakeFileDialog.save_filename = filename_all
            success, saved, viewer, count = export_all.export_all_mindmaps(None, self.mw)
            self.assertTrue(success)
            self.assertEqual(count, 1)
            with open(saved, encoding="utf-8") as f:
                payload = json.load(f)
            self.assertEqual(payload["mindmaps"][0]["note_id"], 1)

    def test_review_indicator_helpers_and_rendering(self):
        review_indicator = import_plugin_module("review_indicator")
        link_note = FakeNote(1, Front='<span class="mindmap-link" data-mid="2" data-nid="node:1"></span>')
        mm_note = FakeNote(2, Title='Title "quoted"', Data=json.dumps({"data": {"id": "root", "children": [{"id": "node:1"}]}}))
        self.mw.col = FakeCollection(notes={2: mm_note})

        self.assertEqual(review_indicator._find_mindmap_link(link_note), ("Front", 2, "node:1"))
        self.assertTrue(review_indicator._node_exists({"id": "root", "children": [{"id": "x"}]}, "x"))
        title, cleanup = review_indicator._resolve_mindmap_link(2, "node:1")
        self.assertEqual(title, 'Title "quoted"')
        self.assertFalse(cleanup)

        js = review_indicator._build_indicator_js('Title "quoted"', "open_mindmap:2:node:1")
        self.assertIn("mindmap-indicator", js)
        self.assertIn('Title \\"quoted\\"', js)
        self.assertIn('pycmd("open_mindmap:2:node:1")', js)

    def test_review_indicator_show_removes_stale_indicator_on_deleted_node(self):
        review_indicator = import_plugin_module("review_indicator")
        calls = []

        class Web:
            def eval(self, js):
                calls.append(js)

        class Card:
            def note(self):
                return FakeNote(1, Front='<span class="mindmap-link" data-mid="2" data-nid="missing"></span>')

        self.mw.reviewer = types.SimpleNamespace(card=Card(), web=Web())
        self.mw.col = FakeCollection(notes={2: FakeNote(2, Title="Map", Data=json.dumps({"data": {"id": "root"}}))})
        card_linker = types.ModuleType(f"{PACKAGE_NAME}.card_linker")
        card_linker.removed = []
        card_linker.remove_link_from_card = lambda note, field: card_linker.removed.append((note, field))
        sys.modules[f"{PACKAGE_NAME}.card_linker"] = card_linker
        sys.modules[PACKAGE_NAME].card_linker = card_linker

        review_indicator.show_mindmap_indicator()
        self.assertEqual(len(card_linker.removed), 1)
        self.assertIn("existing.remove()", calls[-1])
        self.assertNotIn("document.createElement('div')", calls[-1])

    def test_mindmap_manager_helpers_preserve_selection_and_node_removal(self):
        mindmap_editor = types.ModuleType(f"{PACKAGE_NAME}.mindmap_editor")
        mindmap_editor.MindMapDialog = types.SimpleNamespace(open_instance=lambda *args: None)
        sys.modules[f"{PACKAGE_NAME}.mindmap_editor"] = mindmap_editor
        mindmap_manager = import_plugin_module("mindmap_manager")
        manager = mindmap_manager.MindMapManager(self.mw)
        manager.notes = [("A", 1)]
        manager.list_widget.setCurrentRow(3)
        self.assertIsNone(manager.get_selected_nid())

        data = {"data": {"id": "root", "children": [{"id": "child"}, {"id": "keep"}]}}
        manager._remove_linked_node(data, "child")
        self.assertEqual(data["data"]["children"], [{"id": "keep"}])

    def test_backup_dialog_extract_import_and_preview_escaping(self):
        model_module = import_plugin_module("notes.model")
        backup = import_plugin_module("backup.dialog_ui")
        from_extract = import_plugin_module("backup.import_logic")
        from_preview = import_plugin_module("backup.export_preview")
        model = {"name": "MindMap Master", "flds": [], "tmpls": []}
        model_module.get_or_create_mindmap_model = lambda: model
        self.mw.col = FakeCollection()

        dialog = backup.MindMapBackupDialog(self.mw)
        self.assertEqual(dialog._extract_mindmaps({"mindmaps": [{"title": "A"}]}), [{"title": "A"}])
        self.assertEqual(dialog._extract_mindmaps({"title": "Single"}), [{"title": "Single"}])
        self.assertEqual(dialog._extract_mindmaps([]), [])

        from_extract._import_one_mindmap(
            self.mw,
            {"title": "Imported", "uuid": "u", "data": {"data": {}}, "allow_new_cards": "0"},
            model,
        )
        added = self.mw.col.added_notes[-1]
        self.assertEqual(added["Title"], "Imported (导入)")
        self.assertEqual(added["AllowNewCards"], "0")
        self.assertEqual(added.deck_id, 0)

        preview = from_preview._format_export_selected_preview("<bad>.json", None, "<script>")
        self.assertIn("&lt;script&gt;", preview)

    def test_usage_guide_language_and_content_contract(self):
        usage = import_plugin_module("usage_guide")
        dialog = usage.UsageDialog(self.mw)
        dialog.switch_language("cn")
        self.assertEqual(self.mw.addonManager.config["guide_language"], "cn")
        self.assertIn("中文", dialog.btn_cn.text)
        self.assertIn("#quick-start", dialog.get_chinese_content())
        self.assertIn('id="backup"', dialog.get_english_content())
        dialog.switch_language("invalid")
        self.assertEqual(dialog.current_lang, "en")


if __name__ == "__main__":
    unittest.main()
