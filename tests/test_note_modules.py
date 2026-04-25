import importlib
import json
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

    aqt = types.ModuleType("aqt")
    aqt.mw = fake_mw

    qt = types.ModuleType("aqt.qt")
    qt.QDialog = FakeWidget
    qt.QVBoxLayout = FakeWidget
    qt.QHBoxLayout = FakeWidget
    qt.QPushButton = FakeWidget
    qt.QTextEdit = FakeWidget
    qt.QTextBrowser = FakeWidget
    qt.QListWidget = FakeWidget
    qt.QFileDialog = FakeFileDialog

    utils = types.ModuleType("aqt.utils")
    utils.messages = []
    utils.tooltips = []
    utils.showInfo = lambda message: utils.messages.append(message)
    utils.tooltip = lambda message: utils.tooltips.append(message)
    utils.getText = lambda *args, **kwargs: ("", False)
    utils.askUser = lambda *args, **kwargs: False

    hooks = types.SimpleNamespace(
        reviewer_did_show_question=HookList(),
        reviewer_did_show_answer=HookList(),
        webview_did_receive_js_message=HookList(),
    )
    aqt.gui_hooks = hooks

    anki = types.ModuleType("anki")
    anki_models = types.ModuleType("anki.models")
    anki_models.NotetypeDict = dict

    sys.modules["aqt"] = aqt
    sys.modules["aqt.qt"] = qt
    sys.modules["aqt.utils"] = utils
    sys.modules["anki"] = anki
    sys.modules["anki.models"] = anki_models
    return fake_mw, utils, hooks


def import_plugin_module(name):
    if PACKAGE_NAME not in sys.modules:
        package = types.ModuleType(PACKAGE_NAME)
        package.__path__ = [str(ROOT)]
        sys.modules[PACKAGE_NAME] = package
    full_name = f"{PACKAGE_NAME}.{name}"
    sys.modules.pop(full_name, None)
    return importlib.import_module(full_name)


class TestNotesConfig(unittest.TestCase):
    def setUp(self):
        for key in list(sys.modules):
            if key.startswith(f"{PACKAGE_NAME}."):
                sys.modules.pop(key)

    def test_constants(self):
        config = import_plugin_module("notes.config")
        self.assertEqual(config.MODEL_NAME, "MindMap Master")
        self.assertEqual(config.FIELD_TITLE, "Title")
        self.assertEqual(config.FIELD_DATA, "Data")
        self.assertEqual(config.FIELD_DISPLAY_HTML, "DisplayHTML")
        self.assertEqual(config.FIELD_UUID, "UUID")
        self.assertEqual(config.FIELD_ALLOW_NEW_CARDS, "AllowNewCards")
        self.assertEqual(
            config.MODEL_FIELDS,
            ("Title", "Data", "DisplayHTML", "UUID", "AllowNewCards"),
        )
        self.assertEqual(config.CARD_TEMPLATE_NAME, "Card 1")
        self.assertEqual(config.CARD_TEMPLATE_QFMT, "{{Title}}<br>{{DisplayHTML}}")
        self.assertEqual(config.CARD_TEMPLATE_AFMT, "{{FrontSide}}")
        self.assertEqual(config.DEFAULT_ALLOW_NEW_CARDS, "1")
        self.assertEqual(config.DEFAULT_DECK_ID, 0)
        self.assertEqual(
            config.ALLOW_NEW_CARDS_MIGRATION_MESSAGE,
            "Added AllowNewCards field to existing MindMap Master model",
        )


