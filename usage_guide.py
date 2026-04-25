from aqt import mw
from aqt.qt import QDialog, QHBoxLayout, QPushButton, QTextBrowser, QVBoxLayout


CONFIG_KEY_LANGUAGE = "guide_language"
DEFAULT_LANGUAGE = "en"
ACTIVE_BUTTON_STYLE = "background-color: #4CAF50; color: white; font-weight: bold;"

GUIDE_STYLE = """
body { font-family: var(--guide-font), "Segoe UI", Arial, sans-serif; line-height: 1.6; margin: 0; padding: 0; background: #f9f9f9; color: #333; display: flex; height: 100vh; overflow: hidden; }
.sidebar { width: 220px; background: #2c3e50; color: white; padding: 20px; display: flex; flex-direction: column; overflow-y: auto; flex-shrink: 0; }
.sidebar h2 { color: #ecf0f1; font-size: 1.2em; margin-top: 0; border-bottom: 2px solid #34495e; padding-bottom: 10px; }
.nav-link { color: #bdc3c7; text-decoration: none; padding: 8px 0; display: block; transition: color 0.3s; font-size: 0.95em; }
.nav-link:hover { color: #ffffff; font-weight: bold; }
.main-content { flex-grow: 1; padding: 20px 40px; overflow-y: auto; scroll-behavior: smooth; }
h1 { color: #2c3e50; border-bottom: 3px solid #3498db; padding-bottom: 10px; margin-top: 0; }
h2 { color: #34495e; margin-top: 30px; border-left: 4px solid #3498db; padding: 10px; background: linear-gradient(to right, #f0f4f8, #ffffff); border-radius: 3px; }
h3 { color: #2980b9; margin-top: 20px; }
.shortcut { background: #3498db; color: white; padding: 2px 6px; border-radius: 4px; font-family: "Consolas", monospace; font-size: 0.9em; font-weight: bold; }
.feature { background: linear-gradient(to right, #e8f5e9, #f1fdf3); padding: 15px; margin: 15px 0; border-radius: 5px; border-left: 4px solid #4caf50; }
.tip { background: linear-gradient(to right, #fff3cd, #fffaf0); padding: 12px; margin: 10px 0; border-radius: 5px; border-left: 4px solid #ff9800; }
.warning { background: linear-gradient(to right, #ffebee, #fff5f6); padding: 12px; margin: 10px 0; border-radius: 5px; border-left: 4px solid #f44336; }
.warning strong { color: #c0392b; }
ul { padding-left: 20px; }
li { margin: 6px 0; }
code { background: #f5f5f5; padding: 2px 6px; border-radius: 3px; font-family: "Consolas", monospace; border: 1px solid #ddd; color: #e74c3c; }
table { width: 100%; border-collapse: collapse; margin: 15px 0; box-shadow: 0 2px 4px rgba(0,0,0,0.05); border-radius: 5px; overflow: hidden; }
th, td { border: none; border-bottom: 1px solid #e8e8e8; padding: 10px; text-align: left; }
th { background: linear-gradient(135deg, #3498db 0%, #5dade2 100%); color: white; font-weight: 600; }
tr:nth-child(even) { background: #fafbfc; }
tr:hover { background: #f0f7ff; }
"""


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

    def _render_page(self, lang, sidebar_html, body_html):
        font = '"Microsoft YaHei", "Segoe UI", Arial, sans-serif' if lang == "cn" else '"Segoe UI", Arial, sans-serif'
        return f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <style>
        :root {{ --guide-font: {font}; }}
        {GUIDE_STYLE}
    </style>
</head>
<body>
    <div class="sidebar">{sidebar_html}</div>
    <div class="main-content">{body_html}</div>
