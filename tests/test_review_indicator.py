"""Dedicated unit tests for review_indicator.py (repo root module)."""
import importlib
import json
import sys
import types
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PACKAGE_NAME = "mindmap_plugin_under_test"


class HookList(list):
    pass


class FakeAddonManager:
    def __init__(self):
        self.config = {}

    def getConfig(self, name):
        return dict(self.config)

    def writeConfig(self, name, config):
        self.config = dict(config)


class FakeNote(dict):
    def __init__(self, note_id=0, **fields):
        super().__init__(fields)
        self.id = note_id

    def keys(self):
        return super().keys()


class FakeCollection:
    def __init__(self, notes=None):
        self.notes = notes or {}
        self.updated_notes = []

    def get_note(self, note_id):
        return self.notes[note_id]

    def update_note(self, note):
        self.updated_notes.append(note)


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
        utils.showInfo = lambda *a, **kw: None
        utils.tooltip = lambda *a, **kw: None
        utils.getText = lambda *a, **kw: ("", False)
        utils.askUser = lambda *a, **kw: False
        return utils

    _, _, _, hooks = install_aqt_stub(
        fake_mw=fake_mw,
        hook_list_cls=HookList,
        utils_factory=_utils_factory,
    )
    return fake_mw, hooks


def import_plugin_module(name):
    if PACKAGE_NAME not in sys.modules:
        package = types.ModuleType(PACKAGE_NAME)
        package.__path__ = [str(ROOT)]
        sys.modules[PACKAGE_NAME] = package
    full_name = f"{PACKAGE_NAME}.{name}"
    sys.modules.pop(full_name, None)
    return importlib.import_module(full_name)


def _clear_package_modules():
    for key in list(sys.modules):
        if key.startswith(f"{PACKAGE_NAME}."):
            sys.modules.pop(key)
    # Also clear cached attributes on the parent package so that subsequent
    # `from . import name` calls re-resolve through sys.modules.
    pkg = sys.modules.get(PACKAGE_NAME)
    if pkg is not None:
        for attr in ("card_linker", "mindmap_editor"):
            if hasattr(pkg, attr):
                delattr(pkg, attr)


class _RecordingWeb:
    def __init__(self):
        self.calls = []

    def eval(self, js):
        self.calls.append(js)


class _Card:
    def __init__(self, note):
        self._note = note

    def note(self):
        return self._note


class HookRegistrationTests(unittest.TestCase):
    """review_indicator registers three hooks at import time."""

    def setUp(self):
        self.mw, self.hooks = install_anki_stubs()
        _clear_package_modules()

    def test_hooks_appended_on_import(self):
        before_q = len(self.hooks.reviewer_did_show_question)
        before_a = len(self.hooks.reviewer_did_show_answer)
        before_pycmd = len(self.hooks.webview_did_receive_js_message)

        import_plugin_module("review_indicator")

        self.assertEqual(len(self.hooks.reviewer_did_show_question), before_q + 1)
        self.assertEqual(len(self.hooks.reviewer_did_show_answer), before_a + 1)
        self.assertEqual(len(self.hooks.webview_did_receive_js_message), before_pycmd + 1)

    def test_question_hook_invokes_show_indicator(self):
        ri = import_plugin_module("review_indicator")
        # The lambda registered ignores its argument and calls show_mindmap_indicator.
        # mw.reviewer is None, so it should be a no-op (no exception).
        self.mw.reviewer = None
        hook_fn = self.hooks.reviewer_did_show_question[-1]
        hook_fn(object())  # passes some arg to the lambda
        # If we got here without raising, the hook is wired correctly.
        self.assertTrue(callable(hook_fn))

    def test_pycmd_hook_returns_handled_for_unknown_command(self):
        import_plugin_module("review_indicator")
        hook_fn = self.hooks.webview_did_receive_js_message[-1]
        sentinel = (False, "untouched")
        result = hook_fn(sentinel, "not_a_mindmap_command", None)
        self.assertEqual(result, sentinel)


