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
        # mimic anki note.fields attribute used by some code
        self.fields = list(fields.keys())

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


class FakeDB:
    def __init__(self, collection):
        self.collection = collection

    def list(self, query, *args):
        # Simulate "select id from notes where id in (...)"
        return [nid for nid in args if nid in self.collection.notes]


class FakeCollection:
    def __init__(self, notes=None, models=None):
        self.notes = notes or {}
        self.models = models or FakeModels()
        self.added_notes = []
        self.updated_notes = []
        self.removed_notes = []
        self.db = FakeDB(self)

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
        utils_factory=_utils_factory,
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


class TestUtilityFunctions(unittest.TestCase):
    def setUp(self):
        install_anki_stubs()
        for key in list(sys.modules):
            if key.startswith(f"{PACKAGE_NAME}."):
                sys.modules.pop(key)
        self.cl = import_plugin_module("card_linker")

    def test_extract_first_line_plain(self):
        self.assertEqual(self.cl.extract_first_line("Hello World"), "Hello World")

    def test_extract_first_line_with_br(self):
        self.assertEqual(self.cl.extract_first_line("Line1<br>Line2"), "Line1")

    def test_extract_first_line_with_html(self):
        self.assertEqual(self.cl.extract_first_line("<b>Hello</b> <i>World</i>"), "Hello World")

    def test_extract_first_line_empty(self):
        self.assertEqual(self.cl.extract_first_line(""), "")

    def test_find_node_by_id_root(self):
        root = {"id": "root", "children": []}
        self.assertIs(self.cl.find_node_by_id(root, "root"), root)

    def test_find_node_by_id_nested(self):
        child = {"id": "child"}
        root = {"id": "root", "children": [child]}
        self.assertIs(self.cl.find_node_by_id(root, "child"), child)

    def test_find_node_by_id_missing(self):
        root = {"id": "root", "children": []}
        self.assertIsNone(self.cl.find_node_by_id(root, "missing"))

    def test_build_node_index(self):
        child = {"id": "child", "children": [{"id": "grandchild"}]}
        root = {"id": "root", "children": [child]}
        index = self.cl.build_node_index(root)
        self.assertEqual(len(index), 3)
        self.assertIs(index["root"], root)
        self.assertIs(index["child"], child)
        self.assertEqual(index["grandchild"]["id"], "grandchild")

    def test_parse_mindmap_link_found(self):
        html = '<div id="mindmap-link" data-mid="123" data-nid="node_abc" style="display:none;"></div>'
        self.assertEqual(self.cl.parse_mindmap_link(html), (123, "node_abc"))

    def test_parse_mindmap_link_not_found(self):
        self.assertIsNone(self.cl.parse_mindmap_link("no link here"))

    def test_select_link_field_back(self):
        note = FakeNote(1, Front="Q", Back="A")
        self.assertEqual(self.cl.select_link_field(note), "Back")

    def test_select_link_field_back_extra(self):
        note = FakeNote(1, Front="Q", Back="A", Back_Extra="extra")
        # note keys are as passed; FakeNote keys() returns super().keys()
        # but we passed Back_Extra as kwarg, so key is "Back_Extra"
        self.assertEqual(self.cl.select_link_field(note), "Back")

    def test_select_link_field_extra(self):
        note = FakeNote(1, Front="Q", Extra="E")
        self.assertEqual(self.cl.select_link_field(note), "Extra")

    def test_select_link_field_fallback(self):
        note = FakeNote(1, Front="Q", Field2="A")
        self.assertEqual(self.cl.select_link_field(note), "Field2")

    def test_get_root_node_full_data(self):
        data = {"data": {"id": "root"}}
        self.assertEqual(self.cl.get_root_node(data), {"id": "root"})

    def test_get_root_node_raw(self):
        root = {"id": "root"}
        self.assertIs(self.cl.get_root_node(root), root)


