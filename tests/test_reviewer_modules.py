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


class TestReviewerJs(unittest.TestCase):
    def setUp(self):
        install_anki_stubs()
        for key in list(sys.modules):
            if key.startswith(f"{PACKAGE_NAME}."):
                sys.modules.pop(key)

    def test_clear_indicator_js_contains_id(self):
        js = import_plugin_module("reviewer.js")
        self.assertIn("mindmap-indicator", js.CLEAR_INDICATOR_JS)
        self.assertIn("existing.remove()", js.CLEAR_INDICATOR_JS)

    def test_build_indicator_js_escapes_quotes(self):
        js = import_plugin_module("reviewer.js")
        out = js._build_indicator_js('Title "quoted"', "open_mindmap:2:node:1")
        self.assertIn("mindmap-indicator", out)
        self.assertIn('Title \\"quoted\\"', out)
        self.assertIn('pycmd("open_mindmap:2:node:1")', out)

    def test_build_indicator_js_empty_title(self):
        js = import_plugin_module("reviewer.js")
        out = js._build_indicator_js("", "")
        self.assertIn('if ("" === "")', out)
        self.assertIn("existing.remove()", out)

    def test_build_indicator_js_newlines_replaced(self):
        js = import_plugin_module("reviewer.js")
        out = js._build_indicator_js("Line1\nLine2", "param")
        self.assertIn("Line1 Line2", out)


class TestReviewerLinkResolver(unittest.TestCase):
    def setUp(self):
        self.mw, self.utils, self.hooks = install_anki_stubs()
        for key in list(sys.modules):
            if key.startswith(f"{PACKAGE_NAME}."):
                sys.modules.pop(key)

    def test_find_mindmap_link_found(self):
        lr = import_plugin_module("reviewer.link_resolver")
        note = FakeNote(1, Front='<span class="mindmap-link" data-mid="2" data-nid="node:1"></span>')
        self.assertEqual(lr._find_mindmap_link(note), ("Front", 2, "node:1"))

    def test_find_mindmap_link_no_link(self):
        lr = import_plugin_module("reviewer.link_resolver")
        note = FakeNote(1, Front="plain text")
        self.assertIsNone(lr._find_mindmap_link(note))

    def test_find_mindmap_link_missing_nid(self):
        lr = import_plugin_module("reviewer.link_resolver")
        note = FakeNote(1, Front='<span class="mindmap-link" data-mid="5"></span>')
        self.assertEqual(lr._find_mindmap_link(note), ("Front", 5, None))

    def test_node_exists_root(self):
        lr = import_plugin_module("reviewer.link_resolver")
        self.assertTrue(lr._node_exists({"id": "root"}, "root"))

    def test_node_exists_child(self):
        lr = import_plugin_module("reviewer.link_resolver")
        tree = {"id": "root", "children": [{"id": "x"}, {"id": "y"}]}
        self.assertTrue(lr._node_exists(tree, "x"))
        self.assertTrue(lr._node_exists(tree, "y"))
        self.assertFalse(lr._node_exists(tree, "z"))

    def test_node_exists_nested(self):
        lr = import_plugin_module("reviewer.link_resolver")
        tree = {"id": "root", "children": [{"id": "a", "children": [{"id": "b"}]}]}
        self.assertTrue(lr._node_exists(tree, "b"))
        self.assertFalse(lr._node_exists(tree, "c"))

    def test_node_exists_non_dict_skipped(self):
        lr = import_plugin_module("reviewer.link_resolver")
        tree = {"id": "root", "children": [None, "bad", {"id": "ok"}]}
        self.assertTrue(lr._node_exists(tree, "ok"))

    def test_resolve_mindmap_link_success(self):
        lr = import_plugin_module("reviewer.link_resolver")
        mm_note = FakeNote(2, Title='Title "quoted"', Data=json.dumps({"data": {"id": "root", "children": [{"id": "node:1"}]}}))
        self.mw.col = FakeCollection(notes={2: mm_note})
        title, cleanup = lr._resolve_mindmap_link(2, "node:1")
        self.assertEqual(title, 'Title "quoted"')
        self.assertFalse(cleanup)

    def test_resolve_mindmap_link_missing_note(self):
        lr = import_plugin_module("reviewer.link_resolver")
        self.mw.col = FakeCollection(notes={})
        title, cleanup = lr._resolve_mindmap_link(99, "node:1")
        self.assertIsNone(title)
        self.assertFalse(cleanup)

    def test_resolve_mindmap_link_missing_node(self):
        lr = import_plugin_module("reviewer.link_resolver")
        mm_note = FakeNote(2, Title="Map", Data=json.dumps({"data": {"id": "root"}}))
        self.mw.col = FakeCollection(notes={2: mm_note})
        title, cleanup = lr._resolve_mindmap_link(2, "missing")
        self.assertEqual(title, "Map")
        self.assertTrue(cleanup)

    def test_resolve_mindmap_link_bad_json(self):
        lr = import_plugin_module("reviewer.link_resolver")
        mm_note = FakeNote(2, Title="Map", Data="not json")
        self.mw.col = FakeCollection(notes={2: mm_note})
        title, cleanup = lr._resolve_mindmap_link(2, "node:1")
        self.assertEqual(title, "Map")
        self.assertFalse(cleanup)


