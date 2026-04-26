import base64
import json
import logging
import os

from aqt.qt import QUrl
from aqt.webview import AnkiWebView

logger = logging.getLogger(__name__)

# ---------- Asset caches ----------
_asset_cache = {}
_bg_image_cache = {}


def read_asset(filename):
    if filename not in _asset_cache:
        try:
            addon_dir = os.path.dirname(os.path.dirname(__file__))
            web_dir = os.path.join(addon_dir, "web")
            with open(os.path.join(web_dir, filename), 'r', encoding='utf-8') as f:
                _asset_cache[filename] = f.read()
        except Exception:
            logger.warning("Asset not found or unreadable: %s", filename)
            _asset_cache[filename] = ""
    return _asset_cache[filename]


def read_assets(filenames):
    return "\n".join(read_asset(filename) for filename in filenames)


def read_css_entry(filename):
    """Inline split CSS imports because Anki embeds assets in a style tag."""
    content = read_asset(filename)
    base_dir = os.path.dirname(filename)
    expanded = []
    for line in content.splitlines():
        stripped = line.strip()
        if stripped.startswith("@import") and "url(" in stripped:
            import_path = stripped.split("url(", 1)[1].split(")", 1)[0].strip("\"'")
            import_path = import_path.lstrip("./").replace("/", os.sep)
            if base_dir:
                import_path = os.path.join(base_dir, import_path)
            expanded.append(read_asset(import_path))
        else:
            expanded.append(line)
    return "\n".join(expanded)


def get_background_style(addon_dir, config):
    """Load background image and return CSS style string."""
    bg_filename = config.get('background_image', '')
    if not bg_filename:
        return ""
    bg_path = os.path.join(addon_dir, 'backgrounds', bg_filename)
    if not os.path.exists(bg_path):
        return ""
    try:
        mtime = os.path.getmtime(bg_path)
        cache_key = (bg_filename, mtime)
        if cache_key not in _bg_image_cache:
            with open(bg_path, 'rb') as img_file:
                img_data = base64.b64encode(img_file.read()).decode('utf-8')
            ext = os.path.splitext(bg_filename)[1].lower()
            mime_type = 'image/jpeg' if ext in ['.jpg', '.jpeg'] else 'image/png'
            overlay = config.get('background_overlay', '')
            if overlay:
                bg_css = f"linear-gradient({overlay}, {overlay}), url(data:{mime_type};base64,{img_data})"
            else:
                bg_css = f"url(data:{mime_type};base64,{img_data})"
            _bg_image_cache[cache_key] = f"""
            .jsmind-inner {{
                background-image: {bg_css} !important;
            }}
            """
        return _bg_image_cache[cache_key]
    except Exception:
        logger.exception("Error loading background image")
        return ""


def build_editor_html(dialog, config, data_json, focus_node_id):
    """Build the full HTML for the mind map editor."""
    addon_dir = os.path.dirname(os.path.dirname(__file__))

    jsmind_js = read_assets([
        "vendor/jsmind/jsmind.core.js",
        "vendor/jsmind/jsmind.model.js",
        "vendor/jsmind/jsmind.format.js",
        "vendor/jsmind/jsmind.util.js",
        "vendor/jsmind/jsmind.data-provider.js",
        "vendor/jsmind/jsmind.layout-provider.js",
        "vendor/jsmind/jsmind.view-provider.js",
        "vendor/jsmind/jsmind.shortcut-plugin.js",
        "vendor/jsmind/jsmind.js",
    ])
    jsmind_draggable = read_assets([
        "vendor/jsmind/jsmind.draggable.options.js",
        "vendor/jsmind/jsmind.draggable.canvas.js",
        "vendor/jsmind/jsmind.draggable.highlight.js",
        "vendor/jsmind/jsmind.draggable.shadow.js",
        "vendor/jsmind/jsmind.draggable.timer.js",
        "vendor/jsmind/jsmind.draggable.lookup.js",
        "vendor/jsmind/jsmind.draggable.autoscroll.js",
        "vendor/jsmind/jsmind.draggable.move.js",
        "vendor/jsmind/jsmind.draggable.events.js",
        "vendor/jsmind/jsmind.draggable.core.js",
    ])
    jsmind_css = read_css_entry("vendor/jsmind/jsmind.css")
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

    bg_style = get_background_style(addon_dir, config)

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
        var initialFocusId = "{focus_node_id or ''}";

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

    return html