class TestSyncCardToMindmap(unittest.TestCase):
    def setUp(self):
        self.mw, self.utils, self.hooks = install_anki_stubs()
        for key in list(sys.modules):
            if key.startswith(f"{PACKAGE_NAME}."):
                sys.modules.pop(key)
        self.cl = import_plugin_module("card_linker")

    def test_sync_no_link(self):
        note = FakeNote(1, Front="Hello")
        self.cl.sync_card_to_mindmap(note)
        self.assertEqual(len(self.mw.col.updated_notes), 0)

    def test_sync_updates_topic(self):
        mindmap = FakeNote(10, Title="Map", Data=json.dumps({"data": {"id": "root", "children": [{"id": "n1", "topic": "Old"}]}}))
        card = FakeNote(1, Front="New Topic", Back='<div id="mindmap-link" data-mid="10" data-nid="n1" style="display:none;"></div>')
        self.mw.col = FakeCollection(notes={10: mindmap})
        self.cl.sync_card_to_mindmap(card)
        self.assertEqual(len(self.mw.col.updated_notes), 1)
        updated_data = json.loads(self.mw.col.updated_notes[0]["Data"])
        self.assertEqual(updated_data["data"]["children"][0]["topic"], "New Topic")

    def test_sync_no_front_field(self):
        note = FakeNote(1, Back='<div id="mindmap-link" data-mid="10" data-nid="n1" style="display:none;"></div>')
        self.cl.sync_card_to_mindmap(note)
        self.assertEqual(len(self.mw.col.updated_notes), 0)

    def test_sync_prevents_loop(self):
        self.cl._sync_flags.syncing_from_node = True
        note = FakeNote(1, Front="Hello", Back='<div id="mindmap-link" data-mid="10" data-nid="n1" style="display:none;"></div>')
        self.cl.sync_card_to_mindmap(note)
        self.assertEqual(len(self.mw.col.updated_notes), 0)
        self.cl._sync_flags.syncing_from_node = False


class TestEditorLoadNote(unittest.TestCase):
    def setUp(self):
        self.mw, self.utils, self.hooks = install_anki_stubs()
        for key in list(sys.modules):
            if key.startswith(f"{PACKAGE_NAME}."):
                sys.modules.pop(key)
        self.cl = import_plugin_module("card_linker")

    def test_new_card_preserves_selection(self):
        editor = types.SimpleNamespace(note=FakeNote(0, Front="Q"), mindmap_selection={"id": 5, "title": "Map"}, web=types.SimpleNamespace(eval=lambda js: None), parentWindow=None)
        self.cl.on_editor_load_note(editor)
        self.assertEqual(editor.note.mindmap_selection["title"], "Map")

    def test_existing_card_valid_link(self):
        mindmap = FakeNote(10, Title="Map", Data=json.dumps({"data": {"id": "root", "children": [{"id": "n1"}]}}))
        card = FakeNote(1, Front="Q", Back='<div id="mindmap-link" data-mid="10" data-nid="n1" style="display:none;"></div>')
        self.mw.col = FakeCollection(notes={10: mindmap})
        editor = types.SimpleNamespace(note=card, web=types.SimpleNamespace(eval=lambda js: None), parentWindow=None)
        self.cl.on_editor_load_note(editor)
        self.assertEqual(editor.mindmap_selection["title"], "Map")

    def test_existing_card_deleted_mindmap(self):
        card = FakeNote(1, Front="Q", Back='<div id="mindmap-link" data-mid="99" data-nid="n1" style="display:none;"></div>')
        self.mw.col = FakeCollection(notes={})
        editor = types.SimpleNamespace(note=card, web=types.SimpleNamespace(eval=lambda js: None), parentWindow=None)
        self.cl.on_editor_load_note(editor)
        self.assertFalse(hasattr(editor, "mindmap_selection"))

    def test_existing_card_missing_node(self):
        mindmap = FakeNote(10, Title="Map", Data=json.dumps({"data": {"id": "root", "children": []}}))
        card = FakeNote(1, Front="Q", Back='<div id="mindmap-link" data-mid="10" data-nid="n1" style="display:none;"></div>')
        self.mw.col = FakeCollection(notes={10: mindmap})
        editor = types.SimpleNamespace(note=card, web=types.SimpleNamespace(eval=lambda js: None), parentWindow=None)
        self.cl.on_editor_load_note(editor)
        self.assertFalse(hasattr(editor, "mindmap_selection"))


