window.saveHistory = function () {
    if (!MM.state.jm) return;

    try {
        if (!Array.isArray(MM.state.mindMapHistory)) {
            MM.state.mindMapHistory = [];
            MM.state.mindMapHistoryStateStrings = [];
            MM.state.mindMapHistoryIndex = -1;
        }

        var mindMapData = MM.state.jm.get_data('node_tree');
        var floatingData = MM.state.floatingNodes.map(function (n) {
            return { id: n.id, topic: n.topic, x: n.x, y: n.y };
        });

        var currentState = {
            mind: mindMapData,
            floating: floatingData
        };
        var currentStateStr = JSON.stringify(currentState);

        if (MM.state.mindMapHistoryIndex >= 0 && MM.state.mindMapHistory[MM.state.mindMapHistoryIndex]) {
            var lastStateStr = MM.state.mindMapHistoryStateStrings[MM.state.mindMapHistoryIndex];
            if (typeof lastStateStr !== 'string') {
                lastStateStr = JSON.stringify(MM.state.mindMapHistory[MM.state.mindMapHistoryIndex]);
                MM.state.mindMapHistoryStateStrings[MM.state.mindMapHistoryIndex] = lastStateStr;
            }
            if (currentStateStr === lastStateStr) return;
        }

        if (MM.state.mindMapHistoryIndex < MM.state.mindMapHistory.length - 1) {
            MM.state.mindMapHistory = MM.state.mindMapHistory.slice(0, MM.state.mindMapHistoryIndex + 1);
            MM.state.mindMapHistoryStateStrings = MM.state.mindMapHistoryStateStrings.slice(0, MM.state.mindMapHistoryIndex + 1);
        }

        MM.state.mindMapHistory.push(JSON.parse(currentStateStr));
        MM.state.mindMapHistoryStateStrings.push(currentStateStr);

        if (MM.state.mindMapHistory.length > MM.state.maxHistory) {
            MM.state.mindMapHistory.shift();
            MM.state.mindMapHistoryStateStrings.shift();
        } else {
            MM.state.mindMapHistoryIndex++;
        }

        console.log("History saved. Total steps: " + MM.state.mindMapHistory.length);
    } catch (e) {
        console.error("Error saving history:", e);
    }
};

function restoreState(state) {
    if (!state) return;
    console.log("Restoring state...");

    var panel = MM.state.jm.view.e_panel;

    var lastScrollX = panel.scrollLeft;
    var lastScrollY = panel.scrollTop;

    var selectedNode = MM.state.jm.get_selected_node();
    var lastSelectedId = selectedNode ? selectedNode.id : null;

    if (state.mind) {
        MM.state.jm.show(state.mind);
    }

    MM.state.floatingNodes = [];
    var container = document.getElementById('jsmind_container');
    var oldNodes = container.querySelectorAll('jmnode[nodeid^="floating_"]');
    oldNodes.forEach(function (el) { el.remove(); });

    if (state.floating && Array.isArray(state.floating)) {
        state.floating.forEach(function (nodeData) {
            loadFloatingNode(nodeData);
        });
    }

    if (panel) {
        panel.scrollLeft = lastScrollX;
        panel.scrollTop = lastScrollY;
    }

    if (lastSelectedId) {
        var node = MM.state.jm.get_node(lastSelectedId);
        if (node) {
            MM.state.jm.select_node(lastSelectedId);
        } else {
            MM.state.jm.select_clear();
        }
    } else {
        MM.state.jm.select_clear();
    }
}

window.undo = function () {
    console.log("Undo trigger received. Index: " + MM.state.mindMapHistoryIndex);
    if (MM.state.mindMapHistoryIndex > 0) {
        MM.state.mindMapHistoryIndex--;
        restoreState(MM.state.mindMapHistory[MM.state.mindMapHistoryIndex]);
        scheduleAutoSave();
    } else {
        console.log("Nothing to undo");
    }
};

window.redo = function () {
    console.log("Redo trigger received. Index: " + MM.state.mindMapHistoryIndex);
    if (MM.state.mindMapHistoryIndex < MM.state.mindMapHistory.length - 1) {
        MM.state.mindMapHistoryIndex++;
        restoreState(MM.state.mindMapHistory[MM.state.mindMapHistoryIndex]);
        scheduleAutoSave();
    }
};

function scheduleAutoSave() {
    if (MM.state.autoSaveTimeout) {
        clearTimeout(MM.state.autoSaveTimeout);
    }

    MM.state.autoSaveTimeout = setTimeout(function () {
        autoSave();
    }, MM.state.autoSaveDelay);
}

function collectFloatingNodesData() {
    return MM.state.floatingNodes.map(function (node) {
        return {
            id: node.id,
            topic: node.topic,
            x: node.x,
            y: node.y
        };
    });
}

function collectChangedNodesData() {
    var changedNodesData = [];
    MM.state.changedNodes.forEach(function (nodeId) {
        var node = MM.state.jm.get_node(nodeId);
        if (!node) return;

        // jsMind stores custom data in node.data
        var noteId = node.data && node.data.noteId;
        var isMapLink = node.data && node.data.isMapLink;
        var sourceMapId = node.data && node.data.sourceMapId;
        var hasLinkedMaps = node.isroot && node.data && node.data.linkedMaps;

        // Include nodes with linked cards
        if (noteId) {
            changedNodesData.push({
                id: nodeId,
                topic: node.topic,
                noteId: noteId
            });
        }

        // Include map-linked nodes for sync
        if (isMapLink && sourceMapId) {
            changedNodesData.push({
                id: nodeId,
                topic: node.topic,
                isMapLink: true,
                sourceMapId: sourceMapId
            });
        }

        // Include root nodes with linkedMaps for sync
        if (hasLinkedMaps) {
            changedNodesData.push({
                id: nodeId,
                topic: node.topic,
                hasLinkedMaps: true,
                linkedMaps: node.data.linkedMaps
            });
        }
    });
    return changedNodesData;
}

function buildSavePayload() {
    var mind_data = MM.state.jm.get_data('node_tree');
    var container = document.getElementById('jsmind_container');

    return {
        data: mind_data,
        image_html: container ? container.innerHTML : "",
        arrows: MM.state.arrows,
        floatingNodes: collectFloatingNodesData(),
        summaryBraces: MM.state.summaryBraces,
        boundaries: MM.state.boundaries,
        changedNodes: collectChangedNodesData()
    };
}

function autoSave() {
    if (!MM.state.jm) return;

    try {
        var payload = buildSavePayload();

        console.log('AutoSaving... Data nodes count:', payload.data.data ? countNodes(payload.data.data) : 0);
        console.log('Changed nodes to sync:', payload.changedNodes);

        pycmd("save:" + JSON.stringify(payload));

        // Clear change records
        MM.state.changedNodes.clear();

        var status = document.getElementById('auto-save-status');
        if (status) {
            status.style.opacity = '1';
            setTimeout(function () {
                status.style.opacity = '0';
            }, 1500);
        }
    } catch (e) {
        console.error("Auto-save error:", e);
    }
}

// Helper function to count nodes
