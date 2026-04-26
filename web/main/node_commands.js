function addChild() {
    if (!MM.state.jm) return;
    var selected = MM.state.jm.get_selected_node();
    if (!selected) {
        alert("Please select a node first");
        return;
    }
    var newId = 'node_' + Date.now();
    MM.state.jm.add_node(selected, newId, 'New Child');
    MM.state.jm.select_node(newId);
    setTimeout(renderMath, 300);
    saveHistory();
    scheduleAutoSave();
}

function addSibling() {
    if (!MM.state.jm) return;
    var selected = MM.state.jm.get_selected_node();
    if (!selected || selected.isroot) {
        alert("Cannot add sibling to root");
        return;
    }
    // Cannot add sibling to summary node
    if (selected.data && selected.data.isSummaryNode) {
        showToast('Cannot add sibling to summary node');
        return;
    }
    var parent = MM.state.jm.get_node(selected.parent);
    if (!parent) return;
    var newId = 'node_' + Date.now();
    MM.state.jm.add_node(parent, newId, 'New Sibling');
    MM.state.jm.select_node(newId);
    setTimeout(renderMath, 300);
    saveHistory();
    scheduleAutoSave();
}

function saveMap() {
    if (!MM.state.jm) return;
    try {
        var payload = buildSavePayload();

        console.log('Changed nodes to sync:', payload.changedNodes);

        pycmd("save:" + JSON.stringify(payload));


        // Clear change records
        MM.state.changedNodes.clear();

        var status = document.getElementById('auto-save-status');
        if (status) {
            status.textContent = 'Saved!';
            status.style.opacity = '1';
            setTimeout(function () {
                status.textContent = 'Auto-saved';
                status.style.opacity = '0';
            }, 2000);
        }
    } catch (e) {
        alert("Error saving: " + e);
    }
}

// Center view on root node
function centerRoot() {
    if (!MM.state.jm) return;

    var root = MM.state.jm.get_root();
    if (!root) return;

    // Select root node
    MM.state.jm.select_node(root);

    // Use jsMind's built-in centering by calling show with keep_center=true
    MM.state.jm.view.show(true);
}

// Refresh mind map data from database
function refreshMap() {
    if (!MM.state.jm) return;

    console.log('Requesting data refresh...');
    // Request fresh data from Python
    pycmd("refresh_data");
}

// Toggle fullscreen mode (maximize window in Anki)
function toggleFullscreen() {
    // Use Qt's fullscreen API via pycmd
    // The browser Fullscreen API doesn't work properly in QtWebEngine
    if (typeof pycmd !== 'undefined') {
        pycmd('toggle_fullscreen');
    }
}

// Update fullscreen button text when fullscreen state changes
document.addEventListener('fullscreenchange', updateFullscreenButton);
document.addEventListener('webkitfullscreenchange', updateFullscreenButton);
document.addEventListener('mozfullscreenchange', updateFullscreenButton);
document.addEventListener('MSFullscreenChange', updateFullscreenButton);

function updateFullscreenButton() {
    var btn = document.getElementById('fullscreen-btn');
    if (btn) {
        if (document.fullscreenElement || document.webkitFullscreenElement ||
            document.mozFullScreenElement || document.msFullscreenElement) {
            btn.textContent = '⛶ Exit Fullscreen';
        } else {
            btn.textContent = '⛶ Fullscreen';
        }
    }
}


