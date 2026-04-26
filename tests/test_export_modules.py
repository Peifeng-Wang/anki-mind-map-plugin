import importlib
import json
import os
import sys
import types
import tempfile
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


class TestExportModules(unittest.TestCase):
    def setUp(self):
        self.mw, self.utils, self.hooks = install_anki_stubs()
        FakeFileDialog.save_filename = ""
        FakeFileDialog.open_filename = ""
        for key in list(sys.modules):
            if key.startswith(f"{PACKAGE_NAME}."):
                sys.modules.pop(key)

    # ------------------------------------------------------------------
    # export/note_data
    # ------------------------------------------------------------------
    def test_get_optional_note_field_present(self):
        note_data = import_plugin_module("export.note_data")
        note = FakeNote(1, Title="Map A")
        self.assertEqual(note_data._get_optional_note_field(note, "Title", "default"), "Map A")

    def test_get_optional_note_field_missing(self):
        note_data = import_plugin_module("export.note_data")
        note = FakeNote(1, Title="Map A")
        self.assertEqual(note_data._get_optional_note_field(note, "Missing", "default"), "default")

    def test_get_note_data_with_data(self):
        note_data = import_plugin_module("export.note_data")
        note = FakeNote(1, Data=json.dumps({"key": "value"}))
        self.assertEqual(note_data._get_note_data(note), {"key": "value"})

    def test_get_note_data_empty(self):
        note_data = import_plugin_module("export.note_data")
        note = FakeNote(1, Data="")
        self.assertEqual(note_data._get_note_data(note), {})

    def test_build_mindmap_info_defaults(self):
        note_data = import_plugin_module("export.note_data")
        note = FakeNote(1, Title="Map A", UUID="u1", Data=json.dumps({"k": "v"}), AllowNewCards="1")
        info = note_data._build_mindmap_info(note)
        self.assertEqual(info["title"], "Map A")
        self.assertEqual(info["uuid"], "u1")
        self.assertEqual(info["data"], {"k": "v"})
        self.assertEqual(info["allow_new_cards"], "1")
        self.assertNotIn("note_id", info)

    def test_build_mindmap_info_with_title_and_note_id(self):
        note_data = import_plugin_module("export.note_data")
        note = FakeNote(1, Title="Map A", UUID="u1", Data="", AllowNewCards="0")
        info = note_data._build_mindmap_info(note, title="Custom", note_id=99)
        self.assertEqual(info["title"], "Custom")
        self.assertEqual(info["note_id"], 99)
        self.assertEqual(info["allow_new_cards"], "0")

    def test_build_mindmap_info_missing_fields(self):
        note_data = import_plugin_module("export.note_data")
        note = FakeNote(1, Title="Map A", Data="")
        info = note_data._build_mindmap_info(note)
        self.assertEqual(info["uuid"], "")
        self.assertEqual(info["allow_new_cards"], "1")

    # ------------------------------------------------------------------
    # export/file_io
    # ------------------------------------------------------------------
    def test_get_documents_path(self):
        file_io = import_plugin_module("export.file_io")
        path = file_io._get_documents_path("test.json")
        self.assertTrue(path.endswith(os.path.join("Documents", "test.json")))

    def test_write_json_file(self):
        file_io = import_plugin_module("export.file_io")
        with tempfile.TemporaryDirectory() as tmpdir:
            filepath = os.path.join(tmpdir, "out.json")
            file_io._write_json_file(filepath, {"a": 1})
            with open(filepath, encoding="utf-8") as f:
                data = json.load(f)
            self.assertEqual(data, {"a": 1})

    def test_viewer_copy_is_current_same_file(self):
        file_io = import_plugin_module("export.file_io")
        with tempfile.TemporaryDirectory() as tmpdir:
            src = os.path.join(tmpdir, "src.html")
            with open(src, "w", encoding="utf-8") as f:
                f.write("hello")
            self.assertTrue(file_io._viewer_copy_is_current(src, src))

    def test_viewer_copy_is_current_different_content(self):
        file_io = import_plugin_module("export.file_io")
        with tempfile.TemporaryDirectory() as tmpdir:
            src = os.path.join(tmpdir, "src.html")
            dst = os.path.join(tmpdir, "dst.html")
            with open(src, "w", encoding="utf-8") as f:
                f.write("hello")
            with open(dst, "w", encoding="utf-8") as f:
                f.write("world")
            self.assertFalse(file_io._viewer_copy_is_current(src, dst))

    def test_viewer_copy_is_current_missing_dest(self):
        file_io = import_plugin_module("export.file_io")
        with tempfile.TemporaryDirectory() as tmpdir:
            src = os.path.join(tmpdir, "src.html")
            with open(src, "w", encoding="utf-8") as f:
                f.write("hello")
            self.assertFalse(file_io._viewer_copy_is_current(src, os.path.join(tmpdir, "nope.html")))

    def test_copy_standalone_viewer_creates_file(self):
        file_io = import_plugin_module("export.file_io")
        with tempfile.TemporaryDirectory() as tmpdir:
            # create fake viewer source in web/standalone_viewer.html
            web_dir = os.path.join(tmpdir, "web")
            os.makedirs(web_dir)
            src = os.path.join(web_dir, "standalone_viewer.html")
            with open(src, "w", encoding="utf-8") as f:
                f.write("<html></html>")

            # patch __file__ to point inside tmpdir so addon_dir resolves to tmpdir
            orig_file = file_io.__file__
            try:
                file_io.__file__ = os.path.join(tmpdir, "export", "file_io.py")
                export_file = os.path.join(tmpdir, "export.json")
                result = file_io._copy_standalone_viewer(export_file)
                expected = os.path.join(tmpdir, "MindMap_Viewer.html")
                self.assertEqual(result, expected)
                self.assertTrue(os.path.exists(expected))
            finally:
                file_io.__file__ = orig_file

    def test_copy_standalone_viewer_returns_none_when_missing(self):
        file_io = import_plugin_module("export.file_io")
        with tempfile.TemporaryDirectory() as tmpdir:
            orig_file = file_io.__file__
            try:
                file_io.__file__ = os.path.join(tmpdir, "export", "file_io.py")
                export_file = os.path.join(tmpdir, "export.json")
                result = file_io._copy_standalone_viewer(export_file)
                self.assertIsNone(result)
            finally:
                file_io.__file__ = orig_file

    def test_copy_standalone_viewer_skips_copy_when_current(self):
        file_io = import_plugin_module("export.file_io")
        with tempfile.TemporaryDirectory() as tmpdir:
            web_dir = os.path.join(tmpdir, "web")
            os.makedirs(web_dir)
            src = os.path.join(web_dir, "standalone_viewer.html")
            with open(src, "w", encoding="utf-8") as f:
                f.write("<html></html>")

            # copy once to create an up-to-date dest
            export_dir = os.path.join(tmpdir, "exports")
            os.makedirs(export_dir)
            import shutil
            dest = os.path.join(export_dir, "MindMap_Viewer.html")
            shutil.copy2(src, dest)

            orig_file = file_io.__file__
            try:
                file_io.__file__ = os.path.join(tmpdir, "export", "file_io.py")
                export_file = os.path.join(export_dir, "data.json")
                result = file_io._copy_standalone_viewer(export_file)
                self.assertEqual(result, dest)
            finally:
                file_io.__file__ = orig_file

    # ------------------------------------------------------------------
    # export/error_utils
    # ------------------------------------------------------------------
    def test_print_export_failure(self):
        error_utils = import_plugin_module("export.error_utils")
        # should not raise
        try:
            error_utils._print_export_failure("Something broke", Exception("boom"))
        except Exception as e:
            self.fail(f"_print_export_failure raised {e}")

    # ------------------------------------------------------------------
    # export/export_mindmap
    # ------------------------------------------------------------------
    def test_export_mindmap_to_json_success(self):
        export_mindmap = import_plugin_module("export.export_mindmap")
        note = FakeNote(1, Title="Map A", UUID="u1", Data=json.dumps({"data": {"id": "root"}}), AllowNewCards="1")
        self.mw.col = FakeCollection(notes={1: note})

        with tempfile.TemporaryDirectory() as tmpdir:
            web_dir = os.path.join(tmpdir, "web")
            os.makedirs(web_dir)
            with open(os.path.join(web_dir, "standalone_viewer.html"), "w", encoding="utf-8") as f:
                f.write("<html></html>")

            filename = os.path.join(tmpdir, "single.json")
            FakeFileDialog.save_filename = filename

            # patch addon dir resolution inside export_mindmap module
            orig_file = export_mindmap.__file__
            try:
                export_mindmap.__file__ = os.path.join(tmpdir, "export", "export_mindmap.py")
                success, saved, viewer = export_mindmap.export_mindmap_to_json(None, self.mw, 1)
                self.assertTrue(success)
                self.assertEqual(saved, filename)
                self.assertEqual(viewer, os.path.join(tmpdir, "MindMap_Viewer.html"))
                self.assertTrue(os.path.exists(viewer))
                with open(filename, encoding="utf-8") as f:
                    payload = json.load(f)
                self.assertEqual(payload["title"], "Map A")
                self.assertEqual(payload["allow_new_cards"], "1")
                self.assertIn("export_date", payload)
                self.assertEqual(payload["uuid"], "u1")
            finally:
                export_mindmap.__file__ = orig_file

    def test_export_mindmap_to_json_cancelled(self):
        export_mindmap = import_plugin_module("export.export_mindmap")
        note = FakeNote(1, Title="Map A", UUID="u1", Data="", AllowNewCards="1")
        self.mw.col = FakeCollection(notes={1: note})
        FakeFileDialog.save_filename = ""
        success, saved, viewer = export_mindmap.export_mindmap_to_json(None, self.mw, 1)
        self.assertFalse(success)
        self.assertIsNone(saved)
        self.assertIsNone(viewer)

    def test_export_mindmap_to_json_exception(self):
        export_mindmap = import_plugin_module("export.export_mindmap")
        self.mw.col = FakeCollection(notes={})
        success, saved, viewer = export_mindmap.export_mindmap_to_json(None, self.mw, 1)
        self.assertFalse(success)
        self.assertIsNone(saved)
        self.assertIsNone(viewer)

    def test_export_mindmap_to_json_custom_title(self):
        export_mindmap = import_plugin_module("export.export_mindmap")
        note = FakeNote(1, Title="Map A", UUID="u1", Data=json.dumps({"x": 1}), AllowNewCards="0")
        self.mw.col = FakeCollection(notes={1: note})

        with tempfile.TemporaryDirectory() as tmpdir:
            web_dir = os.path.join(tmpdir, "web")
            os.makedirs(web_dir)
            with open(os.path.join(web_dir, "standalone_viewer.html"), "w", encoding="utf-8") as f:
                f.write("<html></html>")

            filename = os.path.join(tmpdir, "custom.json")
            FakeFileDialog.save_filename = filename
            orig_file = export_mindmap.__file__
            try:
                export_mindmap.__file__ = os.path.join(tmpdir, "export", "export_mindmap.py")
                success, saved, viewer = export_mindmap.export_mindmap_to_json(None, self.mw, 1, title="Custom")
                self.assertTrue(success)
                with open(saved, encoding="utf-8") as f:
                    payload = json.load(f)
                self.assertEqual(payload["title"], "Custom")
            finally:
                export_mindmap.__file__ = orig_file

    # ------------------------------------------------------------------
    # export/export_all_mindmaps
    # ------------------------------------------------------------------
    def test_export_all_mindmaps_success(self):
        export_all = import_plugin_module("export.export_all_mindmaps")
        note = FakeNote(1, Title="Map A", UUID="u1", Data=json.dumps({"data": {"id": "root"}}), AllowNewCards="1")
        self.mw.col = FakeCollection(notes={1: note})

        with tempfile.TemporaryDirectory() as tmpdir:
            web_dir = os.path.join(tmpdir, "web")
            os.makedirs(web_dir)
            with open(os.path.join(web_dir, "standalone_viewer.html"), "w", encoding="utf-8") as f:
                f.write("<html></html>")

            filename = os.path.join(tmpdir, "all.json")
            FakeFileDialog.save_filename = filename
            orig_file = export_all.__file__
            try:
                export_all.__file__ = os.path.join(tmpdir, "export", "export_all_mindmaps.py")
                success, saved, viewer, count = export_all.export_all_mindmaps(None, self.mw)
                self.assertTrue(success)
                self.assertEqual(saved, filename)
                self.assertEqual(viewer, os.path.join(tmpdir, "MindMap_Viewer.html"))
                self.assertEqual(count, 1)
                with open(saved, encoding="utf-8") as f:
                    payload = json.load(f)
                self.assertEqual(payload["mindmaps"][0]["note_id"], 1)
                self.assertEqual(payload["anki_version"], "42")
                self.assertIn("export_date", payload)
            finally:
                export_all.__file__ = orig_file

    def test_export_all_mindmaps_no_notes(self):
        export_all = import_plugin_module("export.export_all_mindmaps")
        self.mw.col = FakeCollection(notes={})
        success, saved, viewer, count = export_all.export_all_mindmaps(None, self.mw)
        self.assertFalse(success)
        self.assertIsNone(saved)
        self.assertIsNone(viewer)
        self.assertEqual(count, 0)

    def test_export_all_mindmaps_cancelled(self):
        export_all = import_plugin_module("export.export_all_mindmaps")
        note = FakeNote(1, Title="Map A", UUID="u1", Data="", AllowNewCards="1")
        self.mw.col = FakeCollection(notes={1: note})
        FakeFileDialog.save_filename = ""
        success, saved, viewer, count = export_all.export_all_mindmaps(None, self.mw)
        self.assertFalse(success)
        self.assertIsNone(saved)
        self.assertIsNone(viewer)
        self.assertEqual(count, 0)

    def test_export_all_mindmaps_exception(self):
        export_all = import_plugin_module("export.export_all_mindmaps")

        class BrokenCollection:
            def find_notes(self, query):
                raise RuntimeError("boom")

        self.mw.col = BrokenCollection()
        success, saved, viewer, count = export_all.export_all_mindmaps(None, self.mw)
        self.assertFalse(success)
        self.assertIsNone(saved)
        self.assertIsNone(viewer)
        self.assertEqual(count, 0)


if __name__ == "__main__":
    unittest.main()