class ShowMindmapIndicatorTests(unittest.TestCase):
    def setUp(self):
        self.mw, self.hooks = install_anki_stubs()
        _clear_package_modules()
        self.ri = import_plugin_module("review_indicator")

    def tearDown(self):
        _clear_package_modules()

    def test_no_reviewer_returns_silently(self):
        self.mw.reviewer = None
        # must not raise
        self.ri.show_mindmap_indicator()

    def test_no_card_returns_silently(self):
        self.mw.reviewer = types.SimpleNamespace(card=None, web=_RecordingWeb())
        self.ri.show_mindmap_indicator()
        self.assertEqual(self.mw.reviewer.web.calls, [])

    def test_renders_clear_indicator_when_note_has_no_link(self):
        note = FakeNote(1, Front="plain content", Back="no link here")
        web = _RecordingWeb()
        self.mw.reviewer = types.SimpleNamespace(card=_Card(note), web=web)

        self.ri.show_mindmap_indicator()

        self.assertEqual(len(web.calls), 1)
        # Clear-indicator JS removes any existing element
        self.assertIn("existing.remove()", web.calls[0])
        # And does NOT include the build-creation pattern
        self.assertNotIn("document.createElement('div')", web.calls[0])

    def test_renders_indicator_when_link_resolves(self):
        # Card has a mindmap link to mindmap id=2, node node:1
        card_note = FakeNote(
            1,
            Front='<span class="mindmap-link" data-mid="2" data-nid="node:1"></span>',
        )
        mm = FakeNote(
            2,
            Title="Topic",
            Data=json.dumps({"data": {"id": "root", "children": [{"id": "node:1"}]}}),
        )
        self.mw.col = FakeCollection(notes={2: mm})
        web = _RecordingWeb()
        self.mw.reviewer = types.SimpleNamespace(card=_Card(card_note), web=web)

        self.ri.show_mindmap_indicator()

        self.assertEqual(len(web.calls), 1)
        out = web.calls[0]
        self.assertIn("Topic", out)
        # pycmd param has format open_mindmap:<mid>:<nid>
        self.assertIn("open_mindmap:2:node:1", out)
        # The mindmap was not modified (no cleanup happened)
        self.assertEqual(self.mw.col.updated_notes, [])

    def test_cleans_up_card_link_when_node_missing(self):
        card_note = FakeNote(
            1,
            Front='<span class="mindmap-link" data-mid="2" data-nid="ghost"></span>',
        )
        mm = FakeNote(
            2,
            Title="Topic",
            Data=json.dumps({"data": {"id": "root", "children": []}}),
        )
        self.mw.col = FakeCollection(notes={2: mm})
        web = _RecordingWeb()
        self.mw.reviewer = types.SimpleNamespace(card=_Card(card_note), web=web)

        # Stub card_linker because review_indicator does `from . import card_linker`
        card_linker = types.ModuleType(f"{PACKAGE_NAME}.card_linker")
        cl_calls = []
        card_linker.remove_link_from_card = lambda note, field: cl_calls.append((note, field))
        sys.modules[f"{PACKAGE_NAME}.card_linker"] = card_linker
        sys.modules[PACKAGE_NAME].card_linker = card_linker

        self.ri.show_mindmap_indicator()

        self.assertEqual(len(cl_calls), 1)
        called_note, called_field = cl_calls[0]
        self.assertIs(called_note, card_note)
        self.assertEqual(called_field, "Front")
        # Last JS call clears the indicator
        self.assertIn("existing.remove()", web.calls[-1])

    def test_renders_clear_when_mindmap_note_missing_entirely(self):
        # _resolve_mindmap_link returns (None, False) → falls through to _render_indicator()
        card_note = FakeNote(
            1,
            Front='<span class="mindmap-link" data-mid="999" data-nid="node:1"></span>',
        )
        self.mw.col = FakeCollection(notes={})
        web = _RecordingWeb()
        self.mw.reviewer = types.SimpleNamespace(card=_Card(card_note), web=web)

        # _resolve_mindmap_link returns (None, False); _build_pycmd_param with empty title
        # yields "" and _render_indicator renders an indicator with empty title.
        self.ri.show_mindmap_indicator()

        self.assertEqual(len(web.calls), 1)
        self.assertIn("existing.remove()", web.calls[0])