class TestRemoveLinkFromCard(unittest.TestCase):
    def setUp(self):
        self.mw, self.utils, self.hooks = install_anki_stubs()
        for key in list(sys.modules):
            if key.startswith(f"{PACKAGE_NAME}."):
                sys.modules.pop(key)
        self.cl = import_plugin_module("card_linker")

    def test_removes_link(self):
        note = FakeNote(1, Front="Q", Back='<div id="mindmap-link" data-mid="10" data-nid="n1" style="display:none;"></div>')
        self.mw.col = FakeCollection()
        self.cl.remove_link_from_card(note, "Back")
        self.assertEqual(len(self.mw.col.updated_notes), 1)
        self.assertNotIn("mindmap-link", self.mw.col.updated_notes[0]["Back"])

    def test_no_link_no_update(self):
        note = FakeNote(1, Front="Q", Back="plain")
        self.cl.remove_link_from_card(note, "Back")
        self.assertEqual(len(self.mw.col.updated_notes), 0)


class TestClearMindmapSelection(unittest.TestCase):
    def setUp(self):
        self.mw, self.utils, self.hooks = install_anki_stubs()
        for key in list(sys.modules):
            if key.startswith(f"{PACKAGE_NAME}."):
                sys.modules.pop(key)
        self.cl = import_plugin_module("card_linker")

    def test_clears_selection_and_deletes_node(self):
        mindmap = FakeNote(10, Title="Map", Data=json.dumps({"data": {"id": "root", "children": [{"id": "n1", "topic": "T"}]}}))
        card = FakeNote(1, Front="Q", Back='<div id="mindmap-link" data-mid="10" data-nid="n1" style="display:none;"></div>')
        self.mw.col = FakeCollection(notes={10: mindmap})
        editor = types.SimpleNamespace(note=card, web=types.SimpleNamespace(eval=lambda js: None), parentWindow=None)
        self.cl.clear_mindmap_selection(editor)
        self.assertFalse(hasattr(editor, "mindmap_selection"))
        updated_data = json.loads(self.mw.col.updated_notes[0]["Data"])
        self.assertEqual(updated_data["data"]["children"], [])


class TestSpecialBoundaryInfo(unittest.TestCase):
    def setUp(self):
        install_anki_stubs()
        for key in list(sys.modules):
            if key.startswith(f"{PACKAGE_NAME}."):
                sys.modules.pop(key)
        self.cl = import_plugin_module("card_linker")

    def test_no_boundaries(self):
        self.assertIsNone(self.cl.get_special_boundary_info({"data": {"id": "root"}}))

    def test_special_boundary_found(self):
        data = {
            "data": {
                "id": "root",
                "children": [{"id": "n1"}],
                "boundaries": [{"isSpecial": True, "nodeIds": ["n1"]}],
            }
        }
        self.assertEqual(self.cl.get_special_boundary_info(data), ["n1"])

    def test_special_boundary_missing_node(self):
        data = {
            "data": {
                "id": "root",
                "children": [],
                "boundaries": [{"isSpecial": True, "nodeIds": ["n1"]}],
            }
        }
        self.assertIsNone(self.cl.get_special_boundary_info(data))

    def test_special_boundary_alternate_keys(self):
        data = {
            "boundaries": [{"is_special": True, "node_ids": ["n1"]}],
            "data": {"id": "root", "children": [{"id": "n1"}]},
        }
        self.assertEqual(self.cl.get_special_boundary_info(data), ["n1"])

    def test_non_dict_boundary_skipped(self):
        data = {
            "data": {
                "id": "root",
                "children": [{"id": "n1"}],
                "boundaries": ["bad", {"isSpecial": True, "nodeIds": ["n1"]}],
            }
        }
        self.assertEqual(self.cl.get_special_boundary_info(data), ["n1"])


