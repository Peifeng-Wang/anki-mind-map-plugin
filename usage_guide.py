from aqt import mw
from aqt.qt import QDialog, QHBoxLayout, QPushButton, QTextBrowser, QVBoxLayout

from .guide.content_cn import get_chinese_body, get_chinese_sidebar
from .guide.content_en import get_english_body, get_english_sidebar
from .guide.renderer import render_page


CONFIG_KEY_LANGUAGE = "guide_language"
DEFAULT_LANGUAGE = "en"
ACTIVE_BUTTON_STYLE = "background-color: #4CAF50; color: white; font-weight: bold;"


class UsageDialog(QDialog):
    def __init__(self, parent):
        super().__init__(parent)
        self.setWindowTitle("Mind Map Plugin - Usage Guide")
        self.resize(1000, 750)
        self.current_lang = self._load_language()
        self._content_loaded = False

        layout = QVBoxLayout(self)
        layout.addLayout(self._build_language_buttons())

        self.web = QTextBrowser(self)
        self.web.setOpenExternalLinks(False)
        self.web.setSearchPaths([])
        layout.addWidget(self.web)

        self.switch_language(self.current_lang, save_preference=False)

    def _build_language_buttons(self):
        btn_layout = QHBoxLayout()
        self.btn_en = QPushButton("English")
        self.btn_cn = QPushButton("中文")
        self.btn_en.clicked.connect(lambda: self.switch_language("en"))
        self.btn_cn.clicked.connect(lambda: self.switch_language("cn"))
        btn_layout.addWidget(self.btn_en)
        btn_layout.addWidget(self.btn_cn)
        btn_layout.addStretch()
        return btn_layout

    def _load_language(self):
        config = mw.addonManager.getConfig(__name__) or {}
        return self._normalize_language(config.get(CONFIG_KEY_LANGUAGE, DEFAULT_LANGUAGE))

    def _save_language(self, lang):
        config = mw.addonManager.getConfig(__name__) or {}
        config[CONFIG_KEY_LANGUAGE] = lang
        mw.addonManager.writeConfig(__name__, config)

    def _normalize_language(self, lang):
        return lang if lang in ("en", "cn") else DEFAULT_LANGUAGE

    def switch_language(self, lang, save_preference=True):
        next_lang = self._normalize_language(lang)
        if self._content_loaded and next_lang == self.current_lang:
            self._update_language_buttons()
            return

        self.current_lang = next_lang
        self._update_language_buttons()
        if save_preference:
            self._save_language(self.current_lang)
        content = self.get_english_content() if self.current_lang == "en" else self.get_chinese_content()
        self.web.setHtml(content)
        self._content_loaded = True

    def _update_language_buttons(self):
        self.btn_en.setStyleSheet(ACTIVE_BUTTON_STYLE if self.current_lang == "en" else "")
        self.btn_cn.setStyleSheet(ACTIVE_BUTTON_STYLE if self.current_lang == "cn" else "")

    def get_english_content(self):
        return render_page("en", get_english_sidebar(), get_english_body())

    def get_chinese_content(self):
        return render_page("cn", get_chinese_sidebar(), get_chinese_body())


def show_usage():
    dialog = UsageDialog(mw)
    dialog.exec()