class TestReviewerRenderer(unittest.TestCase):
    def setUp(self):
        self.mw, self.utils, self.hooks = install_anki_stubs()
        for key in list(sys.modules):
            if key.startswith(f"{PACKAGE_NAME}."):
                sys.modules.pop(key)

    def test_build_pycmd_param_with_node(self):
        r = import_plugin_module("reviewer.renderer")
        self.assertEqual(r._build_pycmd_param(2, "node:1", "Map"), "open_mindmap:2:node:1")

    def test_build_pycmd_param_without_node(self):
        r = import_plugin_module("reviewer.renderer")
        self.assertEqual(r._build_pycmd_param(2, None, "Map"), "open_mindmap:2")

    def test_build_pycmd_param_empty_title(self):
        r = import_plugin_module("reviewer.renderer")
        self.assertEqual(r._build_pycmd_param(2, "node:1", ""), "")

    def test_build_pycmd_param_empty_id(self):
        r = import_plugin_module("reviewer.renderer")
        self.assertEqual(r._build_pycmd_param(0, "node:1", "Map"), "")

    def test_render_indicator_clear_when_no_title(self):
        r = import_plugin_module("reviewer.renderer")
        calls = []

        class Web:
            def eval(self, js):
                calls.append(js)

        self.mw.reviewer = types.SimpleNamespace(web=Web())
        r._render_indicator("")
        self.assertEqual(len(calls), 1)
        self.assertIn("existing.remove()", calls[0])

    def test_render_indicator_builds_js(self):
        r = import_plugin_module("reviewer.renderer")
        calls = []

        class Web:
            def eval(self, js):
                calls.append(js)

        self.mw.reviewer = types.SimpleNamespace(web=Web())
        r._render_indicator("My Map", "open_mindmap:3:n2")
        self.assertEqual(len(calls), 1)
        self.assertIn("mindmap-indicator", calls[0])
        self.assertIn("My Map", calls[0])
        self.assertIn("open_mindmap:3:n2", calls[0])

    def test_render_indicator_no_reviewer(self):
        r = import_plugin_module("reviewer.renderer")
        self.mw.reviewer = None
        # should not raise
        r._render_indicator("Map", "param")

    def test_render_indicator_no_web(self):
        r = import_plugin_module("reviewer.renderer")
        self.mw.reviewer = types.SimpleNamespace(web=None)
        # should not raise
        r._render_indicator("Map", "param")


class TestReviewIndicatorFacade(unittest.TestCase):
    def setUp(self):
        self.mw, self.utils, self.hooks = install_anki_stubs()
        FakeFileDialog.save_filename = ""
        FakeFileDialog.open_filename = ""
        for key in list(sys.modules):
            if key.startswith(f"{PACKAGE_NAME}."):
                sys.modules.pop(key)

    def test_facade_reexports(self):
        ri = import_plugin_module("review_indicator")
        # Ensure all expected names are accessible
        self.assertTrue(callable(ri._find_mindmap_link))
        self.assertTrue(callable(ri._node_exists))
        self.assertTrue(callable(ri._resolve_mindmap_link))
        self.assertTrue(callable(ri._build_indicator_js))
        self.assertTrue(callable(ri.show_mindmap_indicator))
        self.assertTrue(callable(ri.on_reviewer_pycmd))
        self.assertTrue(callable(ri._build_pycmd_param))
        self.assertTrue(callable(ri._render_indicator))
        self.assertIn("mindmap-indicator", ri.CLEAR_INDICATOR_JS)

    def test_show_mindmap_indicator_no_reviewer(self):
        ri = import_plugin_module("review_indicator")
        self.mw.reviewer = None
        # should not raise
        ri.show_mindmap_indicator()

    def test_show_mindmap_indicator_no_link(self):
        ri = import_plugin_module("review_indicator")
        calls = []

        class Web:
            def eval(self, js):
                calls.append(js)

        class Card:
            def note(self):
                return FakeNote(1, Front="plain")

        self.mw.reviewer = types.SimpleNamespace(card=Card(), web=Web())
        ri.show_mindmap_indicator()
        self.assertEqual(len(calls), 1)
        self.assertIn("existing.remove()", calls[0])

    def test_show_mindmap_indicator_with_link(self):
        ri = import_plugin_module("review_indicator")
        calls = []

        class Web:
            def eval(self, js):
                calls.append(js)

        class Card:
            def note(self):
                return FakeNote(1, Front='<span class="mindmap-link" data-mid="2" data-nid="node:1"></span>')

        mm_note = FakeNote(2, Title="Map", Data=json.dumps({"data": {"id": "root", "children": [{"id": "node:1"}]}}))
        self.mw.reviewer = types.SimpleNamespace(card=Card(), web=Web())
        self.mw.col = FakeCollection(notes={2: mm_note})

        ri.show_mindmap_indicator()
        self.assertEqual(len(calls), 1)
        self.assertIn("Map", calls[0])
        self.assertIn("open_mindmap:2:node:1", calls[0])

    def test_show_mindmap_indicator_cleanup_missing_node(self):
        ri = import_plugin_module("review_indicator")
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

        ri.show_mindmap_indicator()
        self.assertEqual(len(card_linker.removed), 1)
        self.assertIn("existing.remove()", calls[-1])
        self.assertNotIn("document.createElement('div')", calls[-1])

    def test_on_reviewer_pycmd_opens_mindmap(self):
        ri = import_plugin_module("review_indicator")
        opened = []

        mindmap_opener = types.ModuleType(f"{PACKAGE_NAME}.mindmap_opener")
        mindmap_opener.open_mindmap = lambda mid, nid: opened.append((mid, nid))
        sys.modules[f"{PACKAGE_NAME}.mindmap_opener"] = mindmap_opener

        result = ri.on_reviewer_pycmd((False, None), "open_mindmap:7:node:3", None)
        self.assertEqual(result, (True, None))
        self.assertEqual(opened, [(7, "node:3")])

    def test_on_reviewer_pycmd_ignores_other(self):
        ri = import_plugin_module("review_indicator")
        handled = (False, None)
        result = ri.on_reviewer_pycmd(handled, "some_other_cmd", None)
        self.assertEqual(result, handled)


if __name__ == "__main__":
    unittest.main()
