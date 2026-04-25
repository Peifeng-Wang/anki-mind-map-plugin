window.saveHistory = function () {
    if (!jm) return;

    try {
        if (!Array.isArray(mindMapHistory)) {
            mindMapHistory = [];
            mindMapHistoryStateStrings = [];
            mindMapHistoryIndex = -1;
        }

        var mindMapData = jm.get_data('node_tree');
        var floatingData = floatingNodes.map(function (n) {
            return { id: n.id, topic: n.topic, x: n.x, y: n.y };
        });

        var currentState = {
            mind: mindMapData,
            floating: floatingData
        };
        var currentStateStr = JSON.stringify(currentState);

        if (mindMapHistoryIndex >= 0 && mindMapHistory[mindMapHistoryIndex]) {
            var lastStateStr = mindMapHistoryStateStrings[mindMapHistoryIndex];
            if (typeof lastStateStr !== 'string') {
                lastStateStr = JSON.stringify(mindMapHistory[mindMapHistoryIndex]);
                mindMapHistoryStateStrings[mindMapHistoryIndex] = lastStateStr;
            }
            if (currentStateStr === lastStateStr) return;
        }

        if (mindMapHistoryIndex < mindMapHistory.length - 1) {
            mindMapHistory = mindMapHistory.slice(0, mindMapHistoryIndex + 1);
            mindMapHistoryStateStrings = mindMapHistoryStateStrings.slice(0, mindMapHistoryIndex + 1);
        }

        mindMapHistory.push(JSON.parse(currentStateStr));
        mindMapHistoryStateStrings.push(currentStateStr);

        if (mindMapHistory.length > maxHistory) {
            mindMapHistory.shift();
            mindMapHistoryStateStrings.shift();
        } else {
            mindMapHistoryIndex++;
        }

        console.log("History saved. Total steps: " + mindMapHistory.length);
    } catch (e) {
        console.error("Error saving history:", e);
    }
};

function restoreState(state) {
    if (!state) return;
    console.log("Restoring state...");

    var panel = jm.view.e_panel;

    var lastScrollX = panel.scrollLeft;
    var lastScrollY = panel.scrollTop;

    var selectedNode = jm.get_selected_node();
    var lastSelectedId = selectedNode ? selectedNode.id : null;

    if (state.mind) {
        jm.show(state.mind);
    }

    floatingNodes = [];
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
        var node = jm.get_node(lastSelectedId);
        if (node) {
            jm.select_node(lastSelectedId);
        } else {
            jm.select_clear();
        }
    } else {
        jm.select_clear();
    }
}

window.undo = function () {
    console.log("Undo trigger received. Index: " + mindMapHistoryIndex);
    if (mindMapHistoryIndex > 0) {
        mindMapHistoryIndex--;
        restoreState(mindMapHistory[mindMapHistoryIndex]);
        scheduleAutoSave();
    } else {
        console.log("Nothing to undo");
    }
};

window.redo = function () {
    console.log("Redo trigger received. Index: " + mindMapHistoryIndex);
    if (mindMapHistoryIndex < mindMapHistory.length - 1) {
        mindMapHistoryIndex++;
        restoreState(mindMapHistory[mindMapHistoryIndex]);
        scheduleAutoSave();
    }
};

function scheduleAutoSave() {
    if (autoSaveTimeout) {
        clearTimeout(autoSaveTimeout);
    }

    autoSaveTimeout = setTimeout(function () {
        autoSave();
    }, autoSaveDelay);
}

function collectFloatingNodesData() {
    return floatingNodes.map(function (node) {
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
    changedNodes.forEach(function (nodeId) {
        var node = jm.get_node(nodeId);
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
    var mind_data = jm.get_data('node_tree');
    var container = document.getElementById('jsmind_container');

    return {
        data: mind_data,
        image_html: container ? container.innerHTML : "",
        arrows: arrows,
        floatingNodes: collectFloatingNodesData(),
        summaryBraces: summaryBraces,
        boundaries: boundaries,
        changedNodes: collectChangedNodesData()
    };
}

function autoSave() {
    if (!jm) return;

    try {
        var payload = buildSavePayload();

        console.log('AutoSaving... Data nodes count:', payload.data.data ? countNodes(payload.data.data) : 0);
        console.log('Changed nodes to sync:', payload.changedNodes);

        pycmd("save:" + JSON.stringify(payload));

        // Clear change records
        changedNodes.clear();

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
