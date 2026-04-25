import json
import os
import base64
from aqt import mw
from aqt.qt import *
from aqt.webview import AnkiWebView
from aqt.qt import QDialog, QVBoxLayout
from aqt.utils import showInfo

class MindMapDialog(QDialog):
    PREVIEW_TOOLBAR_HEIGHT: int = 34
    PREVIEW_TOOLBAR_MARGIN: int = 6
    PREVIEW_TOOLBAR_SPACING: int = 6

    @classmethod
    def open_instance(cls, mw, note_id, focus_node_id=None):
        """Unified window management: open or focus existing mindmap window"""
        # Initialize editor list
        if not hasattr(mw, 'mindmap_editors'):
            mw.mindmap_editors = []
        
        # Check if already open
        for editor in mw.mindmap_editors:
            if editor.note_id == note_id:
                editor.show()
                editor.raise_()
                editor.activateWindow()
                # Focus on specific node if needed
                if focus_node_id:
                    editor.web.eval(f"if(typeof focusNode === 'function') focusNode('{focus_node_id}');")
                return editor
        
        # Create new window
        dialog = cls(mw, note_id, focus_node_id)
        mw.mindmap_editors.append(dialog)
        dialog.show()
        
        # Remove from list when window closes
        dialog.finished.connect(lambda: mw.mindmap_editors.remove(dialog) if dialog in mw.mindmap_editors else None)
        
        return dialog
    
    def __init__(self, mw, note_id, focus_node_id=None):
        super().__init__(None)
        self.setWindowFlags(Qt.WindowType.Window)
        self.mw = mw
        self.note_id = note_id
        self.focus_node_id = focus_node_id
        self.note = mw.col.get_note(note_id)
        self.setWindowTitle(f"Mind Map Editor - {self.note['Title']}")
        self.resize(1024, 768)
        
        # Save this as last opened mind map
        config = mw.addonManager.getConfig(__name__) or {}
        config['last_mindmap_id'] = note_id
        mw.addonManager.writeConfig(__name__, config)
        
        # Validate and clean up orphaned links before opening
        from . import card_linker
        card_linker.validate_and_cleanup_mindmap(self.note)
        self._cleanup_orphaned_links()
        
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        
        # Initialize WebView
        self.web = AnkiWebView(parent=self)
        self.web.set_bridge_command(self._on_bridge_cmd, self)
        self.layout.addWidget(self.web)
        
        # Load the editor assets
        addon_dir = os.path.dirname(__file__)
        web_dir = os.path.join(addon_dir, "web")
        
        def read_asset(filename):
            with open(os.path.join(web_dir, filename), 'r', encoding='utf-8') as f:
                return f.read()

        def read_assets(filenames):
            return "\n".join(read_asset(filename) for filename in filenames)

        def read_css_entry(filename):
            """Inline split CSS imports because Anki embeds assets in a style tag."""
            content = read_asset(filename)
            expanded = []
            for line in content.splitlines():
                stripped = line.strip()
                if stripped.startswith("@import") and "url(" in stripped:
                    import_path = stripped.split("url(", 1)[1].split(")", 1)[0].strip("\"'")
                    import_path = import_path.lstrip("./").replace("/", os.sep)
                    expanded.append(read_asset(import_path))
                else:
                    expanded.append(line)
            return "\n".join(expanded)

        try:
            # Load jsMind assets
            jsmind_js = read_assets([
                "jsmind.core.js",
                "jsmind.model.js",
                "jsmind.format.js",
                "jsmind.util.js",
                "jsmind.data-provider.js",
                "jsmind.layout-provider.js",
                "jsmind.view-provider.js",
                "jsmind.shortcut-plugin.js",
                "jsmind.js",
            ])
            jsmind_draggable = read_assets([
                "jsmind.draggable.options.js",
                "jsmind.draggable.canvas.js",
                "jsmind.draggable.highlight.js",
                "jsmind.draggable.shadow.js",
                "jsmind.draggable.timer.js",
                "jsmind.draggable.lookup.js",
                "jsmind.draggable.autoscroll.js",
                "jsmind.draggable.move.js",
                "jsmind.draggable.events.js",
                "jsmind.draggable.core.js",
            ])
            jsmind_css = read_css_entry("jsmind.css")
            style_css = read_css_entry("style.css")
            main_js = read_assets([
                "main/state.js",
                "main/jsmind_dom.js",
                "main/hotkeys.js",
                "main/ui_feedback.js",
                "main/text_formatting.js",
                "main/app_events.js",
                "main/floating_nodes.js",
                "main/persistence.js",
                "main/mathjax.js",
                "main/node_commands.js",
                "main/persistence_reload.js",
                "main/selection.js",
                "main/summary_braces.js",
                "main/boundaries.js",
                "main/navigation.js",
                "main/node_editor.js",
                "main/backend_links.js",
                "main/clipboard.js",
                "main/app_events_tail.js",
            ])
            
            # Prepare data for injection
            data_json = self.note['Data']
            if not data_json:
                data_json = "{}"
            
            # Load background image if configured
            bg_style = ""
            config = mw.addonManager.getConfig(__name__) or {}
            bg_filename = config.get('background_image', '')
            if bg_filename:
                bg_path = os.path.join(addon_dir, 'backgrounds', bg_filename)
                if os.path.exists(bg_path):
                    try:
                        with open(bg_path, 'rb') as img_file:
                            img_data = base64.b64encode(img_file.read()).decode('utf-8')
                            ext = os.path.splitext(bg_filename)[1].lower()
                            mime_type = 'image/jpeg' if ext in ['.jpg', '.jpeg'] else 'image/png'
                            
                            overlay = config.get('background_overlay', '')
                            if overlay:
                                bg_css = f"linear-gradient({overlay}, {overlay}), url(data:{mime_type};base64,{img_data})"
                            else:
                                bg_css = f"url(data:{mime_type};base64,{img_data})"

                            bg_style = f"""
                            .jsmind-inner {{
                                background-image: {bg_css} !important;
                            }}
                            """
                    except Exception as e:
                        print(f"Error loading background image: {e}")
            
            # Construct HTML with inlined assets and data
            html = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <meta charset="utf-8">
                <style>
                {jsmind_css}
                {style_css}
                {bg_style}

                .toolbar {{
                    position: fixed;
                    top: 5px;    
                    left: 5px;     
                    z-index: 2000;
                    padding: 0;
                    margin: 0;
                    background: transparent;
                    box-shadow: none;    
                    width: auto;
                    height: auto;
                }}

                .toolbar button {{
                    background: transparent !important; 
                    color: #aaa;   
                    border: none;
                    padding: 2px 4px; 
                    border-radius: 3px;
                    cursor: pointer;
                    font-weight: normal;
                    font-size: 14px; 
                    line-height: 1;
                    transition: all 0.2s;
                    opacity: 0.4;   
                    box-shadow: none;
                }}
                
                .toolbar button:hover {{
                    color: #333;    
                    opacity: 1;
                    background: rgba(0,0,0,0.05) !important; 
                }}

                .menu-container {{
                    position: relative;
                    display: inline-block;
                }}
                .menu-content {{
                    display: none;
                    position: absolute;
                    top: 100%;
                    left: 0;
                    background-color: white;
                    min-width: 160px;
                    box-shadow: 0 2px 10px rgba(0,0,0,0.1);
                    border-radius: 4px;
                    padding: 5px 0;
                    z-index: 2001;
                    border: 1px solid #eee;
                    margin-top: 5px;
                }}
                .menu-content.show {{
                    display: block;
                }}
                .menu-item {{
                    padding: 8px 12px;
                    cursor: pointer;
                    display: flex;
                    align-items: center;
                    font-size: 13px;
                    color: #333;
                }}
                .menu-item:hover {{
                    background-color: #f5f5f5;
                }}
                .menu-item input {{
                    margin-right: 8px;
                }}
                .menu-divider {{
                    height: 1px;
                    background-color: #eee;
                    margin: 4px 0;
                }}
                
                html, body {{
                    margin: 0;
                    padding: 0;
                    width: 100%;
                    height: 100%;
                    overflow: hidden;
                }}
                
                #jsmind_container {{
                    position: absolute;
                    top: 0 !important;
                    left: 0;
                    right: 0;
                    bottom: 0;
                    height: 100% !important;
                    margin: 0;
                    padding: 0;
                }}
                
                :fullscreen #jsmind_container {{
                    top: 0 !important;
                    height: 100% !important;
                }}
                
                #auto-save-status {{
                    position: fixed;
                    top: 55px;
                    right: 10px;
                    padding: 5px 10px;
                    background: rgba(40, 167, 69, 0.9);
                    color: white;
                    border-radius: 3px;
                    font-size: 12px;
                    opacity: 0;
                    transition: opacity 0.3s;
                    z-index: 1000;
                }}
                
                /* Floating nodes styles */
                jmnode[nodeid^="floating_"] {{
                    transition: border-color 0.2s, box-shadow 0.2s;
                }}
                jmnode[nodeid^="floating_"]:hover {{
                    box-shadow: 0 4px 12px rgba(0,0,0,0.3) !important;
                }}
                jmnode[nodeid^="floating_"].attaching {{
                    border-color: #4dc4ff !important;
                    animation: pulse 0.5s infinite;
                }}
                @keyframes pulse {{
                    0%, 100% {{ transform: scale(1); }}
                    50% {{ transform: scale(1.05); }}
                }}
                </style>
                <script>
                window.MathJax = {{
                    tex: {{
                        inlineMath: [['\\\\(', '\\\\)'], ['$', '$']],
                        displayMath: [['\\\\[', '\\\\]'], ['$$', '$$']]
                    }},
                    svg: {{
                        fontCache: 'global'
                    }}
                }};
                </script>
                <script src="https://cdn.jsdelivr.net/npm/mathjax@3/es5/tex-svg.js" async></script>
                <script>
                {jsmind_js}
                </script>
                <script>
                {jsmind_draggable}
                </script>
            </head>
            <body>
                <div class="toolbar">
                    <div class="menu-container">
                        <button onclick="toggleMenu()" title="Menu">☰</button>
                        
                        <div id="main-menu" class="menu-content">
                            <div style="padding: 5px 12px; font-weight:bold; color:#666; font-size:11px;">LINK ACTION</div>

                            <label class="menu-item" onclick="toggleReadOnly()">
                                <input type="checkbox" id="readonly_toggle"> Read-Only Mode
                            </label>
                            <div class="menu-divider"></div>
                            
                            <label class="menu-item" onclick="setJumpMode('preview')">
                                <input type="radio" name="jump_mode" id="mode_preview" checked> Preview Card
                            </label>
                            
                            <label class="menu-item" onclick="setJumpMode('browser')">
                                <input type="radio" name="jump_mode" id="mode_browser"> Card Browser
                            </label>
                            
                            <div class="menu-divider"></div>
                            
                            <div class="menu-item" onclick="toggleFullscreen()">
                                ⛶ Toggle Fullscreen
                            </div>
                        </div>
                    </div>
                </div>
                
                <div id="jsmind_container" tabindex="0" style="background: #f4f4f4; outline: none; overflow: auto;">
                </div>
                
                <div id="auto-save-status">Auto-saved</div>
                
                <script>
                {main_js}
                </script>
                
                <script>
                // Inject hotkey configuration
                var hotkeyConfigFromPython = {json.dumps(config.get('hotkeys', {}))};
                var lineColorFromPython = {json.dumps(config.get('line_color', 'rgba(139, 92, 246, 0.6)'))};
                var braceColorFromPython = {json.dumps(config.get('brace_color', '#3b82f6'))};
                var boundaryColorFromPython = {json.dumps(config.get('boundary_color', '#ef4444'))};
                var enableFloatingNodesFromPython = {json.dumps(config.get('enable_floating_nodes', True))};
                var initialJumpMode = {json.dumps(config.get('jump_mode', 'preview'))};
                
                if (hotkeyConfigFromPython && Object.keys(hotkeyConfigFromPython).length > 0) {{
                    // Merge user config with defaults so new hotkeys get sensible fallbacks.
                    hotkeyConfig = Object.assign({{}}, hotkeyConfig, hotkeyConfigFromPython);
                    console.log("Loaded hotkey config:", hotkeyConfig);
                }}
                
                // Inject data directly
                var initialData = {data_json};
                var initialFocusId = "{self.focus_node_id or ''}";
                
                // Menu Logic
                function toggleMenu() {{
                    var menu = document.getElementById("main-menu");
                    if (menu.style.display === "block") {{
                        menu.style.display = "none";
                    }} else {{
                        menu.style.display = "block";
                    }}
                }}

                // Close menu when clicking outside
                document.addEventListener('click', function(event) {{
                    var container = document.querySelector('.menu-container');
                    if (!container.contains(event.target)) {{
                        document.getElementById("main-menu").style.display = "none";
                    }}
                }});

                function setJumpMode(mode) {{
                    // Update UI
                    document.getElementById('mode_' + mode).checked = true;
                    // Save to Anki config
                    pycmd("update_config:jump_mode=" + mode);
                }}

                // Initialize UI based on config
                if (typeof initialJumpMode !== 'undefined') {{
                    document.getElementById('mode_' + initialJumpMode).checked = true;
                }}

                window.onload = function() {{
                    console.log("Window loaded. Starting init...");
                    if (typeof initEditor === 'function') {{
                        initEditor(initialData);
                        
                        if (initialFocusId) {{
                            setTimeout(function() {{
                                if (typeof focusNode === 'function') {{
                                    focusNode(initialFocusId);
                                }}
                            }}, 800);
                        }}
                    }} else {{
                        console.error("Error: initEditor function not found!");
                    }}
                }};
                </script>
            </body>
            </html>
            """
            
            # Set base URL
            base_url = QUrl.fromLocalFile(os.path.join(web_dir, "index.html"))
            self.web.setHtml(html, base_url)

            self.undo_shortcut = QShortcut(QKeySequence("Ctrl+Z"), self)
            self.undo_shortcut.activated.connect(lambda: self.web.eval("window.undo();"))

            self.redo_shortcut = QShortcut(QKeySequence("Ctrl+Y"), self)
            self.redo_shortcut.activated.connect(lambda: self.web.eval("window.redo();"))
            
            self.redo_shortcut_alt = QShortcut(QKeySequence("Ctrl+Shift+Z"), self)
            self.redo_shortcut_alt.activated.connect(lambda: self.web.eval("window.redo();"))

            # Formatting shortcuts for node edit mode (configurable via add-on config.json -> hotkeys).
            config = self.mw.addonManager.getConfig(__name__) or {}
            hotkeys = config.get("hotkeys", {}) if isinstance(config, dict) else {}

            def _bind_formatting_hotkey(config_key: str, action: str) -> None:
                seq_str = hotkeys.get(config_key)
                if not isinstance(seq_str, str) or not seq_str.strip():
                    return

                shortcut = QShortcut(QKeySequence(seq_str), self)
                shortcut.setContext(Qt.ShortcutContext.WidgetWithChildrenShortcut)
                shortcut.activated.connect(
                    lambda a=action: self.web.eval(
                        f"window.applyTextFormatting && window.applyTextFormatting({json.dumps(a)});"
                    )
                )
                setattr(self, f"{config_key}_shortcut", shortcut)

            _bind_formatting_hotkey("bold", "bold")
            _bind_formatting_hotkey("italic", "italic")
            _bind_formatting_hotkey("inline_code", "inline_code")
            _bind_formatting_hotkey("code_block", "code_block")
            
        except Exception as e:
            self.web.setHtml(f"<h1>Error loading assets: {e}</h1>")

    def _on_bridge_cmd(self, cmd: str) -> None:
        if cmd.startswith("save:"):
            self._handle_save(cmd[5:])
        elif cmd.startswith("update_config:"):
            self._handle_update_config(cmd[14:])
        elif cmd == "close":
            self.close()
        elif cmd.startswith("jump_to_card:"):
            self._handle_jump_to_card(cmd[13:])
        elif cmd == "refresh_data":
            self._handle_refresh()
        elif cmd == "toggle_fullscreen":
            self._handle_toggle_fullscreen()
        elif cmd == "get_editable_maps":
            self._handle_get_editable_maps()
        elif cmd.startswith("create_map_link:"):
            self._handle_create_map_link(cmd[16:])
        elif cmd.startswith("jump_to_map:"):
            self._handle_jump_to_map(cmd[12:])
        elif cmd.startswith("delete_map_link:"):
            self._handle_delete_map_link(cmd[16:])
        elif cmd.startswith("unlink_map:"):
            self._handle_unlink_map(cmd[11:])
        else:
            print(f"Unknown command: {cmd}")
    
    def _on_preview_bridge_cmd(self, cmd: str) -> None:
        """Handle commands from the preview window"""
        if cmd.startswith("save_mode:"):
            mode = cmd.split(":", 1)[1]
            config = self.mw.addonManager.getConfig(__name__) or {}
            config['preview_mode'] = mode
            self.mw.addonManager.writeConfig(__name__, config)

    def _handle_update_config(self, params: str):
            """Handle configuration updates from UI"""
            try:
                key, value = params.split('=', 1)
                config = self.mw.addonManager.getConfig(__name__) or {}
                config[key] = value
                self.mw.addonManager.writeConfig(__name__, config)
            except Exception as e:
                print(f"Error updating config: {e}")

    def _handle_jump_to_card(self, note_id_str):
            try:
                nid = int(note_id_str)
                config = self.mw.addonManager.getConfig(__name__) or {}
                mode = config.get('jump_mode', 'preview')

                if mode == 'browser':
                    from aqt import dialogs
                    browser = dialogs.open("Browser", self.mw)
                    browser.search_for(f"nid:{nid}")
                else:
                    self._open_card_preview(nid)
                    
            except ValueError:
                print(f"Invalid note ID: {note_id_str}")
            except Exception as e:
                from aqt.utils import showInfo
                showInfo(f"Error jumping to card: {e}")


    def _open_card_preview(self, nid):
        """Open single instance card preview window (Fixed: Safe JSON injection)"""
        try:
            # 1. Get note content
            try:
                note = self.mw.col.get_note(nid)
            except Exception:
                from aqt.utils import showInfo
                showInfo(f"Note {nid} not found.")
                return

            cards = note.cards()
            if not cards:
                return
            card = cards[0]
            
            # 2. Render content (Front and Back)
            try:
                content = card.render_output()
                q_text = content.q
                a_text = content.a
            except (AttributeError, Exception):
                q_text = card.q()
                a_text = card.a()
            
            # Serialize content to JSON and ESCAPE closing tags
            # This prevents </script> in card content from breaking the viewer
            import json
            q_json = json.dumps(q_text).replace("</", "<\\/")
            a_json = json.dumps(a_text).replace("</", "<\\/")
            
            # Get saved preference
            config = self.mw.addonManager.getConfig(__name__) or {}
            current_mode = config.get('preview_mode', 'all')

            # 3. Define HTML Template (Standard string, NO f-string to avoid conflicts)
            html_template = """
            <!DOCTYPE html>
            <html>
            <head>
                <meta charset="utf-8">
                <style>
                    body { 
                        margin: 0; 
                        padding: 0; 
                        display: flex; 
                        flex-direction: column; 
                        height: 100vh; 
                        font-family: -apple-system, system-ui, BlinkMacSystemFont, "Segoe UI", Roboto, Arial, sans-serif;
                        background: white;
                    }
                    .controls {
                        background: #f8f9fa; 
                        border-bottom: 1px solid #e9ecef; 
                        padding: 10px;
                        display: flex; 
                        justify-content: center; 
                        gap: 10px; 
                        flex-shrink: 0;
                        user-select: none;
                    }
                    .btn {
                        padding: 6px 16px; 
                        border: 1px solid #ced4da; 
                        background: white;
                        border-radius: 20px; 
                        cursor: pointer; 
                        font-size: 13px;
                        font-weight: 500;
                        color: #495057;
                        transition: all 0.2s ease;
                    }
                    .btn:hover { background: #e9ecef; }
                    .btn.active { 
                        background: #007bff; 
                        color: white; 
                        border-color: #007bff; 
                        box-shadow: 0 2px 4px rgba(0,123,255,0.2);
                    }
                    #content {
                        flex-grow: 1; 
                        padding: 20px; 
                        overflow-y: auto; 
                        display: flex; 
                        flex-direction: column; 
                        align-items: center;
                    }
                    .card { 
                        font-size: 18px; 
                        line-height: 1.5; 
                        max-width: 800px; 
                        width: 100%; 
                        text-align: center; 
                        color: #212529;
                    }
                    hr { margin: 20px 0; border: 0; border-top: 1px solid #dee2e6; width: 100%; }
                    img { max-width: 100%; height: auto; border-radius: 4px; }
                    
                    /* Custom Scrollbar */
                    ::-webkit-scrollbar { width: 8px; }
                    ::-webkit-scrollbar-track { background: transparent; }
                    ::-webkit-scrollbar-thumb { background: #cbd5e0; border-radius: 4px; }
                    ::-webkit-scrollbar-thumb:hover { background: #a0aec0; }
                </style>
                <script>
                    var frontContent = VAR_FRONT_CONTENT;
                    var allContent = VAR_ALL_CONTENT;
                    var currentMode = "VAR_CURRENT_MODE";

                    function setMode(mode) {
                        currentMode = mode;
                        var contentDiv = document.getElementById('content');
                        var btnFront = document.getElementById('btn-front');
                        var btnAll = document.getElementById('btn-all');

                        if (mode === 'front') {
                            contentDiv.innerHTML = "<div class='card'>" + frontContent + "</div>";
                            btnFront.classList.add('active');
                            btnAll.classList.remove('active');
                        } else {
                            contentDiv.innerHTML = "<div class='card'>" + allContent + "</div>";
                            btnFront.classList.remove('active');
                            btnAll.classList.add('active');
                        }
                        // Save config back to Python
                        pycmd("save_mode:" + mode);
                    }

                    window.onload = function() {
                        setMode(currentMode);
                    };
                </script>
            </head>
            <body>
                <div class="controls">
                    <button id="btn-front" class="btn" onclick="setMode('front')">Front Only</button>
                    <button id="btn-all" class="btn" onclick="setMode('all')">All Content</button>
                </div>
                <div id="content"></div>
            </body>
            </html>
            """
            
            # 4. Inject Data safely
            html = html_template.replace("VAR_FRONT_CONTENT", q_json)
            html = html.replace("VAR_ALL_CONTENT", a_json)
            html = html.replace("VAR_CURRENT_MODE", current_mode)

            # 5. Window Management (Independent Window)
            dialog = getattr(self, '_preview_dialog', None)
            
            try:
                if dialog:
                    dialog.isVisible() 
            except RuntimeError:
                dialog = None

            if not dialog:
                dialog = QDialog(None) # None parent for independent window
                dialog.setWindowFlags(Qt.WindowType.Window)
                dialog.setWindowTitle("Card Preview")
                dialog.setMinimumSize(450, 600)
                
                layout = QVBoxLayout(dialog)
                layout.setContentsMargins(0,0,0,0)
                layout.setSpacing(0)

                # Native toolbar so the user can pin/unpin the preview window (always on top).
                toolbar = QWidget(dialog)
                toolbar.setFixedHeight(self.PREVIEW_TOOLBAR_HEIGHT)
                toolbar_layout = QHBoxLayout(toolbar)
                toolbar_layout.setContentsMargins(
                    self.PREVIEW_TOOLBAR_MARGIN,
                    self.PREVIEW_TOOLBAR_MARGIN,
                    self.PREVIEW_TOOLBAR_MARGIN,
                    self.PREVIEW_TOOLBAR_MARGIN,
                )
                toolbar_layout.setSpacing(self.PREVIEW_TOOLBAR_SPACING)
                toolbar_layout.addStretch(1)

                pin_btn = QToolButton(toolbar)
                pin_btn.setCheckable(True)
                pin_btn.setToolTip("Always on top")
                toolbar_layout.addWidget(pin_btn, 0, Qt.AlignmentFlag.AlignRight)
                
                from aqt.webview import AnkiWebView
                dialog._web = AnkiWebView(parent=dialog)
                dialog._web.set_bridge_command(self._on_preview_bridge_cmd, dialog)

                layout.addWidget(toolbar)
                layout.addWidget(dialog._web)

                def apply_pinned_state(checked: bool) -> None:
                    self._set_window_always_on_top(dialog, checked)
                    cfg = self.mw.addonManager.getConfig(__name__) or {}
                    cfg["preview_pinned"] = bool(checked)
                    self.mw.addonManager.writeConfig(__name__, cfg)
                    pin_btn.setText("Unpin" if checked else "Pin")

                # Restore last pin state for this preview window.
                cfg = self.mw.addonManager.getConfig(__name__) or {}
                pinned = bool(cfg.get("preview_pinned", False))
                pin_btn.setChecked(pinned)
                pin_btn.setText("Unpin" if pinned else "Pin")
                apply_pinned_state(pinned)
                pin_btn.toggled.connect(apply_pinned_state)
                
                self.finished.connect(dialog.close)
                self._preview_dialog = dialog
            
            # 6. Update and Show
            title = note['Title'] if 'Title' in note else 'Card Preview'
            dialog.setWindowTitle(title)
            dialog._web.setHtml(html)
            
            if not dialog.isVisible():
                dialog.show()
            
            dialog.raise_()
            dialog.activateWindow()
            
        except Exception as e:
            from aqt.utils import showInfo
            showInfo(f"Preview error: {e}")                        

    def _set_window_always_on_top(self, window: QWidget, enabled: bool) -> None:
        """Toggle the native always-on-top flag and keep the window stable."""
        flags = window.windowFlags()
        if enabled:
            flags |= Qt.WindowType.WindowStaysOnTopHint
        else:
            flags &= ~Qt.WindowType.WindowStaysOnTopHint

        was_visible = window.isVisible()
        window.setWindowFlags(flags)
        if was_visible:
            # Re-show is required for some platforms for new flags to take effect.
            window.show()
            window.raise_()
            window.activateWindow()

    def _handle_toggle_fullscreen(self):
        """Toggle fullscreen mode"""
        if self.isFullScreen():
            self.showNormal()
        else:
            self.showFullScreen()


    def _cleanup_orphaned_links(self):
        """Remove links from cards that point to non-existent nodes, and remove noteId from nodes whose cards are deleted"""
        try:
            # Get all node IDs from the mindmap
            data_str = self.note['Data']
            if not data_str:
                return
            
            data = json.loads(data_str)
            existing_node_ids = set()
            nodes_with_note_ids = {}  # node_id -> noteId mapping
            
            # Recursively collect all node IDs and noteIds
            def collect_node_info(node):
                if isinstance(node, dict):
                    if 'id' in node:
                        existing_node_ids.add(node['id'])
                        if 'noteId' in node:
                            nodes_with_note_ids[node['id']] = node['noteId']
                    if 'children' in node:
                        for child in node['children']:
                            collect_node_info(child)
            
            if 'data' in data:
                collect_node_info(data['data'])
            
            # Part 1: Clean up orphaned links in cards (node was deleted)
            all_notes = self.mw.col.find_notes(f'data-mid="{self.note_id}"')
            
            cleaned_card_count = 0
            for nid in all_notes:
                try:
                    card_note = self.mw.col.get_note(nid)
                    modified = False
                    
                    # Check all fields for the mindmap link
                    for field_name in card_note.keys():
                        field_content = card_note[field_name]
                        
                        # Look for mindmap-link divs
                        import re
                        pattern = r'<div id="mindmap-link"\s+data-mid="(\d+)"\s+data-nid="([^"]+)"\s+style="display:none;">\s*</div>'
                        
                        def check_and_remove(match):
                            nonlocal modified
                            mid = match.group(1)
                            node_id = match.group(2)
                            
                            # If this link points to our mindmap
                            if mid == str(self.note_id):
                                # Check if the node still exists
                                if node_id not in existing_node_ids:
                                    # Node doesn't exist, remove this link
                                    modified = True
                                    print(f"Removing orphaned link to node {node_id} from card {nid}")
                                    return ""  # Remove the div
                            
                            return match.group(0)  # Keep the div
                        
                        new_content = re.sub(pattern, check_and_remove, field_content)
                        if new_content != field_content:
                            card_note[field_name] = new_content
                    
                    if modified:
                        self.mw.col.update_note(card_note)
                        cleaned_card_count += 1
                        
                except Exception as e:
                    print(f"Error cleaning card {nid}: {e}")
            
            # Part 2: Clean up noteId from nodes whose cards are deleted
            orphaned_node_ids = []
            for node_id, note_id in nodes_with_note_ids.items():
                try:
                    # Try to get the card
                    card_note = self.mw.col.get_note(note_id)
                    # Card exists, check if it still has the link to this mindmap
                    has_link = False
                    for field_name in card_note.keys():
                        if f'data-mid="{self.note_id}"' in card_note[field_name]:
                            has_link = True
                            break
                    
                    if not has_link:
                        # Card exists but link was removed, clean up noteId
                        orphaned_node_ids.append(node_id)
                        
                except Exception:
                    # Card doesn't exist, mark for cleanup
                    orphaned_node_ids.append(node_id)
            
            # Remove noteId from nodes
            if orphaned_node_ids:
                def remove_note_ids(node):
                    if isinstance(node, dict):
                        if 'id' in node and node['id'] in orphaned_node_ids:
                            if 'noteId' in node:
                                del node['noteId']
                                print(f"Removed orphaned noteId from node {node['id']}")
                        if 'children' in node:
                            for child in node['children']:
                                remove_note_ids(child)
                
                if 'data' in data:
                    remove_note_ids(data['data'])
                    
                    # Part 3: Delete nodes whose linked cards are deleted
                    deleted_count = 0
            
                    def delete_orphaned_nodes(node, parent_children=None, index=None):
                        nonlocal deleted_count
                        if isinstance(node, dict):
                            node_id = node.get('id')
                            # Delete this node if it's orphaned
                            if node_id in orphaned_node_ids:
                                if parent_children is not None and index is not None:
                                    parent_children.pop(index)
                                    deleted_count += 1
                                    print(f"Deleted orphaned node {node_id}")
                                    return True
                            # Recursively check children
                            if 'children' in node:
                                for i in range(len(node['children']) - 1, -1, -1):
                                    delete_orphaned_nodes(node['children'][i], node['children'], i)
                        return False
            
                    if 'data' in data:
                        delete_orphaned_nodes(data['data'])
                        if deleted_count > 0 or orphaned_node_ids:
                            self.note['Data'] = json.dumps(data)
                            self.mw.col.update_note(self.note)
                            print(f"Deleted {deleted_count} orphaned nodes, cleaned up {len(orphaned_node_ids)} noteId references")
            
            if cleaned_card_count > 0 or orphaned_node_ids:
                print(f"Cleanup complete: {cleaned_card_count} card links removed, {len(orphaned_node_ids)} orphaned references found")
                
        except Exception as e:
            print(f"Error during cleanup: {e}")


    def _handle_save(self, payload_json: str):
        try:
            payload = json.loads(payload_json)
            data = payload.get("data")
            image_html = payload.get("image_html")
            floating_nodes = payload.get("floatingNodes", [])
            summary_braces = payload.get("summaryBraces", [])
            boundary_data = payload.get("boundaries", [])
            changed_nodes = payload.get("changedNodes", [])  # Added: receive changed nodes
            
            print(f"DEBUG: Received changed_nodes: {changed_nodes}")
            
            # Combine mind map data with floating nodes, summary braces, and boundaries
            if data:
                if isinstance(data, dict):
                    data['floatingNodes'] = floating_nodes
                    data['summaryBraces'] = summary_braces
                    data['boundaries'] = boundary_data
                # Log data to save before saving (for debugging)
                new_data_json = json.dumps(data)
                print(f"DEBUG: About to save data, length: {len(new_data_json)}, root topic: {data.get('data', {}).get('topic', 'N/A')}")
                
                self.note['Data'] = new_data_json

            
            if image_html:
                self.note['DisplayHTML'] = f"<div class='mindmap-static'>{image_html}</div>"
            
            # Save note
            self.mw.col.update_note(self.note)
            
            # Force flush to database to ensure data is written
            self.mw.col.flush()
            
            # Verify data was saved (reload)
            verification_note = self.mw.col.get_note(self.note_id)
            verification_data = verification_note['Data']
            print(f"DEBUG: Data saved and verified, length: {len(verification_data)}")
            if verification_data != self.note['Data']:
                print("WARNING: Saved data differs from what we tried to save!")
            else:
                print("DEBUG: Data verified - matches what we saved")
            
            # Sync changed nodes to linked cards
            if changed_nodes:
                print(f"DEBUG: Syncing {len(changed_nodes)} changed nodes to cards")
                self._sync_nodes_to_cards(changed_nodes)
                # Also sync map-linked nodes
                self._sync_map_linked_nodes(changed_nodes)
            else:
                print("DEBUG: No changed nodes to sync")
            
            # Don't reset immediately, wait for sync to complete
            self.mw.reset()
            
            self.web.eval("if(typeof showToast === 'function') showToast('Saved!');")
            
        except Exception as e:
            print(f"Error saving: {e}")
            import traceback
            traceback.print_exc()
            self.web.eval(f"if(typeof showToast === 'function') showToast('Error: {e}');")

    
    def _sync_nodes_to_cards(self, changed_nodes):
        """Sync changed node content to linked cards"""
        import re
        # Import cycle prevention flag
        from . import card_linker
        
        for node_info in changed_nodes:
            node_id = node_info.get('id')
            new_topic = node_info.get('topic', '')
            note_id = node_info.get('noteId')
            
            if not note_id or not new_topic:
                continue
            
            try:
                # Prevent sync loop
                card_linker._syncing_from_node = True
                
                # Get linked card
                card_note = self.mw.col.get_note(note_id)
                
                # Check if card has Front field
                if 'Front' not in card_note:
                    continue
                
                # Get current front content
                front_content = card_note['Front']
                
                # Extract first line
                front_text = re.sub(r'<br\s*/?>', '\n', front_content, flags=re.IGNORECASE)
                clean_text = re.sub('<[^<]+?>', '', front_text)
                lines = clean_text.split('\n')
                first_line = lines[0].strip() if lines else ''
                
                # Update if first line differs from node content
                if first_line != new_topic:
                    # Replace first line, keep rest
                    # Need to preserve HTML format
                    if '<br' in front_content.lower():
                        # Has newline
                        parts = re.split(r'<br\s*/?>', front_content, maxsplit=1, flags=re.IGNORECASE)
                        if len(parts) > 1:
                            card_note['Front'] = new_topic + '<br>' + parts[1]
                        else:
                            card_note['Front'] = new_topic
                    else:
                        # No newline, replace entire
                        card_note['Front'] = new_topic
                    
                    self.mw.col.update_note(card_note)
                    print(f"Synced mindmap node to card: '{first_line}' -> '{new_topic}'")
                    
            except Exception as e:
                print(f"Error syncing node {node_id} to card {note_id}: {e}")
            finally:
                card_linker._syncing_from_node = False

    def _sync_map_linked_nodes(self, changed_nodes):
        """Sync changes from map-linked nodes to their source maps"""
        # Load current map data to check for map link properties
        try:
            data_str = self.note['Data']
            current_data = json.loads(data_str)
        except Exception as e:
            print(f"Error loading current map data for sync: {e}")
            return
        
        # Build index of nodes with map link properties
        map_link_nodes = {}
        
        def collect_map_link_nodes(node):
            if isinstance(node, dict):
                node_id = node.get('id')
                if node.get('isMapLink') and node.get('sourceMapId'):
                    map_link_nodes[node_id] = {
                        'sourceMapId': node.get('sourceMapId'),
                        'sourceNodeId': node.get('sourceNodeId', 'root')
                    }
                if 'children' in node:
                    for child in node['children']:
                        collect_map_link_nodes(child)
        
        if 'data' in current_data:
            collect_map_link_nodes(current_data['data'])
        
        # Also check root node for linkedMaps (sync content from root to linked nodes)
        root_node = current_data.get('data', {})
        root_linked_maps = root_node.get('linkedMaps', [])
        
        for node_info in changed_nodes:
            node_id = node_info.get('id')
            new_topic = node_info.get('topic', '')
            
            if not node_id or not new_topic:
                continue
            
            # Case 1: This is a map-linked node - sync to source map's root
            if node_id in map_link_nodes:
                link_info = map_link_nodes[node_id]
                source_map_id = link_info['sourceMapId']
                self._sync_map_link_content(node_id, new_topic, source_map_id)
            
            # Case 2: This is the root node with linkedMaps - sync to all linked nodes
            if node_id == 'root' and root_linked_maps:
                for link in root_linked_maps:
                    target_map_id = link.get('targetMapId')
                    linked_node_id = link.get('linkedNodeId')
                    if target_map_id and linked_node_id:
                        self._sync_to_linked_node(target_map_id, linked_node_id, new_topic)

    def _sync_to_linked_node(self, target_map_id: int, linked_node_id: str, new_topic: str):
        """Sync content from root to a linked node in another map"""
        try:
            target_note = self.mw.col.get_note(target_map_id)
            target_data_str = target_note['Data']
            target_data = json.loads(target_data_str)
            
            modified = False
            
            def update_node(node):
                nonlocal modified
                if isinstance(node, dict):
                    if node.get('id') == linked_node_id:
                        if node.get('topic') != new_topic:
                            node['topic'] = new_topic
                            modified = True
                            return True
                    if 'children' in node:
                        for child in node['children']:
                            if update_node(child):
                                return True
                return False
            
            if 'data' in target_data:
                update_node(target_data['data'])
            
            if modified:
                target_note['Data'] = json.dumps(target_data)
                self.mw.col.update_note(target_note)
                print(f"Synced root content to linked node {linked_node_id} in map {target_map_id}")
                
                # Notify open target map window to refresh if exists
                if hasattr(self.mw, 'mindmap_editors'):
                    for editor in self.mw.mindmap_editors:
                        if editor.note_id == target_map_id:
                            editor._handle_refresh()
                            break
        except Exception as e:
            print(f"Error syncing to linked node: {e}")

    def _handle_refresh(self):
        """Refresh mindmap data"""
        try:
            print(f"DEBUG: Refresh requested for note {self.note_id}")
            
            # Force reload latest data from database
            # Clear possible cache first
            self.mw.col.flush()
            
            # Completely re-fetch note (don't use self.note)
            fresh_note = self.mw.col.get_note(self.note_id)
            data_str = fresh_note['Data']
            
            print(f"DEBUG: Loaded fresh data, length: {len(data_str)}")
            
            # Parse to check root topic
            try:
                import json
                parsed_data = json.loads(data_str)
                root_topic = parsed_data.get('data', {}).get('topic', 'N/A')
                print(f"DEBUG: Root topic in fresh data: {root_topic}")
            except:
                pass
            
            # Update self.note with latest data
            self.note = fresh_note
            
            # Send to JavaScript
            js_code = f"if(typeof reloadMapData === 'function') reloadMapData({data_str});"
            self.web.eval(js_code)
            print("DEBUG: Refresh command sent to JavaScript")
        except Exception as e:
            print(f"Error refreshing: {e}")
            import traceback
            traceback.print_exc()

    def _handle_get_editable_maps(self):
        """Get list of editable mind maps for the selection dialog, including linked status"""
        try:
            maps_list = []
            ids = self.mw.col.find_notes('"note:MindMap Master"')
            
            # Get current linked maps from source root
            linked_map_ids = set()
            try:
                data_str = self.note['Data']
                source_data = json.loads(data_str)
                source_root = source_data.get('data', {})
                linked_maps = source_root.get('linkedMaps', [])
                for link in linked_maps:
                    linked_map_ids.add(link.get('targetMapId'))
            except Exception as e:
                print(f"Error getting linked maps: {e}")
            
            for nid in ids:
                # Skip current map
                if nid == self.note_id:
                    continue
                note = self.mw.col.get_note(nid)
                # Only include active (editable) maps
                try:
                    allow_new = note['AllowNewCards']
                except KeyError:
                    allow_new = '1'
                if allow_new == '1':
                    maps_list.append({
                        'id': nid,
                        'title': note['Title'],
                        'isLinked': nid in linked_map_ids
                    })
            # Send list to JavaScript
            js_code = f"if(typeof onEditableMapsReceived === 'function') onEditableMapsReceived({json.dumps(maps_list)});"
            self.web.eval(js_code)
        except Exception as e:
            print(f"Error getting editable maps: {e}")

    def _handle_create_map_link(self, params_json: str):
        """Create a bidirectional link between this map's root and another map"""
        try:
            params = json.loads(params_json)
            target_map_id = params.get('targetMapId')
            
            if not target_map_id:
                print("Error: No target map ID provided")
                return
            
            # Load current map data
            data_str = self.note['Data']
            source_data = json.loads(data_str)
            source_root = source_data.get('data', {})
            root_topic = source_root.get('topic', 'Linked Node')
            
            # Generate new node ID for the linked node in target map
            import uuid
            linked_node_id = f"maplink_{uuid.uuid4().hex[:8]}"
            
            # Load target map
            target_note = self.mw.col.get_note(target_map_id)
            target_data_str = target_note['Data']
            target_data = json.loads(target_data_str)
            target_root = target_data.get('data', {})
            
            # Create linked node in target map (copy style from source root)
            linked_node = {
                "id": linked_node_id,
                "topic": root_topic,
                "direction": "right",
                "expanded": True,
                "isMapLink": True,
                "sourceMapId": self.note_id,
                "sourceNodeId": "root"
            }
            
            # Copy style properties from source root to linked node
            style_props = ['background-color', 'foreground-color', 'width', 'height', 
                          'font-size', 'font-weight', 'font-style']
            for prop in style_props:
                if prop in source_root:
                    linked_node[prop] = source_root[prop]
            
            # Add to target root's children
            if 'children' not in target_root:
                target_root['children'] = []
            target_root['children'].append(linked_node)
            
            # Save target map
            target_note['Data'] = json.dumps(target_data)
            self.mw.col.update_note(target_note)
            
            # Update source root with link info (include title for display)
            if 'linkedMaps' not in source_root:
                source_root['linkedMaps'] = []
            source_root['linkedMaps'].append({
                "targetMapId": target_map_id,
                "targetMapTitle": target_note['Title'],
                "linkedNodeId": linked_node_id
            })
            
            # Save source map
            self.note['Data'] = json.dumps(source_data)
            self.mw.col.update_note(self.note)
            
            # Notify JavaScript of success
            self.web.eval(f"if(typeof onMapLinkCreated === 'function') onMapLinkCreated({target_map_id}, '{linked_node_id}');")
            self.web.eval("if(typeof showToast === 'function') showToast('Link created!');")
            
            # Refresh source map to show updated link indicator
            self._handle_refresh()
            
            # Refresh target map window if open to show the new linked node
            if hasattr(self.mw, 'mindmap_editors'):
                for editor in self.mw.mindmap_editors:
                    if editor.note_id == target_map_id:
                        editor._handle_refresh()
                        print(f"Refreshed target map window {target_map_id}")
                        break
            
            print(f"Created map link: {self.note_id} -> {target_map_id} (node: {linked_node_id})")
            
        except Exception as e:
            print(f"Error creating map link: {e}")
            import traceback
            traceback.print_exc()
            self.web.eval(f"if(typeof showToast === 'function') showToast('Error: {e}');")

    def _handle_jump_to_map(self, params_json: str):
        """Jump to another mind map, optionally focusing on a specific node"""
        try:
            params = json.loads(params_json)
            target_map_id = params.get('targetMapId')
            focus_node_id = params.get('focusNodeId', None)
            
            if not target_map_id:
                print("Error: No target map ID provided")
                return
            
            # Use open_instance to open or focus the target map
            MindMapDialog.open_instance(self.mw, target_map_id, focus_node_id)
            
        except Exception as e:
            print(f"Error jumping to map: {e}")

    def _handle_delete_map_link(self, params_json: str):
        """Handle deletion of a map link node - clean up the link in source map"""
        try:
            params = json.loads(params_json)
            source_map_id = params.get('sourceMapId')
            linked_node_id = params.get('linkedNodeId')
            
            if not source_map_id:
                print("Error: No source map ID provided")
                return
            
            # Load source map and remove the link reference
            try:
                source_note = self.mw.col.get_note(source_map_id)
                source_data_str = source_note['Data']
                source_data = json.loads(source_data_str)
                source_root = source_data.get('data', {})
                
                # Remove from linkedMaps array
                if 'linkedMaps' in source_root:
                    source_root['linkedMaps'] = [
                        link for link in source_root['linkedMaps']
                        if link.get('linkedNodeId') != linked_node_id
                    ]
                    # Clean up empty array
                    if not source_root['linkedMaps']:
                        del source_root['linkedMaps']
                
                # Save source map
                source_note['Data'] = json.dumps(source_data)
                self.mw.col.update_note(source_note)
                
                print(f"Cleaned up map link in source map {source_map_id}")
                
                # Notify open source map window to refresh if exists
                if hasattr(self.mw, 'mindmap_editors'):
                    for editor in self.mw.mindmap_editors:
                        if editor.note_id == source_map_id:
                            editor._handle_refresh()
                            break
                
            except Exception as e:
                print(f"Source map {source_map_id} no longer exists or error: {e}")
            
        except Exception as e:
            print(f"Error deleting map link: {e}")

    def _handle_unlink_map(self, params_json: str):
        """Remove a link from this map's root and delete the linked node in target map"""
        try:
            params = json.loads(params_json)
            target_map_id = params.get('targetMapId')
            
            if not target_map_id:
                print("Error: No target map ID provided")
                return
            
            # Load current map data
            data_str = self.note['Data']
            source_data = json.loads(data_str)
            source_root = source_data.get('data', {})
            
            # Find and remove the link to target map
            linked_node_id = None
            if 'linkedMaps' in source_root:
                for link in source_root['linkedMaps']:
                    if link.get('targetMapId') == target_map_id:
                        linked_node_id = link.get('linkedNodeId')
                        break
                
                # Remove from linkedMaps array
                source_root['linkedMaps'] = [
                    link for link in source_root['linkedMaps']
                    if link.get('targetMapId') != target_map_id
                ]
                if not source_root['linkedMaps']:
                    del source_root['linkedMaps']
            
            # Save source map
            self.note['Data'] = json.dumps(source_data)
            self.mw.col.update_note(self.note)
            
            # Delete the linked node from target map
            if linked_node_id:
                try:
                    target_note = self.mw.col.get_note(target_map_id)
                    target_data_str = target_note['Data']
                    target_data = json.loads(target_data_str)
                    
                    # Recursively find and remove the linked node
                    def remove_node(node, parent_children_list=None, index=None):
                        if isinstance(node, dict):
                            if node.get('id') == linked_node_id:
                                if parent_children_list is not None and index is not None:
                                    parent_children_list.pop(index)
                                    return True
                            if 'children' in node:
                                for i, child in enumerate(list(node['children'])):
                                    if remove_node(child, node['children'], i):
                                        return True
                        return False
                    
                    if 'data' in target_data:
                        remove_node(target_data['data'])
                    
                    # Save target map
                    target_note['Data'] = json.dumps(target_data)
                    self.mw.col.update_note(target_note)
                    
                    print(f"Removed linked node {linked_node_id} from target map {target_map_id}")
                    
                    # Refresh target map window if open
                    if hasattr(self.mw, 'mindmap_editors'):
                        for editor in self.mw.mindmap_editors:
                            if editor.note_id == target_map_id:
                                editor._handle_refresh()
                                break
                    
                except Exception as e:
                    print(f"Error removing linked node from target map: {e}")
            
            # Refresh source map
            self._handle_refresh()
            
            self.web.eval("if(typeof showToast === 'function') showToast('Link removed');")
            print(f"Unlinked map {target_map_id} from {self.note_id}")
            
        except Exception as e:
            print(f"Error unlinking map: {e}")
            import traceback
            traceback.print_exc()

    def _sync_map_link_content(self, node_id: str, new_topic: str, source_map_id: int):
        """Sync content changes from a linked node to the source map's root"""
        try:
            source_note = self.mw.col.get_note(source_map_id)
            source_data_str = source_note['Data']
            source_data = json.loads(source_data_str)
            source_root = source_data.get('data', {})
            
            # Update source root topic
            if source_root.get('topic') != new_topic:
                source_root['topic'] = new_topic
                source_note['Data'] = json.dumps(source_data)
                
                # Also update Title field
                source_note['Title'] = new_topic
                
                self.mw.col.update_note(source_note)
                print(f"Synced linked node content to source map {source_map_id}: '{new_topic}'")
                
                # Notify open source map window to refresh if exists
                if hasattr(self.mw, 'mindmap_editors'):
                    for editor in self.mw.mindmap_editors:
                        if editor.note_id == source_map_id:
                            editor._handle_refresh()
                            break
        except Exception as e:
            print(f"Error syncing map link content: {e}")

    def closeEvent(self, event):
        event.accept()

