import base64
import json
import logging
import os

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


def _render_editor_init_js(config, data_json, focus_node_id):
    """Substitute __FOO__ placeholders in editor_init.js with json-encoded
    config/data. Every value is fed through ``json.dumps`` so user-supplied
    text is never concatenated raw into the HTML."""
    template = read_asset("editor_assets/editor_init.js")

    # ``data_json`` is already a JSON string emitted from the Anki note. Splice
    # it in as-is so we don't double-encode (Python json.dumps would wrap it in
    # quotes and turn it into a string instead of an object literal).
    substitutions = {
        "__HOTKEY_CONFIG_JSON__": json.dumps(config.get('hotkeys', {})),
        "__LINE_COLOR_JSON__": json.dumps(config.get('line_color', 'rgba(139, 92, 246, 0.6)')),
        "__BRACE_COLOR_JSON__": json.dumps(config.get('brace_color', '#3b82f6')),
        "__BOUNDARY_COLOR_JSON__": json.dumps(config.get('boundary_color', '#ef4444')),
        "__ENABLE_FLOATING_NODES_JSON__": json.dumps(config.get('enable_floating_nodes', True)),
        "__JUMP_MODE_JSON__": json.dumps(config.get('jump_mode', 'preview')),
        "__INITIAL_DATA_JSON__": data_json if data_json else "{}",
        "__FOCUS_NODE_ID_JSON__": json.dumps(focus_node_id or ''),
    }

    rendered = template
    for token, value in substitutions.items():
        rendered = rendered.replace(token, value)
    return rendered


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
        "main/summary_braces_dom.js",
        "main/summary_braces_commands.js",
        "main/summary_braces_render.js",
        "main/multi_selection_menu.js",
        "main/boundaries.js",
        "main/navigation.js",
        "main/node_editor.js",
        "main/node_editor_events.js",
        "main/backend_links.js",
        "main/clipboard.js",
        "main/app_events_tail.js",
    ])

    bg_style = get_background_style(addon_dir, config)

    # Heavy CSS/JS literals live in real files now. Keep only the slim HTML
    # scaffolding here so syntax highlighting and editing work.
    editor_chrome_css = read_asset("editor_assets/editor_chrome.css")
    mathjax_config_js = read_asset("editor_assets/mathjax_config.js")
    dompurify_js = read_asset("vendor/dompurify/dompurify.min.js")
    editor_init_js = _render_editor_init_js(config, data_json, focus_node_id)

    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <style>
        {jsmind_css}
        {style_css}
        {bg_style}
        {editor_chrome_css}
        </style>
        <script>
        {mathjax_config_js}
        </script>
        <script src="vendor/mathjax/es5/tex-svg.js" async></script>
        <script>
        {dompurify_js}
        </script>
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
        {editor_init_js}
        </script>
    </body>
    </html>
    """

    return html
