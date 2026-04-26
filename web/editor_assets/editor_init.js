// Editor initialization: receives JSON-encoded data from Python via
// substituted placeholders, then wires up menus, hotkey config, jump
// mode, and triggers initEditor()/focusNode() on window load.
//
// All __FOO__ tokens are replaced by mindmap_editor/assets.py with
// json.dumps(...)-encoded values before this script reaches the browser.

var hotkeyConfigFromPython = __HOTKEY_CONFIG_JSON__;
var lineColorFromPython = __LINE_COLOR_JSON__;
var braceColorFromPython = __BRACE_COLOR_JSON__;
var boundaryColorFromPython = __BOUNDARY_COLOR_JSON__;
var enableFloatingNodesFromPython = __ENABLE_FLOATING_NODES_JSON__;
var initialJumpMode = __JUMP_MODE_JSON__;

if (hotkeyConfigFromPython && Object.keys(hotkeyConfigFromPython).length > 0) {
    // Merge user config with defaults so new hotkeys get sensible fallbacks.
    MM.state.hotkeyConfig = Object.assign({}, MM.state.hotkeyConfig, hotkeyConfigFromPython);
    console.log("Loaded hotkey config:", MM.state.hotkeyConfig);
}

// Inject data directly
var initialData = __INITIAL_DATA_JSON__;
var initialFocusId = __FOCUS_NODE_ID_JSON__;

// Menu Logic
function toggleMenu() {
    var menu = document.getElementById("main-menu");
    if (menu.style.display === "block") {
        menu.style.display = "none";
    } else {
        menu.style.display = "block";
    }
}

// Close menu when clicking outside
document.addEventListener('click', function(event) {
    var container = document.querySelector('.menu-container');
    if (!container.contains(event.target)) {
        document.getElementById("main-menu").style.display = "none";
    }
});

function setJumpMode(mode) {
    // Update UI
    document.getElementById('mode_' + mode).checked = true;
    // Save to Anki config
    pycmd("update_config:jump_mode=" + mode);
}

// Initialize UI based on config
if (typeof initialJumpMode !== 'undefined') {
    document.getElementById('mode_' + initialJumpMode).checked = true;
}

window.onload = function() {
    console.log("Window loaded. Starting init...");
    if (typeof initEditor === 'function') {
        initEditor(initialData);

        if (initialFocusId) {
            setTimeout(function() {
                if (typeof focusNode === 'function') {
                    focusNode(initialFocusId);
                }
            }, 800);
        }
    } else {
        console.error("Error: initEditor function not found!");
    }
};
