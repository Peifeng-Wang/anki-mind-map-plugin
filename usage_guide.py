from aqt import mw
from aqt.qt import *

class UsageDialog(QDialog):
    def __init__(self, parent):
        super().__init__(parent)
        self.setWindowTitle("Mind Map Plugin - Usage Guide")
        self.resize(1000, 750)
        
        # Get current language preference
        config = mw.addonManager.getConfig(__name__) or {}
        self.current_lang = config.get('guide_language', 'en')
        
        layout = QVBoxLayout(self)
        
        # Language toggle buttons
        btn_layout = QHBoxLayout()
        self.btn_en = QPushButton("English")
        self.btn_cn = QPushButton("中文")
        
        self.btn_en.clicked.connect(lambda: self.switch_language('en'))
        self.btn_cn.clicked.connect(lambda: self.switch_language('cn'))
        
        btn_layout.addWidget(self.btn_en)
        btn_layout.addWidget(self.btn_cn)
        btn_layout.addStretch()
        
        layout.addLayout(btn_layout)
        
        # Web view for content
        self.web = QTextBrowser(self)
        self.web.setOpenExternalLinks(False)
        # Allow linking to anchors within the page
        self.web.setSearchPaths([]) 
        layout.addWidget(self.web)
        
        # Load initial content
        self.switch_language(self.current_lang)
    
    def switch_language(self, lang):
        self.current_lang = lang
        
        # Update button styles
        if lang == 'en':
            self.btn_en.setStyleSheet("background-color: #4CAF50; color: white; font-weight: bold;")
            self.btn_cn.setStyleSheet("")
        else:
            self.btn_cn.setStyleSheet("background-color: #4CAF50; color: white; font-weight: bold;")
            self.btn_en.setStyleSheet("")
        
        # Save preference
        config = mw.addonManager.getConfig(__name__) or {}
        config['guide_language'] = lang
        mw.addonManager.writeConfig(__name__, config)
        
        # Load content
        content = self.get_english_content() if lang == 'en' else self.get_chinese_content()
        self.web.setHtml(content)
    
    def get_english_content(self):
        # Using safe BMP Unicode entities to avoid rendering issues
        # Icons used: ⚡(&#9889;), ☁(&#9729;), ★(&#9733;), ⇄(&#8644;), ⚙(&#9881;), 📦(&#128230;->&#9632;), ♻(&#9851;)
        return """
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <style>
        body { font-family: "Segoe UI", Arial, sans-serif; line-height: 1.6; margin: 0; padding: 0; background: #f9f9f9; color: #333; display: flex; height: 100vh; overflow: hidden; }
        .sidebar { width: 220px; background: #2c3e50; color: white; padding: 20px; display: flex; flex-direction: column; overflow-y: auto; flex-shrink: 0; }
        .sidebar h2 { color: #ecf0f1; font-size: 1.2em; margin-top: 0; border-bottom: 2px solid #34495e; padding-bottom: 10px; }
        .nav-link { color: #bdc3c7; text-decoration: none; padding: 8px 0; display: block; transition: color 0.3s; font-size: 0.95em; }
        .nav-link:hover { color: #ffffff; font-weight: bold; }
        .main-content { flex-grow: 1; padding: 20px 40px; overflow-y: auto; scroll-behavior: smooth; }
        h1 { color: #2c3e50; border-bottom: 3px solid #3498db; padding-bottom: 10px; margin-top: 0; }
        h2 { color: #34495e; margin-top: 30px; border-left: 4px solid #3498db; padding-left: 10px; background: linear-gradient(to right, #f0f4f8, #ffffff); padding: 10px; border-radius: 3px; }
        h3 { color: #2980b9; margin-top: 20px; }
        .shortcut { background: #3498db; color: white; padding: 2px 6px; border-radius: 4px; font-family: "Consolas", monospace; font-size: 0.9em; font-weight: bold; }
        .feature { background: linear-gradient(to right, #e8f5e9, #f1fdf3); padding: 15px; margin: 15px 0; border-radius: 5px; border-left: 4px solid #4caf50; }
        .tip { background: linear-gradient(to right, #fff3cd, #fffaf0); padding: 12px; margin: 10px 0; border-radius: 5px; border-left: 4px solid #ff9800; }
        .warning { background: linear-gradient(to right, #ffebee, #fff5f6); padding: 12px; margin: 10px 0; border-radius: 5px; border-left: 4px solid #f44336; }
        .warning strong { color: #c0392b; }
        ul { padding-left: 20px; } li { margin: 6px 0; }
        code { background: #f5f5f5; padding: 2px 6px; border-radius: 3px; font-family: "Consolas", monospace; border: 1px solid #ddd; color: #e74c3c; }
        table { width: 100%; border-collapse: collapse; margin: 15px 0; box-shadow: 0 2px 4px rgba(0,0,0,0.05); border-radius: 5px; overflow: hidden; }
        th, td { border: none; border-bottom: 1px solid #e8e8e8; padding: 10px; text-align: left; }
        th { background: linear-gradient(135deg, #3498db 0%, #5dade2 100%); color: white; font-weight: 600; }
        tr:nth-child(even) { background: #fafbfc; } tr:hover { background: #f0f7ff; }
    </style>
</head>
<body>
    <div class="sidebar">
        <h2>Contents</h2>
        <a href="#quick-start" class="nav-link">&#9889; Quick Start</a>
        <a href="#setup-sync" class="nav-link">&#9729; Sync Setup</a>
        <a href="#operations" class="nav-link">&#9733; Operations</a>
        <a href="#card-linking" class="nav-link">&#8644; Card Linking</a>
        <a href="#config" class="nav-link">&#9881; Configuration</a>
        <a href="#advanced" class="nav-link">&#9632; Advanced</a>
        <a href="#backup" class="nav-link">&#9851; Backup</a>
    </div>

    <div class="main-content">
        <h1>&#9733; Mind Map Plugin Guide</h1>
        
        <div id="quick-start" class="feature">
            <h2 style="margin-top:0;">&#9889; Quick Start Workflow</h2>
            <p>Follow these steps to create your first linked mind map:</p>
            <ol>
                <li><strong>Create Map:</strong> Go to <code>Tools &rarr; Mind Map &rarr; Mind Map Manager</code>, and click <strong>New</strong>.</li>
                <li><strong>Link Card:</strong> Open the Anki "Add" window or "Browser", click the <strong>MM</strong> button in the toolbar, and select your map.</li>
                <li><strong>Edit Content:</strong> IMPORTANT! Edit the <strong>first line</strong> of the card's "Front" field. This line directly corresponds to the node's text in the mind map.</li>
                <li><strong>View Node:</strong> Return to the Mind Map editor and press <strong>F5</strong> (Refresh). You will see your new node linked.</li>
                <li><strong>Navigate:</strong>
                    <ul>
                        <li>In Mind Map: <strong>Right-click a node</strong> &rarr; "Jump to Card" to open in Browser.</li>
                        <li>In Review: Click the top-right <strong>Mind Map Badge</strong> to jump to the node.</li>
                    </ul>
                </li>
            </ol>
            <div class="tip">
                <strong>&#10024; Tip:</strong> Not all nodes need to be linked to cards. You can freely create unlinked nodes for structure, titles, or brainstorming!
            </div>
        </div>

        <h2 id="setup-sync">&#9729; Important: First Time Sync</h2>
        <div class="warning">
            <strong>&#9888; CRITICAL STEP FOR NEW USERS</strong>
            <p>After installing this add-on or using the Active/Inactive feature for the first time, Anki will detect database structure changes.</p>
            <p>When asked to Sync, you MUST choose: <strong>"Upload to AnkiWeb"</strong>.</p>
            <ul>
                <li>This is a <strong>one-time</strong> requirement.</li>
                <li>It ensures the custom "MindMap Master" note type is correctly established on the server.</li>
                <li>Future operations will sync normally (bidirectional sync).</li>
            </ul>
        </div>

        <h2 id="operations">&#9733; Basic Operations</h2>
        <h3>Node Manipulation</h3>
        <table>
            <tr><th>Action</th><th>Shortcut</th><th>Description</th></tr>
            <tr><td>Add Child</td><td><span class="shortcut">Tab</span></td><td>Create a new child node.</td></tr>
            <tr><td>Add Sibling</td><td><span class="shortcut">Enter</span></td><td>Create a new node at the same level.</td></tr>
            <tr><td>Edit</td><td><span class="shortcut">Space</span> / <span class="shortcut">Dbl Click</span></td><td>Edit text. <span class="shortcut">Shift+Enter</span> for new line.</td></tr>
            <tr><td>Delete</td><td><span class="shortcut">Delete</span></td><td>Remove node and its children.</td></tr>
            <tr><td>Move</td><td>Drag & Drop</td><td>Drag a node to a new parent.</td></tr>
        </table>

        <h3>Copy, Paste & Smart Paste</h3>
        <ul>
            <li><strong>Copy/Paste Node:</strong> Select a node, press <span class="shortcut">Ctrl+C</span>, select another node, press <span class="shortcut">Ctrl+V</span>. The copied node becomes a <strong>child</strong> of the target.</li>
            <li><strong>Smart Text Paste:</strong> Copy text from anywhere (browser, PDF). Select a node and press <span class="shortcut">Ctrl+V</span>. A new child node containing that text is automatically created and selected.</li>
        </ul>

        <h3>Undo & Redo</h3>
        <ul>
            <li><strong>Undo:</strong> <span class="shortcut">Ctrl+Z</span></li>
            <li><strong>Redo:</strong> <span class="shortcut">Ctrl+Y</span> or <span class="shortcut">Ctrl+Shift+Z</span></li>
        </ul>

        <h2 id="card-linking">&#8644; Card Linking System</h2>
        <div class="feature">
            <h3>Design Philosophy</h3>
            <p>To avoid the cumbersome workflow of creating cards from nodes (like in Obsidian), this plugin is designed for simplicity:</p>
            <ul>
                <li><strong>One-Way Initiation:</strong> Links must be initiated <strong>from the Card</strong> to the Mind Map.</li>
                <li><strong>Bidirectional Sync:</strong>
                    <ul>
                        <li><strong>Mind Map &rarr; Card:</strong> Editing a node updates the <strong>first line</strong> of the card's Front field.</li>
                        <li><strong>Card &rarr; Mind Map:</strong> Editing the first line of the card's Front field updates the Mind Map node.</li>
                    </ul>
                </li>
            </ul>
        </div>

        <div class="warning">
            <strong>&#9888; Auto-Save Warning:</strong> When editing <strong>linked</strong> nodes in the Mind Map, wait for the "Auto-saved" notification in the top right before closing the window to ensure changes sync back to your cards.
        </div>

        <h2 id="config">&#9881; Configuration</h2>
        <p>Go to <strong>Tools &rarr; Add-ons &rarr; Mind Map &rarr; Config</strong>:</p>
        <ul>
            <li><strong>Line Color:</strong> Supports names, Hex, or RGBA. <br>Example: <code>"red"</code>, <code>"#4CAF50"</code>, or <code>"rgba(139, 92, 246, 0.6)"</code>.</li>
            <li><strong>Background:</strong> Copy images to the <code>backgrounds</code> folder and set the filename here. Leave empty <code>""</code> for default.</li>
            <li><strong>Hotkeys:</strong> Customize keys for Save, Refresh, and Focus Root.</li>
            <li><strong>Quick Open:</strong> Set the global shortcut (default <code>Ctrl+M</code>).</li>
        </ul>

        <h2 id="advanced">&#9632; Advanced Features</h2>
        <ul>
            <li><strong>Floating Nodes:</strong> Double-click on empty space to create independent nodes. Great for brainstorming before attaching to the tree.</li>
            <li><strong>MathJax:</strong> Standard syntax supported: <code>\( x^2 \)</code> (inline), <code>\[ E=mc^2 \]</code> (block).</li>
            <li><strong>Active/Inactive:</strong> Mark completed maps as "Inactive" in the Manager to hide them from the card linking menu.</li>
            <li><strong>Fullscreen:</strong> Click the &#9974; icon in the top-left toolbar.</li>
        </ul>

        <h2 id="backup">&#9851; Backup & Recovery</h2>
        <p>Use <strong>Tools &rarr; Mind Map &rarr; Backup & Recovery</strong> to export your maps to JSON.</p>
        <ul>
            <li><strong>Export:</strong> Includes an offline HTML viewer (view in any browser without Anki).</li>
            <li><strong>Import:</strong> Restore data from JSON files.</li>
        </ul>

        <hr style="margin: 30px 0; border: none; border-top: 2px solid #3498db;">
        <p style="text-align: center; color: #95a5a6;">
            <small>Anki Mind Map Plugin | Enhance Learning Through Visualization</small>
        </p>
    </div>
</body>
</html>
"""

    def get_chinese_content(self):
        # Using safe BMP Unicode entities (Decimal) to prevent garbled text
        # 9733=★, 8644=⇄, 9881=⚙, 9632=■ (safe box), 9851=♻
        return """
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <style>
        body {
            font-family: "Microsoft YaHei", "Segoe UI", Arial, sans-serif;
            line-height: 1.6;
            margin: 0;
            padding: 0;
            background: #f9f9f9;
            color: #333;
            display: flex;
            height: 100vh;
            overflow: hidden;
        }
        
        /* 侧边栏样式 */
        .sidebar {
            width: 220px;
            background: #2c3e50;
            color: white;
            padding: 20px;
            display: flex;
            flex-direction: column;
            overflow-y: auto;
            flex-shrink: 0;
        }
        .sidebar h2 {
            color: #ecf0f1;
            font-size: 1.2em;
            margin-top: 0;
            border-bottom: 2px solid #34495e;
            padding-bottom: 10px;
        }
        .nav-link {
            color: #bdc3c7;
            text-decoration: none;
            padding: 8px 0;
            display: block;
            transition: color 0.3s;
            font-size: 0.95em;
        }
        .nav-link:hover {
            color: #ffffff;
            font-weight: bold;
        }
        

        .main-content {
            flex-grow: 1;
            padding: 20px 40px;
            overflow-y: auto;
            scroll-behavior: smooth;
        }
        
        h1 { color: #2c3e50; border-bottom: 3px solid #3498db; padding-bottom: 10px; margin-top: 0; }
        h2 { color: #34495e; margin-top: 30px; border-left: 4px solid #3498db; padding-left: 10px; background: linear-gradient(to right, #f0f4f8, #ffffff); padding: 10px; border-radius: 3px; }
        h3 { color: #2980b9; margin-top: 20px; }
        
        .shortcut {
            background: #3498db;
            color: white;
            padding: 2px 6px;
            border-radius: 4px;
            font-family: "Consolas", monospace;
            font-size: 0.9em;
            font-weight: bold;
        }
        .feature {
            background: linear-gradient(to right, #e8f5e9, #f1fdf3);
            padding: 15px;
            margin: 15px 0;
            border-radius: 5px;
            border-left: 4px solid #4caf50;
        }
        .tip {
            background: linear-gradient(to right, #fff3cd, #fffaf0);
            padding: 12px;
            margin: 10px 0;
            border-radius: 5px;
            border-left: 4px solid #ff9800;
        }
        .warning {
            background: linear-gradient(to right, #ffebee, #fff5f6);
            padding: 12px;
            margin: 10px 0;
            border-radius: 5px;
            border-left: 4px solid #f44336;
        }
        .warning strong { color: #c0392b; }
        
        ul { padding-left: 20px; }
        li { margin: 6px 0; }
        code {
            background: #f5f5f5;
            padding: 2px 6px;
            border-radius: 3px;
            font-family: "Consolas", monospace;
            border: 1px solid #ddd;
            color: #e74c3c;
        }
        
        table {
            width: 100%;
            border-collapse: collapse;
            margin: 15px 0;
            box-shadow: 0 2px 4px rgba(0,0,0,0.05);
            border-radius: 5px;
            overflow: hidden;
        }
        th, td {
            border: none;
            border-bottom: 1px solid #e8e8e8;
            padding: 10px;
            text-align: left;
        }
        th {
            background: linear-gradient(135deg, #3498db 0%, #5dade2 100%);
            color: white;
            font-weight: 600;
        }
        tr:nth-child(even) { background: #fafbfc; }
        tr:hover { background: #f0f7ff; }
    </style>
</head>
<body>
    <div class="sidebar">
        <h2>&#128214; 目录导航</h2>
        <a href="#quick-start" class="nav-link">&#9889; 快速开始流程</a>
        <a href="#setup-sync" class="nav-link">&#9729; 首次同步设置</a>
        <a href="#operations" class="nav-link">&#9733; 基础操作</a>
        <a href="#card-linking" class="nav-link">&#8644; 卡片关联</a>
        <a href="#config" class="nav-link">&#9881; 插件配置</a>
        <a href="#advanced" class="nav-link">&#9632; 高级功能</a>
        <a href="#backup" class="nav-link">&#9851; 备份与恢复</a>
    </div>

    <div class="main-content">
        <h1>&#9733; 思维导图插件使用指南</h1>
        
        <div id="quick-start" class="feature">
            <h2 style="margin-top:0;">&#9889; 快速开始流程</h2>
            <p>按照以下步骤，快速建立你的第一张关联导图：</p>
            <ol>
                <li><strong>创建导图：</strong>点击菜单 <code>工具 &rarr; Mind Map &rarr; Mind Map Manager</code>，点击 <strong>New</strong> 创建一个新导图。</li>
                <li><strong>建立关联：</strong>进入 Anki 的“添加”窗口或“浏览器”，点击编辑器工具栏上的 <strong>MM</strong> 按钮，选择刚才创建的导图。</li>
                <li><strong>编辑内容：</strong>注意！修改卡片<strong>“正面 (Front)”字段的第一行文字</strong>。这行文字将直接对应成为导图中的节点内容。</li>
                <li><strong>刷新查看：</strong>回到思维导图界面，按下快捷键 <strong>F5</strong>，你就会看到刚才关联的卡片已经作为一个节点出现了。</li>
                <li><strong>双向跳转：</strong>
                    <ul>
                        <li>在导图中 <strong>右键点击节点</strong> &rarr; 选择“Jump to Card”可跳转到浏览器。</li>
                        <li>在学习/复习卡片时，点击右上角的 <strong>导图徽章</strong> 可跳转回导图节点。</li>
                    </ul>
                </li>
            </ol>
            <div class="tip">
                <strong>&#10024; 小技巧：</strong> 并非所有节点都需要关联卡片。未关联的节点可以作为结构辅助（父节点、分类标签等），你可以无限制地自由编辑它们！
            </div>
        </div>

        <h2 id="setup-sync">&#9729; 重要：首次同步设置</h2>
        <div class="warning">
            <strong>&#9888; 新用户必读</strong>
            <p>安装本插件或首次使用激活/停用功能后，Anki 会检测到数据库结构的变更。</p>
            <p>当系统提示同步时，请务必选择：<strong>“上传到 AnkiWeb”</strong>。</p>
            <ul>
                <li>这只是<strong>一次性</strong>的要求。</li>
                <li>这确保了自定义的“MindMap Master”笔记类型和字段在服务器上正确建立。</li>
                <li>之后的任何操作（添加节点、关联卡片等）均可正常双向同步。</li>
            </ul>
        </div>

        <h2 id="operations">&#9733; 基础操作</h2>
        <h3>节点操作</h3>
        <table>
            <tr>
                <th>操作</th>
                <th>快捷键</th>
                <th>说明</th>
            </tr>
            <tr>
                <td>添加子节点</td>
                <td><span class="shortcut">Tab</span></td>
                <td>在选中节点下创建子节点。</td>
            </tr>
            <tr>
                <td>添加同级节点</td>
                <td><span class="shortcut">Enter</span></td>
                <td>在同一层级创建兄弟节点。</td>
            </tr>
            <tr>
                <td>编辑</td>
                <td><span class="shortcut">空格</span> / <span class="shortcut">双击</span></td>
                <td>编辑文本。<span class="shortcut">Shift+Enter</span> 换行。</td>
            </tr>
            <tr>
                <td>删除</td>
                <td><span class="shortcut">Delete</span></td>
                <td>删除节点及其所有子节点。</td>
            </tr>
            <tr>
                <td>移动</td>
                <td>拖拽</td>
                <td>将节点拖动到新的父节点下。</td>
            </tr>
        </table>

        <h3>复制、粘贴与智能粘贴</h3>
        <ul>
            <li><strong>复制/粘贴节点：</strong> 选中节点按 <span class="shortcut">Ctrl+C</span>，选中目标节点按 <span class="shortcut">Ctrl+V</span>。被复制的节点将成为目标节点的<strong>子节点</strong>。</li>
            <li><strong>智能文本粘贴：</strong> 如果你从 Anki 外部复制了一段文本，在节点上按 <span class="shortcut">Ctrl+V</span>，系统会自动创建一个包含该文本的子节点并选中它，方便连续记录。</li>
        </ul>

        <h3>撤销与重做</h3>
        <ul>
            <li><strong>撤销：</strong> <span class="shortcut">Ctrl+Z</span></li>
            <li><strong>重做：</strong> <span class="shortcut">Ctrl+Y</span> 或 <span class="shortcut">Ctrl+Shift+Z</span></li>
        </ul>

        <h2 id="card-linking">&#8644; 卡片关联系统详解</h2>
        <div class="feature">
            <h3>双向同步机制</h3>
            <p>为了适配所有卡片类型并保持简洁，本插件采用以下设计逻辑：</p>
            <ul>
                <li><strong>单向发起：</strong> 只能从 <strong>卡片编辑器</strong> 发起链接到 <strong>思维导图</strong>。
                    <br><em>(注：为了避免像 Obsidian 那样从节点创建链接的繁琐操作，本插件特意设计为单向发起，专注于快速归纳)</em>
                </li>
                <li><strong>内容同步：</strong>
                    <ul>
                        <li><strong>思维导图 &rarr; 卡片：</strong> 修改节点内容，会自动更新卡片“正面”字段的<strong>第一行</strong>。</li>
                        <li><strong>卡片 &rarr; 思维导图：</strong> 修改卡片“正面”字段的第一行，会自动更新对应的导图节点。</li>
                    </ul>
                </li>
            </ul>
        </div>

        <div class="warning">
            <strong>&#9888; 自动保存提示：</strong> 在思维导图中编辑<strong>已关联</strong>的节点时，请务必等待右上角的 "Auto-saved" 提示出现后再关闭窗口，以确保更改成功同步回卡片。
        </div>

        <h2 id="config">&#9881; 插件配置详解</h2>
        <p>前往 <strong>工具 &rarr; 插件 &rarr; Mind Map &rarr; Config</strong> 进行自定义：</p>
        
        <h3>1. 快捷键 (Hotkeys)</h3>
        <p>自定义导图编辑器内的操作按键：</p>
        <pre><code>"hotkeys": {
    "save": "Ctrl+S",      // 手动保存
    "refresh": "F5",       // 刷新数据
    "focus_root": "Ctrl+R" // 聚焦回根节点
}</code></pre>

        <h3>2. 快速打开快捷键</h3>
        <p>修改在 Anki 全局界面打开上一个导图的快捷键：</p>
        <code>"quick_open_shortcut": "Ctrl+M"</code>

        <h3>3. 线条颜色 (Line Color)</h3>
        <p>自定义连接线的颜色。支持颜色名称、Hex 代码或 RGBA 格式。</p>
        <ul>
            <li><strong>示例：</strong>
                <ul>
                    <li><code>"red"</code> (纯红色)</li>
                    <li><code>"#4CAF50"</code> (十六进制绿色)</li>
                    <li><code>"rgba(139, 92, 246, 0.6)"</code> (默认：紫色半透明)</li>
                </ul>
            </li>
        </ul>

        <h3>4. 背景图片 (Background Image)</h3>
        <p>将图片文件 (jpg/png) 放入插件目录下的 <code>backgrounds</code> 文件夹。</p>
        <code>"background_image": "galaxy.jpg"</code>
        <p><em>(留空 <code>""</code> 则使用默认米色背景)</em></p>

        <h2 id="advanced">&#9632; 高级功能</h2>
        <ul>
            <li><strong>浮动节点：</strong> 在空白处双击即可创建不依附于树的独立节点。适合头脑风暴，之后可拖拽连接到主树上。</li>
            <li><strong>数学公式：</strong> 支持标准 Anki 格式：<code>\( x^2 \)</code> (行内) 或 <code>\[ E=mc^2 \]</code> (块级)。</li>
            <li><strong>激活/停用：</strong> 在 <em>Mind Map Manager</em> 中，可以将已完成的导图设为“Inactive”，这样它们就不会出现在卡片关联菜单中，保持菜单整洁。</li>
            <li><strong>全屏模式：</strong> 点击左上角的 &#9974; 图标可进入沉浸式全屏模式。</li>
        </ul>

        <h2 id="backup">&#9851; 备份与恢复</h2>
        <p>位于：<strong>工具 &rarr; Mind Map &rarr; Backup & Recovery</strong>。</p>
        <ul>
            <li><strong>导出：</strong> 将思维导图导出为 JSON 文件。附带一个独立的 HTML 查看器，无需 Anki 也能在浏览器中查看（方便分享）。</li>
            <li><strong>导入：</strong> 从 JSON 文件恢复数据。</li>
        </ul>
        <p><em>提示：所有数据都作为 "MindMap Master" 类型的笔记存储在你的集合中，删除插件不会丢失数据。</em></p>

        <hr style="margin: 30px 0; border: none; border-top: 2px solid #3498db;">
        <p style="text-align: center; color: #95a5a6;">
            <small>Anki 思维导图插件 | 通过可视化增强学习</small>
        </p>
    </div>
</body>
</html>
"""

def show_usage():
    dialog = UsageDialog(mw)
    dialog.exec()