class TestNotesModel(unittest.TestCase):
    def setUp(self):
        self.mw, self.utils, self.hooks = install_anki_stubs()
        FakeFileDialog.save_filename = ""
        FakeFileDialog.open_filename = ""
        for key in list(sys.modules):
            if key.startswith(f"{PACKAGE_NAME}."):
                sys.modules.pop(key)

    def test_get_or_create_mindmap_model_creates_new(self):
        model_module = import_plugin_module("notes.model")
        col = FakeCollection(models=FakeModels())

        model = model_module._get_or_create_mindmap_model(col)
        self.assertEqual(model["name"], "MindMap Master")
        self.assertEqual([field["name"] for field in model["flds"]], list(model_module.MODEL_FIELDS))
        self.assertEqual(len(model["tmpls"]), 1)
        self.assertEqual(model["tmpls"][0]["name"], "Card 1")
        self.assertEqual(model["tmpls"][0]["qfmt"], "{{Title}}<br>{{DisplayHTML}}")
        self.assertEqual(model["tmpls"][0]["afmt"], "{{FrontSide}}")
        self.assertEqual(col.models.added, [model])

    def test_get_or_create_mindmap_model_returns_existing(self):
        model_module = import_plugin_module("notes.model")
        existing = {"name": "MindMap Master", "flds": [{"name": "Title"}, {"name": "AllowNewCards"}], "tmpls": []}
        models = FakeModels(existing=existing)
        col = FakeCollection(models=models)

        model = model_module._get_or_create_mindmap_model(col)
        self.assertIs(model, existing)
        self.assertEqual(models.saved, [])
        self.assertEqual(models.added, [])

    def test_get_or_create_mindmap_model_migrates_missing_field(self):
        model_module = import_plugin_module("notes.model")
        existing = {"name": "MindMap Master", "flds": [{"name": "Title"}], "tmpls": []}
        models = FakeModels(existing=existing)
        col = FakeCollection(models=models)

        model = model_module._get_or_create_mindmap_model(col)
        self.assertIs(model, existing)
        self.assertIn({"name": "AllowNewCards"}, existing["flds"])
        self.assertEqual(models.saved, [existing])

    def test_model_has_field_true(self):
        model_module = import_plugin_module("notes.model")
        model = {"flds": [{"name": "Title"}, {"name": "Data"}]}
        self.assertTrue(model_module._model_has_field(model, "Data"))

    def test_model_has_field_false(self):
        model_module = import_plugin_module("notes.model")
        model = {"flds": [{"name": "Title"}]}
        self.assertFalse(model_module._model_has_field(model, "Data"))

    def test_model_has_field_empty(self):
        model_module = import_plugin_module("notes.model")
        model = {"flds": []}
        self.assertFalse(model_module._model_has_field(model, "Title"))

    def test_create_mindmap_model(self):
        model_module = import_plugin_module("notes.model")
        col = FakeCollection(models=FakeModels())

        model = model_module._create_mindmap_model(col)
        self.assertEqual(model["name"], "MindMap Master")
        self.assertEqual([f["name"] for f in model["flds"]], list(model_module.MODEL_FIELDS))
        self.assertEqual(len(model["tmpls"]), 1)
        self.assertEqual(model["tmpls"][0]["name"], "Card 1")
        self.assertEqual(model["tmpls"][0]["qfmt"], "{{Title}}<br>{{DisplayHTML}}")
        self.assertEqual(model["tmpls"][0]["afmt"], "{{FrontSide}}")
        self.assertEqual(col.models.added, [model])

    def test_ensure_mindmap_model_schema_adds_field_when_missing(self):
        model_module = import_plugin_module("notes.model")
        existing = {"name": "MindMap Master", "flds": [{"name": "Title"}], "tmpls": []}
        models = FakeModels(existing=existing)
        col = FakeCollection(models=models)

        model_module._ensure_mindmap_model_schema(col, existing)
        self.assertIn({"name": "AllowNewCards"}, existing["flds"])
        self.assertEqual(models.saved, [existing])

    def test_ensure_mindmap_model_schema_does_nothing_when_field_present(self):
        model_module = import_plugin_module("notes.model")
        existing = {"name": "MindMap Master", "flds": [{"name": "AllowNewCards"}], "tmpls": []}
        models = FakeModels(existing=existing)
        col = FakeCollection(models=models)

        model_module._ensure_mindmap_model_schema(col, existing)
        self.assertEqual(models.saved, [])
        self.assertEqual(models.added, [])

    def test_get_or_create_mindmap_model_uses_mw(self):
        model_module = import_plugin_module("notes.model")
        self.mw.col = FakeCollection(models=FakeModels())
        model = model_module.get_or_create_mindmap_model()
        self.assertEqual(model["name"], "MindMap Master")