class TestFindParentForNewNode(unittest.TestCase):
    def setUp(self):
        install_anki_stubs()
        for key in list(sys.modules):
            if key.startswith(f"{PACKAGE_NAME}."):
                sys.modules.pop(key)
        self.cl = import_plugin_module("card_linker")

    def test_no_special_uses_root(self):
        root = {"id": "root"}
        parent, idx = self.cl.find_parent_for_new_node({"data": root})
        self.assertIs(parent, root)

    def test_uses_special_node(self):
        child = {"id": "n1"}
        root = {"id": "root", "children": [child]}
        parent, idx = self.cl.find_parent_for_new_node({"data": root}, ["n1"])
        self.assertIs(parent, child)


class TestLinkExistingCardToMindmap(unittest.TestCase):
    def setUp(self):
        self.mw, self.utils, self.hooks = install_anki_stubs()
        for key in list(sys.modules):
            if key.startswith(f"{PACKAGE_NAME}."):
                sys.modules.pop(key)
        self.cl = import_plugin_module("card_linker")

    def test_create_new_node(self):
        mindmap = FakeNote(10, Title="Map", Data=json.dumps({"data": {"id": "root", "children": []}}))
        card = FakeNote(1, Front="Card Front", Back="A")
        self.mw.col = FakeCollection(notes={10: mindmap})
        self.cl.link_existing_card_to_mindmap(card, 10, "Map")
        self.assertEqual(len(self.mw.col.updated_notes), 2)  # mindmap + card
        data = json.loads(self.mw.col.updated_notes[0]["Data"])
        self.assertEqual(len(data["data"]["children"]), 1)
        self.assertEqual(data["data"]["children"][0]["topic"], "Card Front")
        self.assertIn("mindmap-link", self.mw.col.updated_notes[1]["Back"])

    def test_update_existing_node(self):
        mindmap = FakeNote(10, Title="Map", Data=json.dumps({"data": {"id": "root", "children": [{"id": "n1", "topic": "Old"}]}}))
        card = FakeNote(1, Front="New Front", Back='<div id="mindmap-link" data-mid="10" data-nid="n1" style="display:none;"></div>')
        self.mw.col = FakeCollection(notes={10: mindmap})
        self.cl.link_existing_card_to_mindmap(card, 10, "Map")
        self.assertEqual(len(self.mw.col.updated_notes), 1)  # only mindmap updated
        data = json.loads(self.mw.col.updated_notes[0]["Data"])
        self.assertEqual(data["data"]["children"][0]["topic"], "New Front")
        self.assertEqual(data["data"]["children"][0]["noteId"], 1)


class TestDeleteNodeFromMindmap(unittest.TestCase):
    def setUp(self):
        self.mw, self.utils, self.hooks = install_anki_stubs()
        for key in list(sys.modules):
            if key.startswith(f"{PACKAGE_NAME}."):
                sys.modules.pop(key)
        self.cl = import_plugin_module("card_linker")

    def test_deletes_node(self):
        mindmap = FakeNote(10, Title="Map", Data=json.dumps({"data": {"id": "root", "children": [{"id": "n1"}]}}))
        self.mw.col = FakeCollection(notes={10: mindmap})
        self.cl.delete_node_from_mindmap(10, "n1")
        self.assertEqual(len(self.mw.col.updated_notes), 1)
        data = json.loads(self.mw.col.updated_notes[0]["Data"])
        self.assertEqual(data["data"]["children"], [])

    def test_missing_mindmap_no_crash(self):
        self.mw.col = FakeCollection(notes={})
        self.cl.delete_node_from_mindmap(99, "n1")
        self.assertEqual(len(self.mw.col.updated_notes), 0)


