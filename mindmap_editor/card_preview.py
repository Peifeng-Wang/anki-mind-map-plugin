import json
import logging

try:
    from aqt.qt import QDialog, QVBoxLayout, QWidget, QHBoxLayout, QToolButton, Qt
    from aqt.webview import AnkiWebView
except ImportError:
    QDialog = QVBoxLayout = QWidget = QHBoxLayout = QToolButton = Qt = AnkiWebView = None

logger = logging.getLogger(__name__)

PREVIEW_TOOLBAR_HEIGHT: int = 34
PREVIEW_TOOLBAR_MARGIN: int = 6
PREVIEW_TOOLBAR_SPACING: int = 6

PREVIEW_HTML_TEMPLATE: str = """
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


def _on_preview_bridge_cmd(dialog, cmd: str) -> None:
    """Handle commands from the preview window"""
    if cmd.startswith("save_mode:"):
        mode = cmd.split(":", 1)[1]
        dialog._set_config('preview_mode', mode)


def _set_window_always_on_top(window, enabled: bool) -> None:
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


def _open_card_preview(dialog, nid) -> None:
    """Open single instance card preview window (Fixed: Safe JSON injection)"""
    try:
        # 1. Get note content
        try:
            note = dialog.mw.col.get_note(nid)
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
        q_json = json.dumps(q_text).replace("</", "<\\/")
        a_json = json.dumps(a_text).replace("</", "<\\/")

        # Get saved preference
        config = dialog.mw.addonManager.getConfig(__name__) or {}
        current_mode = config.get('preview_mode', 'all')

        # 3. Inject Data safely into template
        html = PREVIEW_HTML_TEMPLATE.replace("VAR_FRONT_CONTENT", q_json)
        html = html.replace("VAR_ALL_CONTENT", a_json)
        html = html.replace("VAR_CURRENT_MODE", current_mode)

        # 5. Window Management (Independent Window)
        preview_dialog = getattr(dialog, '_preview_dialog', None)

        try:
            if preview_dialog:
                preview_dialog.isVisible()
        except RuntimeError:
            preview_dialog = None

        if not preview_dialog:
            preview_dialog = QDialog(None)  # None parent for independent window
            preview_dialog.setWindowFlags(Qt.WindowType.Window)
            preview_dialog.setWindowTitle("Card Preview")
            preview_dialog.setMinimumSize(450, 600)

            layout = QVBoxLayout(preview_dialog)
            layout.setContentsMargins(0, 0, 0, 0)
            layout.setSpacing(0)

            # Native toolbar so the user can pin/unpin the preview window (always on top).
            toolbar = QWidget(preview_dialog)
            toolbar.setFixedHeight(PREVIEW_TOOLBAR_HEIGHT)
            toolbar_layout = QHBoxLayout(toolbar)
            toolbar_layout.setContentsMargins(
                PREVIEW_TOOLBAR_MARGIN,
                PREVIEW_TOOLBAR_MARGIN,
                PREVIEW_TOOLBAR_MARGIN,
                PREVIEW_TOOLBAR_MARGIN,
            )
            toolbar_layout.setSpacing(PREVIEW_TOOLBAR_SPACING)
            toolbar_layout.addStretch(1)

            pin_btn = QToolButton(toolbar)
            pin_btn.setCheckable(True)
            pin_btn.setToolTip("Always on top")
            toolbar_layout.addWidget(pin_btn, 0, Qt.AlignmentFlag.AlignRight)

            preview_dialog._web = AnkiWebView(parent=preview_dialog)
            preview_dialog._web.set_bridge_command(
                lambda cmd: _on_preview_bridge_cmd(dialog, cmd), preview_dialog
            )

            layout.addWidget(toolbar)
            layout.addWidget(preview_dialog._web)

            def apply_pinned_state(checked: bool) -> None:
                _set_window_always_on_top(preview_dialog, checked)
                cfg = dialog.mw.addonManager.getConfig(__name__) or {}
                cfg["preview_pinned"] = bool(checked)
                dialog.mw.addonManager.writeConfig(__name__, cfg)
                pin_btn.setText("Unpin" if checked else "Pin")

            # Restore last pin state for this preview window.
            cfg = dialog.mw.addonManager.getConfig(__name__) or {}
            pinned = bool(cfg.get("preview_pinned", False))
            pin_btn.setChecked(pinned)
            pin_btn.setText("Unpin" if pinned else "Pin")
            apply_pinned_state(pinned)
            pin_btn.toggled.connect(apply_pinned_state)

            dialog.finished.connect(preview_dialog.close)
            dialog._preview_dialog = preview_dialog

        # 6. Update and Show
        title = note['Title'] if 'Title' in note else 'Card Preview'
        preview_dialog.setWindowTitle(title)
        preview_dialog._web.setHtml(html)

        if not preview_dialog.isVisible():
            preview_dialog.show()

        preview_dialog.raise_()
        preview_dialog.activateWindow()

    except Exception as e:
        from aqt.utils import showInfo
        showInfo(f"Preview error: {e}")