class TestNoteManagerFacade(unittest.TestCase):
    def setUp(self):
        self.mw, self.utils, self.hooks = install_anki_stubs()
        FakeFileDialog.save_filename = ""
        FakeFileDialog.open_filename = ""
        for key in list(sys.modules):
            if key.startswith(f"{PACKAGE_NAME}."):
                sys.modules.pop(key)

    def test_constants_re_exported(self):
        note_manager = import_plugin_module("note_manager")
        self.assertEqual(note_manager.MODEL_NAME, "MindMap Master")
        self.assertEqual(note_manager.FIELD_TITLE, "Title")
        self.assertEqual(note_manager.FIELD_DATA, "Data")
        self.assertEqual(note_manager.FIELD_DISPLAY_HTML, "DisplayHTML")
        self.assertEqual(note_manager.FIELD_UUID, "UUID")
        self.assertEqual(note_manager.FIELD_ALLOW_NEW_CARDS, "AllowNewCards")
        self.assertEqual(
            note_manager.MODEL_FIELDS,
            ("Title", "Data", "DisplayHTML", "UUID", "AllowNewCards"),
        )
        self.assertEqual(note_manager.CARD_TEMPLATE_NAME, "Card 1")
        self.assertEqual(note_manager.CARD_TEMPLATE_QFMT, "{{Title}}<br>{{DisplayHTML}}")
        self.assertEqual(note_manager.CARD_TEMPLATE_AFMT, "{{FrontSide}}")
        self.assertEqual(note_manager.DEFAULT_ALLOW_NEW_CARDS, "1")
        self.assertEqual(note_manager.DEFAULT_DECK_ID, 0)
        self.assertEqual(
            note_manager.ALLOW_NEW_CARDS_MIGRATION_MESSAGE,
            "Added AllowNewCards field to existing MindMap Master model",
        )

    def test_model_functions_re_exported(self):
        note_manager = import_plugin_module("note_manager")
        expected_model_module = import_plugin_module("notes.model")
        self.assertEqual(note_manager.get_or_create_mindmap_model.__name__, expected_model_module.get_or_create_mindmap_model.__name__)
        self.assertEqual(note_manager._get_or_create_mindmap_model.__name__, expected_model_module._get_or_create_mindmap_model.__name__)
        self.assertEqual(note_manager._ensure_mindmap_model_schema.__name__, expected_model_module._ensure_mindmap_model_schema.__name__)
        self.assertEqual(note_manager._model_has_field.__name__, expected_model_module._model_has_field.__name__)
        self.assertEqual(note_manager._create_mindmap_model.__name__, expected_model_module._create_mindmap_model.__name__)

    def test_create_new_mindmap_note(self):
        note_manager = import_plugin_module("note_manager")
        col = FakeCollection(models=FakeModels())

        note_id = note_manager._create_new_mindmap_note(col, "Map A", "uuid-1")
        self.assertEqual(note_id, 999)
        added = col.added_notes[-1]
        self.assertEqual(added["Title"], "Map A")
        self.assertEqual(added["UUID"], "uuid-1")
        self.assertEqual(added["AllowNewCards"], "1")
        self.assertEqual(added.deck_id, 0)
        data = json.loads(added["Data"])
        self.assertEqual(data["meta"]["name"], "Map A")
        self.assertEqual(data["data"]["id"], "root")
        self.assertEqual(added["DisplayHTML"], "<h1>Map A</h1><p>(Open MindMap Editor to view)</p>")

    def test_create_new_mindmap_note_with_model(self):
        note_manager = import_plugin_module("note_manager")
        col = FakeCollection(models=FakeModels())
        model = col.models.new("MindMap Master")

        note_id = note_manager._create_new_mindmap_note_with_model(col, model, "Map B", "uuid-2")
        self.assertEqual(note_id, 999)
        added = col.added_notes[-1]
        self.assertEqual(added["Title"], "Map B")
        self.assertEqual(added["UUID"], "uuid-2")

    def test_populate_mindmap_note_fields(self):
        note_manager = import_plugin_module("note_manager")
        note = FakeNote(0)
        note_manager._populate_mindmap_note_fields(note, "Map C", "uuid-3")
        self.assertEqual(note["Title"], "Map C")
        self.assertEqual(note["UUID"], "uuid-3")
        self.assertEqual(note["AllowNewCards"], "1")
        data = json.loads(note["Data"])
        self.assertEqual(data["meta"]["name"], "Map C")
        self.assertEqual(data["data"]["id"], "root")
        self.assertEqual(note["DisplayHTML"], "<h1>Map C</h1><p>(Open MindMap Editor to view)</p>")

    def test_build_initial_mindmap_data(self):
        note_manager = import_plugin_module("note_manager")
        data = note_manager._build_initial_mindmap_data("My Map")
        self.assertEqual(data["meta"]["name"], "My Map")
        self.assertEqual(data["meta"]["author"], "anki")
        self.assertEqual(data["meta"]["version"], "0.2")
        self.assertEqual(data["format"], "node_tree")
        self.assertEqual(data["data"]["id"], "root")
        self.assertEqual(data["data"]["topic"], "My Map")

    def test_build_display_html(self):
        note_manager = import_plugin_module("note_manager")
        html = note_manager._build_display_html("Test Title")
        self.assertEqual(html, "<h1>Test Title</h1><p>(Open MindMap Editor to view)</p>")


if __name__ == "__main__":
    unittest.main()