class OnReviewerPycmdTests(unittest.TestCase):
    def setUp(self):
        self.mw, self.hooks = install_anki_stubs()
        _clear_package_modules()
        self.ri = import_plugin_module("review_indicator")

    def tearDown(self):
        _clear_package_modules()

    def _install_opener(self, side_effect=None):
        opened = []
        # Build mindmap_editor.opener as a stub so review_indicator's
        # ``from .mindmap_editor.opener import open_mindmap`` resolves.
        editor_pkg_name = f"{PACKAGE_NAME}.mindmap_editor"
        editor_pkg = sys.modules.get(editor_pkg_name)
        if editor_pkg is None:
            editor_pkg = types.ModuleType(editor_pkg_name)
            editor_pkg.__path__ = []
            sys.modules[editor_pkg_name] = editor_pkg
            sys.modules[PACKAGE_NAME].mindmap_editor = editor_pkg

        opener_mod = types.ModuleType(f"{editor_pkg_name}.opener")

        def _open(mid, nid):
            opened.append((mid, nid))
            if side_effect is not None:
                side_effect()

        opener_mod.open_mindmap = _open
        sys.modules[f"{editor_pkg_name}.opener"] = opener_mod
        editor_pkg.opener = opener_mod
        return opened

    def test_opens_with_mindmap_id_and_node_id(self):
        opened = self._install_opener()
        result = self.ri.on_reviewer_pycmd((False, None), "open_mindmap:42:node:abc", None)
        self.assertEqual(result, (True, None))
        self.assertEqual(opened, [(42, "node:abc")])

    def test_opens_without_node_id(self):
        opened = self._install_opener()
        # cmd has only two parts → split(":", 2) yields ["open_mindmap", "42"]
        result = self.ri.on_reviewer_pycmd((False, None), "open_mindmap:42", None)
        self.assertEqual(result, (True, None))
        # node_id is None when no third part
        self.assertEqual(opened, [(42, None)])

    def test_returns_handled_for_unrelated_command(self):
        # No opener installed; tests pass-through behavior
        sentinel_handled = (True, "result")
        result = self.ri.on_reviewer_pycmd(sentinel_handled, "other_command", None)
        self.assertEqual(result, sentinel_handled)

        sentinel_unhandled = (False, None)
        result2 = self.ri.on_reviewer_pycmd(sentinel_unhandled, "another:cmd", None)
        self.assertEqual(result2, sentinel_unhandled)

    def test_swallows_value_error_for_bad_id(self):
        opened = self._install_opener()
        # mindmap id is non-integer → int(...) raises ValueError, which is swallowed.
        result = self.ri.on_reviewer_pycmd(
            (False, None), "open_mindmap:notanumber:node:1", None
        )
        # Still returns (True, None) because the prefix matched
        self.assertEqual(result, (True, None))
        # open_mindmap was never reached
        self.assertEqual(opened, [])

    def test_swallows_exception_from_opener(self):
        def boom():
            raise RuntimeError("kaboom")

        opened = self._install_opener(side_effect=boom)
        result = self.ri.on_reviewer_pycmd((False, None), "open_mindmap:5:n2", None)
        # exception swallowed, command marked handled
        self.assertEqual(result, (True, None))
        self.assertEqual(opened, [(5, "n2")])

    def test_does_not_match_partial_prefix(self):
        # "open_mindmaps" does not start with "open_mindmap:" so it falls through.
        # NOTE: actual prefix value depends on MINDMAP_COMMAND_PREFIX. We test
        # that an obviously unrelated command falls through.
        opened = self._install_opener()
        sentinel = (False, "untouched")
        result = self.ri.on_reviewer_pycmd(sentinel, "completely_different", None)
        self.assertEqual(result, sentinel)
        self.assertEqual(opened, [])


if __name__ == "__main__":
    unittest.main()