class TestDeleteNodesFromMindmap(unittest.TestCase):
    def setUp(self):
        self.mw, self.utils, self.hooks = install_anki_stubs()
        for key in list(sys.modules):
            if key.startswith(f"{PACKAGE_NAME}."):
                sys.modules.pop(key)
        self.cl = import_plugin_module("card_linker")

    def test_delete_multiple_nodes(self):
        mindmap = FakeNote(10, Title="Map", Data=json.dumps({"data": {"id": "root", "children": [{"id": "n1"}, {"id": "n2", "children": [{"id": "n3"}]}]}}))
        self.mw.col = FakeCollection(notes={10: mindmap})
        self.cl.delete_nodes_from_mindmap(10, {"n1", "n3"})
        self.assertEqual(len(self.mw.col.updated_notes), 1)
        data = json.loads(self.mw.col.updated_notes[0]["Data"])
        children = data["data"]["children"]
        self.assertEqual(len(children), 1)
        self.assertEqual(children[0]["id"], "n2")
        self.assertEqual(children[0].get("children", []), [])

    def test_delete_empty_set_noop(self):
        mindmap = FakeNote(10, Title="Map", Data=json.dumps({"data": {"id": "root", "children": [{"id": "n1"}]}}))
        self.mw.col = FakeCollection(notes={10: mindmap})
        self.cl.delete_nodes_from_mindmap(10, set())
        self.assertEqual(len(self.mw.col.updated_notes), 0)

    def test_missing_mindmap_no_crash(self):
        self.mw.col = FakeCollection(notes={})
        self.cl.delete_nodes_from_mindmap(99, {"n1"})
        self.assertEqual(len(self.mw.col.updated_notes), 0)


class TestOnNoteAdded(unittest.TestCase):
    def setUp(self):
        self.mw, self.utils, self.hooks = install_anki_stubs()
        for key in list(sys.modules):
            if key.startswith(f"{PACKAGE_NAME}."):
                sys.modules.pop(key)
        self.cl = import_plugin_module("card_linker")

    def test_adds_node_and_link(self):
        mindmap = FakeNote(10, Title="Map", Data=json.dumps({"data": {"id": "root", "children": []}}))
        note = FakeNote(1, Front="New Card", Back="A")
        note.mindmap_selection = {"id": 10}
        self.mw.col = FakeCollection(notes={10: mindmap})
        self.cl.on_note_added(note)
        self.assertEqual(len(self.mw.col.updated_notes), 2)
        data = json.loads(self.mw.col.updated_notes[0]["Data"])
        self.assertEqual(len(data["data"]["children"]), 1)
        self.assertEqual(data["data"]["children"][0]["topic"], "New Card")
        self.assertIn("mindmap-link", self.mw.col.updated_notes[1]["Back"])

    def test_no_selection_noop(self):
        note = FakeNote(1, Front="Q", Back="A")
        self.cl.on_note_added(note)
        self.assertEqual(len(self.mw.col.updated_notes), 0)


class TestValidateAndCleanupMindmap(unittest.TestCase):
    def setUp(self):
        self.mw, self.utils, self.hooks = install_anki_stubs()
        for key in list(sys.modules):
            if key.startswith(f"{PACKAGE_NAME}."):
                sys.modules.pop(key)
        self.cl = import_plugin_module("card_linker")

    def test_removes_stale_noteid(self):
        mindmap = FakeNote(10, Title="Map", Data=json.dumps({"data": {"id": "root", "children": [{"id": "n1", "noteId": 99}]}}))
        self.mw.col = FakeCollection(notes={10: mindmap})
        self.cl.validate_and_cleanup_mindmap(mindmap)
        self.assertEqual(len(self.mw.col.updated_notes), 1)
        data = json.loads(self.mw.col.updated_notes[0]["Data"])
        self.assertNotIn("noteId", data["data"]["children"][0])

    def test_keeps_valid_noteid(self):
        existing = FakeNote(99, Front="Q")
        mindmap = FakeNote(10, Title="Map", Data=json.dumps({"data": {"id": "root", "children": [{"id": "n1", "noteId": 99}]}}))
        self.mw.col = FakeCollection(notes={10: mindmap, 99: existing})
        self.cl.validate_and_cleanup_mindmap(mindmap)
        self.assertEqual(len(self.mw.col.updated_notes), 0)


