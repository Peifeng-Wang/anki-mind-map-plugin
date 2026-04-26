import importlib
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


class FakeAddonManager:
    def __init__(self):
        self.config = {}
        self.writes = []

    def getConfig(self, name):
        return dict(self.config)

    def writeConfig(self, name, config):
        self.writes.append((name, dict(config)))
        self.config = dict(config)


class FakeMainWindow:
    def __init__(self):
        self.addonManager = FakeAddonManager()
        self.col = None
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
        hook_names=(
            "reviewer_did_show_question",
            "reviewer_did_show_answer",
            "webview_did_receive_js_message",
        ),
        hook_list_cls=list,
        utils_factory=_utils_factory,
        install_anki=False,
        include_input_helpers=False,
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


class TestGuideModules(unittest.TestCase):
    def setUp(self):
        self.mw, self.utils, self.hooks = install_anki_stubs()
        for key in list(sys.modules):
            if key.startswith(f"{PACKAGE_NAME}."):
                sys.modules.pop(key)

    def test_renderer_guide_style_is_string(self):
        renderer = import_plugin_module("guide.renderer")
        self.assertIsInstance(renderer.GUIDE_STYLE, str)
        self.assertIn("body {", renderer.GUIDE_STYLE)
        self.assertIn(".sidebar {", renderer.GUIDE_STYLE)
        self.assertIn(".main-content {", renderer.GUIDE_STYLE)

    def test_renderer_render_page_en(self):
        renderer = import_plugin_module("guide.renderer")
        sidebar = "<a href='#test'>Link</a>"
        body = "<h1>Hello</h1>"
        result = renderer.render_page("en", sidebar, body)
        self.assertIn("<!DOCTYPE html>", result)
        self.assertIn(sidebar, result)
        self.assertIn(body, result)
        self.assertIn("--guide-font: \"Segoe UI\", Arial, sans-serif", result)
        self.assertIn(renderer.GUIDE_STYLE, result)

    def test_renderer_render_page_cn(self):
        renderer = import_plugin_module("guide.renderer")
        sidebar = "<a href='#test'>链接</a>"
        body = "<h1>你好</h1>"
        result = renderer.render_page("cn", sidebar, body)
        self.assertIn("--guide-font: \"Microsoft YaHei\", \"Segoe UI\", Arial, sans-serif", result)
        self.assertIn(sidebar, result)
        self.assertIn(body, result)

    def test_content_en_sidebar_contains_expected_sections(self):
        content_en = import_plugin_module("guide.content_en")
        sidebar = content_en.get_english_sidebar()
        self.assertIsInstance(sidebar, str)
        self.assertIn("Contents", sidebar)
        self.assertIn("#quick-start", sidebar)
        self.assertIn("#backup", sidebar)

    def test_content_en_body_contains_expected_sections(self):
        content_en = import_plugin_module("guide.content_en")
        body = content_en.get_english_body()
        self.assertIsInstance(body, str)
        self.assertIn("Mind Map Plugin Guide", body)
        self.assertIn("Quick Start Workflow", body)
        self.assertIn("First Time Sync", body)
        self.assertIn("Basic Operations", body)
        self.assertIn("Card Linking System", body)
        self.assertIn("Configuration", body)
        self.assertIn("Advanced Features", body)
        self.assertIn("Backup", body)

    def test_content_cn_sidebar_contains_expected_sections(self):
        content_cn = import_plugin_module("guide.content_cn")
        sidebar = content_cn.get_chinese_sidebar()
        self.assertIsInstance(sidebar, str)
        self.assertIn("目录导航", sidebar)
        self.assertIn("#quick-start", sidebar)
        self.assertIn("#backup", sidebar)

    def test_content_cn_body_contains_expected_sections(self):
        content_cn = import_plugin_module("guide.content_cn")
        body = content_cn.get_chinese_body()
        self.assertIsInstance(body, str)
        self.assertIn("思维导图插件使用指南", body)
        self.assertIn("快速开始流程", body)
        self.assertIn("首次同步", body)
        self.assertIn("基础操作", body)
        self.assertIn("卡片关联系统", body)
        self.assertIn("插件配置", body)
        self.assertIn("高级功能", body)
        self.assertIn("备份与恢复", body)

    def test_usage_dialog_facade_switch_language_and_content(self):
        usage = import_plugin_module("usage_guide")
        dialog = usage.UsageDialog(self.mw)
        dialog.switch_language("cn")
        self.assertEqual(self.mw.addonManager.config["guide_language"], "cn")
        self.assertIn("中文", dialog.btn_cn.text)
        self.assertIn("#quick-start", dialog.get_chinese_content())
        self.assertIn('id="backup"', dialog.get_english_content())
        dialog.switch_language("invalid")
        self.assertEqual(dialog.current_lang, "en")

    def test_usage_dialog_initial_language_load(self):
        self.mw.addonManager.config = {"guide_language": "cn"}
        usage = import_plugin_module("usage_guide")
        dialog = usage.UsageDialog(self.mw)
        self.assertEqual(dialog.current_lang, "cn")

    def test_usage_dialog_switch_language_no_save(self):
        usage = import_plugin_module("usage_guide")
        dialog = usage.UsageDialog(self.mw)
        dialog.switch_language("en", save_preference=False)
        self.assertEqual(self.mw.addonManager.config.get("guide_language"), None)

    def test_usage_dialog_re_switch_same_lang_skips_reload(self):
        usage = import_plugin_module("usage_guide")
        dialog = usage.UsageDialog(self.mw)
        dialog.switch_language("en")
        initial_html = dialog.web.html
        dialog.switch_language("en")
        self.assertEqual(dialog.web.html, initial_html)

    def test_show_usage_runs(self):
        usage = import_plugin_module("usage_guide")
        result = usage.show_usage()
        self.assertIsNone(result)


if __name__ == "__main__":
    unittest.main()