</body>
</html>
"""

    def get_english_content(self):
        return self._render_page("en", self._english_sidebar(), self._english_body())

    def get_chinese_content(self):
        return self._render_page("cn", self._chinese_sidebar(), self._chinese_body())

    def _english_sidebar(self):
        return """
        <h2>Contents</h2>
        <a href="#quick-start" class="nav-link">&#9889; Quick Start</a>
        <a href="#setup-sync" class="nav-link">&#9729; Sync Setup</a>
        <a href="#operations" class="nav-link">&#9733; Operations</a>
        <a href="#card-linking" class="nav-link">&#8644; Card Linking</a>
        <a href="#config" class="nav-link">&#9881; Configuration</a>
        <a href="#advanced" class="nav-link">&#9632; Advanced</a>
        <a href="#backup" class="nav-link">&#9851; Backup</a>
        """

    def _english_body(self):
        return """
        <h1>&#9733; Mind Map Plugin Guide</h1>
        <div id="quick-start" class="feature">
            <h2 style="margin-top:0;">&#9889; Quick Start Workflow</h2>
            <ol>
                <li><strong>Create Map:</strong> Go to <code>Tools &rarr; Mind Map &rarr; Mind Map Manager</code>, then click <strong>New</strong>.</li>
                <li><strong>Link Card:</strong> Open the Add window or Browser, click the <strong>MM</strong> toolbar button, and choose a map.</li>
                <li><strong>Edit Content:</strong> Edit the first line of the card Front field; it becomes the linked node text.</li>
                <li><strong>Refresh:</strong> Return to the mind map editor and press <strong>F5</strong>.</li>
                <li><strong>Navigate:</strong> Right-click a node to jump to the card, or click the review badge to return to the map node.</li>
            </ol>
            <div class="tip"><strong>Tip:</strong> Unlinked nodes can still be used for structure, titles, or brainstorming.</div>
        </div>

        <h2 id="setup-sync">&#9729; Important: First Time Sync</h2>
        <div class="warning">
            <strong>CRITICAL STEP FOR NEW USERS</strong>
            <p>After installing this add-on or using Active/Inactive for the first time, choose <strong>Upload to AnkiWeb</strong> when Anki asks how to sync.</p>
            <ul>
                <li>This is a one-time requirement for the custom <code>MindMap Master</code> note type.</li>
                <li>Future changes will sync normally.</li>
            </ul>
        </div>

        <h2 id="operations">&#9733; Basic Operations</h2>
        <table>
            <tr><th>Action</th><th>Shortcut</th><th>Description</th></tr>
            <tr><td>Add Child</td><td><span class="shortcut">Tab</span></td><td>Create a child node.</td></tr>
            <tr><td>Add Sibling</td><td><span class="shortcut">Enter</span></td><td>Create a sibling node.</td></tr>
            <tr><td>Edit</td><td><span class="shortcut">Space</span> / double-click</td><td>Edit text; use <span class="shortcut">Shift+Enter</span> for a new line.</td></tr>
            <tr><td>Delete</td><td><span class="shortcut">Delete</span></td><td>Remove the node and its children.</td></tr>
            <tr><td>Move</td><td>Drag &amp; Drop</td><td>Move a node to a new parent.</td></tr>
        </table>
        <h3>Copy, Paste &amp; Undo</h3>
        <ul>
            <li>Select a node and use <span class="shortcut">Ctrl+C</span> / <span class="shortcut">Ctrl+V</span> to copy it under another node.</li>
            <li>Pasting external text creates a new child node with that text.</li>
            <li>Undo with <span class="shortcut">Ctrl+Z</span>; redo with <span class="shortcut">Ctrl+Y</span> or <span class="shortcut">Ctrl+Shift+Z</span>.</li>
        </ul>

        <h2 id="card-linking">&#8644; Card Linking System</h2>
        <div class="feature">
            <p>Links are initiated from Anki cards to keep the workflow simple and compatible with different card types.</p>
            <ul>
                <li><strong>Mind Map &rarr; Card:</strong> editing a linked node updates the first line of the card Front field.</li>
                <li><strong>Card &rarr; Mind Map:</strong> editing the first line of the card Front field updates the linked node.</li>
            </ul>
        </div>
        <div class="warning"><strong>Auto-save warning:</strong> Wait for the "Auto-saved" notice before closing an editor after editing linked nodes.</div>

        <h2 id="config">&#9881; Configuration</h2>
        <p>Open <strong>Tools &rarr; Add-ons &rarr; Mind Map &rarr; Config</strong>.</p>
        <ul>
            <li><strong>Line Color:</strong> accepts names, Hex, or RGBA values.</li>
            <li><strong>Background:</strong> place images in <code>backgrounds</code> and set the filename in config.</li>
            <li><strong>Hotkeys:</strong> customize save, refresh, focus root, and quick open shortcuts.</li>
        </ul>

        <h2 id="advanced">&#9632; Advanced Features</h2>
        <ul>
            <li><strong>Floating Nodes:</strong> double-click empty space to create independent nodes.</li>
            <li><strong>MathJax:</strong> use standard inline and block math syntax.</li>
            <li><strong>Active/Inactive:</strong> hide completed maps from the card linking menu.</li>
            <li><strong>Fullscreen:</strong> use the toolbar fullscreen button.</li>
        </ul>

        <h2 id="backup">&#9851; Backup &amp; Recovery</h2>
        <p>Use <strong>Tools &rarr; Mind Map &rarr; Backup &amp; Recovery</strong> to export maps to JSON, optionally with an offline HTML viewer, or import them back later.</p>

        <hr style="margin: 30px 0; border: none; border-top: 2px solid #3498db;">
        <p style="text-align: center; color: #95a5a6;"><small>Anki Mind Map Plugin | Enhance Learning Through Visualization</small></p>
        """

    def _chinese_sidebar(self):
        return """
        <h2>目录导航</h2>
        <a href="#quick-start" class="nav-link">&#9889; 快速开始</a>
        <a href="#setup-sync" class="nav-link">&#9729; 首次同步</a>
        <a href="#operations" class="nav-link">&#9733; 基础操作</a>
        <a href="#card-linking" class="nav-link">&#8644; 卡片关联</a>
        <a href="#config" class="nav-link">&#9881; 插件配置</a>
        <a href="#advanced" class="nav-link">&#9632; 高级功能</a>
        <a href="#backup" class="nav-link">&#9851; 备份恢复</a>
        """

    def _chinese_body(self):
        return """
        <h1>&#9733; 思维导图插件使用指南</h1>
        <div id="quick-start" class="feature">
            <h2 style="margin-top:0;">&#9889; 快速开始流程</h2>
            <ol>
                <li><strong>创建导图：</strong>点击 <code>工具 &rarr; Mind Map &rarr; Mind Map Manager</code>，再点击 <strong>New</strong>。</li>
                <li><strong>关联卡片：</strong>在添加窗口或浏览器中点击工具栏 <strong>MM</strong> 按钮，选择目标导图。</li>
                <li><strong>编辑内容：</strong>卡片正面字段的第一行会同步为导图节点文字。</li>
                <li><strong>刷新查看：</strong>回到导图编辑器按 <strong>F5</strong>。</li>
                <li><strong>双向跳转：</strong>导图中右键节点可跳到卡片；复习时点击右上角徽章可回到导图节点。</li>
            </ol>
            <div class="tip"><strong>提示：</strong>未关联卡片的节点也可以用于结构整理、标题或头脑风暴。</div>
        </div>

        <h2 id="setup-sync">&#9729; 重要：首次同步设置</h2>
        <div class="warning">
            <strong>新用户必须注意</strong>
            <p>安装插件或首次使用启用/停用功能后，Anki 会检测到数据库结构变化。同步时请选择 <strong>上传到 AnkiWeb</strong>。</p>
            <ul>
                <li>这是一次性要求，用于建立自定义的 <code>MindMap Master</code> 笔记类型。</li>
                <li>之后的新增、编辑和关联操作会正常双向同步。</li>
            </ul>
        </div>

        <h2 id="operations">&#9733; 基础操作</h2>
        <table>
            <tr><th>操作</th><th>快捷键</th><th>说明</th></tr>
            <tr><td>添加子节点</td><td><span class="shortcut">Tab</span></td><td>在当前节点下创建子节点。</td></tr>
            <tr><td>添加同级节点</td><td><span class="shortcut">Enter</span></td><td>创建同级节点。</td></tr>
            <tr><td>编辑</td><td><span class="shortcut">空格</span> / 双击</td><td>编辑文字；<span class="shortcut">Shift+Enter</span> 换行。</td></tr>
            <tr><td>删除</td><td><span class="shortcut">Delete</span></td><td>删除节点及其所有子节点。</td></tr>
            <tr><td>移动</td><td>拖拽</td><td>拖动节点到新的父节点下。</td></tr>
        </table>
        <h3>复制、粘贴与撤销</h3>
        <ul>
            <li>选中节点后使用 <span class="shortcut">Ctrl+C</span> / <span class="shortcut">Ctrl+V</span> 可复制到另一个节点下。</li>
            <li>粘贴外部文本时，会自动创建包含该文本的子节点。</li>
            <li>撤销使用 <span class="shortcut">Ctrl+Z</span>；重做使用 <span class="shortcut">Ctrl+Y</span> 或 <span class="shortcut">Ctrl+Shift+Z</span>。</li>
        </ul>

        <h2 id="card-linking">&#8644; 卡片关联系统</h2>
        <div class="feature">
            <p>关联从卡片发起，能兼容不同卡片类型并保持流程简单。</p>
            <ul>
                <li><strong>导图到卡片：</strong>编辑已关联节点会更新卡片正面字段第一行。</li>
                <li><strong>卡片到导图：</strong>编辑卡片正面字段第一行会更新对应导图节点。</li>
            </ul>
        </div>
        <div class="warning"><strong>自动保存提醒：</strong>编辑已关联节点后，请等待右上角 Auto-saved 提示出现再关闭窗口。</div>

        <h2 id="config">&#9881; 插件配置</h2>
        <p>前往 <strong>工具 &rarr; 插件 &rarr; Mind Map &rarr; Config</strong> 自定义设置。</p>
        <ul>
            <li><strong>线条颜色：</strong>支持颜色名、Hex 或 RGBA。</li>
            <li><strong>背景图片：</strong>将图片放入 <code>backgrounds</code> 文件夹，并在配置中填写文件名。</li>
            <li><strong>快捷键：</strong>可配置保存、刷新、聚焦根节点和快速打开。</li>
        </ul>

        <h2 id="advanced">&#9632; 高级功能</h2>
        <ul>
            <li><strong>浮动节点：</strong>双击空白处创建独立节点，适合临时整理想法。</li>
            <li><strong>数学公式：</strong>支持标准行内和块级 MathJax 语法。</li>
            <li><strong>启用/停用：</strong>可在管理器中隐藏已完成导图，避免出现在卡片关联菜单。</li>
            <li><strong>全屏模式：</strong>点击工具栏全屏按钮进入沉浸式编辑。</li>
        </ul>

        <h2 id="backup">&#9851; 备份与恢复</h2>
        <p>使用 <strong>工具 &rarr; Mind Map &rarr; Backup &amp; Recovery</strong> 导出 JSON 备份，可附带离线 HTML 查看器，也可以稍后从 JSON 文件导入恢复。</p>

        <hr style="margin: 30px 0; border: none; border-top: 2px solid #3498db;">
        <p style="text-align: center; color: #95a5a6;"><small>Anki 思维导图插件 | 通过可视化增强学习</small></p>
        """


def show_usage():
    dialog = UsageDialog(mw)
    dialog.exec()