class TestOnNotesWillBeDeleted(unittest.TestCase):
    def setUp(self):
        self.mw, self.utils, self.hooks = install_anki_stubs()
        for key in list(sys.modules):
            if key.startswith(f"{PACKAGE_NAME}."):
                sys.modules.pop(key)
        self.cl = import_plugin_module("card_linker")

    def test_deletes_linked_node(self):
        mindmap = FakeNote(10, Title="Map", Data=json.dumps({"data": {"id": "root", "children": [{"id": "n1"}]}}))
        card = FakeNote(1, Front="Q", Back='<div id="mindmap-link" data-mid="10" data-nid="n1" style="display:none;"></div>')
        self.mw.col = FakeCollection(notes={10: mindmap, 1: card})
        self.cl.on_notes_will_be_deleted(self.mw.col, [1])
        self.assertEqual(len(self.mw.col.updated_notes), 1)
        data = json.loads(self.mw.col.updated_notes[0]["Data"])
        self.assertEqual(data["data"]["children"], [])

    def test_batch_deletes_multiple_nodes_same_map(self):
        mindmap = FakeNote(10, Title="Map", Data=json.dumps({"data": {"id": "root", "children": [{"id": "n1"}, {"id": "n2"}]}}))
        card1 = FakeNote(1, Front="Q", Back='<div id="mindmap-link" data-mid="10" data-nid="n1" style="display:none;"></div>')
        card2 = FakeNote(2, Front="Q", Back='<div id="mindmap-link" data-mid="10" data-nid="n2" style="display:none;"></div>')
        self.mw.col = FakeCollection(notes={10: mindmap, 1: card1, 2: card2})
        self.cl.on_notes_will_be_deleted(self.mw.col, [1, 2])
        self.assertEqual(len(self.mw.col.updated_notes), 1)
        data = json.loads(self.mw.col.updated_notes[0]["Data"])
        self.assertEqual(data["data"]["children"], [])


class TestAddEditorButton(unittest.TestCase):
    def setUp(self):
        self.mw, self.utils, self.hooks = install_anki_stubs()
        for key in list(sys.modules):
            if key.startswith(f"{PACKAGE_NAME}."):
                sys.modules.pop(key)
        self.cl = import_plugin_module("card_linker")

    def test_adds_button(self):
        editor = types.SimpleNamespace(addButton=lambda **kwargs: kwargs, web=types.SimpleNamespace(eval=lambda js: None))
        buttons = []
        result = self.cl.add_editor_button(buttons, editor)
        self.assertEqual(len(result), 1)
        self.assertTrue(hasattr(editor, '_mindmap_btn_added'))


class TestResetAndUpdateMindmapButton(unittest.TestCase):
    def setUp(self):
        self.mw, self.utils, self.hooks = install_anki_stubs()
        for key in list(sys.modules):
            if key.startswith(f"{PACKAGE_NAME}."):
                sys.modules.pop(key)
        self.cl = import_plugin_module("card_linker")

    def test_reset_button_evals_js(self):
        calls = []
        editor = types.SimpleNamespace(web=types.SimpleNamespace(eval=lambda js: calls.append(js)))
        self.cl.reset_mindmap_button(editor)
        self.assertEqual(len(calls), 1)
        self.assertIn("mindmap_link_btn", calls[0])

    def test_update_button_evals_js(self):
        calls = []
        editor = types.SimpleNamespace(web=types.SimpleNamespace(eval=lambda js: calls.append(js)))
        self.cl.update_mindmap_button(editor, "My Map")
        self.assertEqual(len(calls), 1)
        self.assertIn("My Map", calls[0])


class TestRegexConstants(unittest.TestCase):
    def setUp(self):
        install_anki_stubs()
        for key in list(sys.modules):
            if key.startswith(f"{PACKAGE_NAME}."):
                sys.modules.pop(key)
        self.cl = import_plugin_module("card_linker")

    def test_mindmap_link_re_compiled(self):
        self.assertTrue(hasattr(self.cl, "MINDMAP_LINK_RE"))
        m = self.cl.MINDMAP_LINK_RE.search('<div id="mindmap-link" data-mid="1" data-nid="a" style="display:none;"></div>')
        self.assertIsNotNone(m)
        self.assertEqual(m.group(1), "1")
        self.assertEqual(m.group(2), "a")

    def test_data_mid_re_compiled(self):
        self.assertTrue(hasattr(self.cl, "DATA_MID_RE"))
        m = self.cl.DATA_MID_RE.search('data-mid="42"')
        self.assertIsNotNone(m)
        self.assertEqual(m.group(1), "42")


if __name__ == "__main__":
    unittest.main()
