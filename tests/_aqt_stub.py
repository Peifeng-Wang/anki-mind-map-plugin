"""Shared helpers for building the in-memory ``aqt`` stub modules used by
the unit-test suite.

Tests cannot import the real ``aqt``/``anki`` packages, so each suite
historically inlined a near-identical ``install_anki_stubs`` helper that
registered ``aqt``, ``aqt.qt``, ``aqt.utils``, ``aqt.gui_hooks`` plus
``anki``/``anki.models`` in ``sys.modules`` before importing the plugin
under test.

This module consolidates that boilerplate so the per-suite helpers stay a
thin shim over :func:`install_aqt_stub`. The function returns the freshly
installed modules so tests can keep returning ``(fake_mw, utils, hooks)``
or any subset they need.
"""

from __future__ import annotations

import sys
import types
from typing import Any, Iterable, Optional


def _default_qmenu():
    return type("QMenu", (), {"__init__": lambda self, *a, **kw: None})


def _default_qdialog_family() -> dict:
    """Return a dict of QDialog/QVBoxLayout/etc. minimal classes.

    Used by suites that don't have a richer FakeWidget — they get a
    generic class whose ``__init__`` accepts arbitrary args.
    """
    base = type("QStub", (), {"__init__": lambda self, *a, **kw: None})
    names = (
        "QDialog", "QVBoxLayout", "QHBoxLayout", "QPushButton",
        "QTextEdit", "QTextBrowser", "QListWidget",
    )
    return {name: type(name, (base,), {}) for name in names}


def _default_qfile_dialog():
    class _FakeFileDialog:
        @staticmethod
        def getSaveFileName(*a, **kw):
            return ("", "")

        @staticmethod
        def getOpenFileName(*a, **kw):
            return ("", "")

    return _FakeFileDialog


def install_aqt_stub(
    *,
    fake_mw: Any,
    widget_factory: Optional[Any] = None,
    file_dialog: Optional[Any] = None,
    extra_qt_names: Optional[dict] = None,
    hook_names: Optional[Iterable[str]] = None,
    hook_list_cls: Optional[Any] = None,
    utils_factory: Optional[Any] = None,
    install_anki: bool = True,
    include_input_helpers: bool = True,
    install_webview: bool = True,
) -> tuple:
    """Install a canonical ``aqt`` stub into ``sys.modules`` and return
    ``(aqt, qt, utils, hooks)``.

    Parameters
    ----------
    fake_mw
        Instance to expose as ``aqt.mw``.
    widget_factory
        Class used for ``QDialog``/``QVBoxLayout``/etc. Tests that build a
        rich ``FakeWidget`` should pass it here. Defaults to a permissive
        no-op class per Qt name.
    file_dialog
        Class used for ``QFileDialog``. Defaults to a stub that returns
        ``("", "")`` for both ``getSaveFileName`` and ``getOpenFileName``.
    extra_qt_names
        Extra attributes to assign on the ``aqt.qt`` module (e.g. for
        custom signal/event types).
    hook_names
        Names of hook lists to expose on ``aqt.gui_hooks``. Defaults to the
        full set used across the suite.
    hook_list_cls
        Class used for each hook list. Defaults to a plain ``list``
        subclass so callers can ``isinstance`` check them.
    utils_factory
        Optional callable returning a custom ``aqt.utils`` module. If
        omitted, a default stub with ``messages``/``tooltips`` capture
        lists is installed.
    install_anki
        When True (default), also installs ``anki`` and ``anki.models``
        with ``NotetypeDict = dict`` so plugin imports succeed.
    include_input_helpers
        When True (default), populate ``QCursor``/``QMenu``/``QTimer`` —
        they are required by code paths added in P1. Suites that import
        modules predating P1 can pass ``False`` to mirror the original
        narrower stub.
    """
    aqt = types.ModuleType("aqt")
    aqt.mw = fake_mw

    qt = types.ModuleType("aqt.qt")
    if widget_factory is not None:
        qt.QDialog = widget_factory
        qt.QVBoxLayout = widget_factory
        qt.QHBoxLayout = widget_factory
        qt.QPushButton = widget_factory
        qt.QTextEdit = widget_factory
        qt.QTextBrowser = widget_factory
        qt.QListWidget = widget_factory
    else:
        for name, cls in _default_qdialog_family().items():
            setattr(qt, name, cls)

    qt.QFileDialog = file_dialog if file_dialog is not None else _default_qfile_dialog()

    if include_input_helpers:
        qt.QCursor = types.SimpleNamespace(pos=lambda: (0, 0))
        qt.QMenu = _default_qmenu()
        qt.QTimer = types.SimpleNamespace(singleShot=lambda ms, cb: cb())

    if extra_qt_names:
        for name, value in extra_qt_names.items():
            setattr(qt, name, value)

    if utils_factory is not None:
        utils = utils_factory()
    else:
        utils = types.ModuleType("aqt.utils")
        utils.messages = []
        utils.tooltips = []
        utils.showInfo = lambda message: utils.messages.append(message)
        utils.tooltip = lambda message: utils.tooltips.append(message)
        utils.getText = lambda *a, **kw: ("", False)
        utils.askUser = lambda *a, **kw: False

    list_cls = hook_list_cls if hook_list_cls is not None else type("HookList", (list,), {})
    if hook_names is None:
        hook_names = (
            "reviewer_did_show_question",
            "reviewer_did_show_answer",
            "webview_did_receive_js_message",
            "editor_did_init_buttons",
            "editor_did_load_note",
            "add_cards_did_add_note",
            "note_will_flush",
            "notes_will_be_deleted",
        )
    hooks = types.SimpleNamespace(**{name: list_cls() for name in hook_names})
    aqt.gui_hooks = hooks

    sys.modules["aqt"] = aqt
    sys.modules["aqt.qt"] = qt
    sys.modules["aqt.utils"] = utils

    if install_webview:
        webview = types.ModuleType("aqt.webview")

        class _AnkiWebViewStub:
            def __init__(self, *args, **kwargs):
                pass

        webview.AnkiWebView = _AnkiWebViewStub
        aqt.webview = webview
        sys.modules["aqt.webview"] = webview

    if install_anki:
        anki = types.ModuleType("anki")
        anki_models = types.ModuleType("anki.models")
        anki_models.NotetypeDict = dict
        sys.modules["anki"] = anki
        sys.modules["anki.models"] = anki_models

    return aqt, qt, utils, hooks
