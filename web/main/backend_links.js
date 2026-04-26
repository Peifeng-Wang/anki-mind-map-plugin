function toggleSelectedNodeCollapse() {
    if (!MM.state.jm) return false;

    var selected = MM.state.jm.get_selected_node();
    if (!selected) return false;

    if (!selected.children || selected.children.length === 0) {
        return false;
    }

    if (typeof MM.state.jm.toggle_node === 'function') {
        MM.state.jm.toggle_node(selected.id);
        renderSummaryBraces();
        renderBoundaries();
        return true;
    }

    // Fallback for older builds (should not be needed with bundled jsMind).
    if (selected.expanded && typeof MM.state.jm.collapse_node === 'function') {
        MM.state.jm.collapse_node(selected.id);
        renderSummaryBraces();
        renderBoundaries();
        return true;
    }
    if (!selected.expanded && typeof MM.state.jm.expand_node === 'function') {
        MM.state.jm.expand_node(selected.id);
        renderSummaryBraces();
        renderBoundaries();
        return true;
    }

    return false;
}

// Context Menu for Jumping to Card and Map Linking
document.addEventListener('contextmenu', function (e) {
    var target = e.target;
    // Find if we clicked on a node
    var nodeElement = target.closest('jmnode');
    if (nodeElement) {
        e.preventDefault();

        // Check if we have multiple nodes selected
        if (MM.state.selectedNodes.length > 1) {
            showMultiSelectionContextMenu(e.clientX, e.clientY);
            return;
        }

        var nodeId = nodeElement.getAttribute('nodeid');
        var node = MM.state.jm.get_node(nodeId);

        // Gather node properties
        var noteId = (node.data && node.data.noteId) || node.noteId;
        var isRoot = node.isroot;
        var isMapLink = node.data && node.data.isMapLink;
        var sourceMapId = node.data && node.data.sourceMapId;
        var linkedMaps = isRoot && node.data && node.data.linkedMaps;

        showNodeContextMenu(e.clientX, e.clientY, {
            nodeId: nodeId,
            noteId: noteId,
            isRoot: isRoot,
            isMapLink: isMapLink,
            sourceMapId: sourceMapId,
            linkedMaps: linkedMaps || []
        });

    }
});

function showNodeContextMenu(x, y, nodeInfo) {
    // Remove existing menu
    var existing = document.getElementById('custom-context-menu');
    if (existing) existing.remove();

    var menu = document.createElement('div');
    menu.id = 'custom-context-menu';
    menu.className = 'mm-context-menu';
    menu.style.left = x + 'px';
    menu.style.top = y + 'px';

    var hasItems = false;

    // Helper function to create menu item
    function createMenuItem(text, onClick) {
        var item = document.createElement('div');
        item.innerText = text;
        item.className = 'mm-context-menu-item';
        item.onclick = function () {
            onClick();
            menu.remove();
        };
        return item;
    }

    // 1. If node has a linked card, show "Jump to Card"
    if (nodeInfo.noteId) {
        menu.appendChild(createMenuItem("Jump to Card", function () {
            pycmd("jump_to_card:" + nodeInfo.noteId);
        }));
        hasItems = true;
    }

    // 2. If this is a map-linked node, show "Jump to Source Map"
    if (nodeInfo.isMapLink && nodeInfo.sourceMapId) {
        menu.appendChild(createMenuItem("Jump to Source Mind Map", function () {
            pycmd("jump_to_map:" + JSON.stringify({
                targetMapId: nodeInfo.sourceMapId,
                focusNodeId: "root"
            }));
        }));
        hasItems = true;
    }

    // 3. If this is root node with linkedMaps, show submenu for jumping
    if (nodeInfo.isRoot && nodeInfo.linkedMaps && nodeInfo.linkedMaps.length > 0) {
        // Add separator if there are other items
        if (hasItems) {
            var sep = document.createElement('div');
            sep.className = 'mm-context-menu-sep';
            menu.appendChild(sep);
        }

        // Add header for linked maps
        var header = document.createElement('div');
        header.innerText = "Jump to Linked Maps:";
        header.className = 'mm-context-menu-header';
        menu.appendChild(header);

        nodeInfo.linkedMaps.forEach(function (link) {
            var displayName = link.targetMapTitle || ("Map " + link.targetMapId);
            menu.appendChild(createMenuItem("  → " + displayName, function () {
                pycmd("jump_to_map:" + JSON.stringify({
                    targetMapId: link.targetMapId,
                    focusNodeId: link.linkedNodeId
                }));
            }));
        });
        hasItems = true;
    }

    // 4. If this is root node (not in read-only mode), show "Link to Other Mind Map"
    if (nodeInfo.isRoot && MM.state.jm && MM.state.jm.get_editable()) {
        // Add separator if there are other items
        if (hasItems) {
            var sep = document.createElement('div');
            sep.className = 'mm-context-menu-sep';
            menu.appendChild(sep);
        }

        menu.appendChild(createMenuItem("Link to Other Mind Map", function () {
            // Request editable maps list from Python
            pycmd("get_editable_maps");
        }));
        hasItems = true;
    }

    // Only show menu if there are items
    if (hasItems) {
        document.body.appendChild(menu);

        // Close on click elsewhere
        var closeHandler = function (e) {
            if (!menu.contains(e.target)) {
                menu.remove();
                document.removeEventListener('click', closeHandler);
            }
        };
        setTimeout(function () { document.addEventListener('click', closeHandler); }, 0);
    }
}

// Called by Python when editable maps list is received
function onEditableMapsReceived(mapsList) {
    if (!mapsList || mapsList.length === 0) {
        showToast("No other editable mind maps available");
        return;
    }

    showMapSelectionDialog(mapsList);
}

// Show dialog for selecting target map (with toggle for linked maps)
function showMapSelectionDialog(mapsList) {
    // Remove existing dialog
    var existing = document.getElementById('map-select-dialog');
    if (existing) existing.remove();

    var overlay = document.createElement('div');
    overlay.id = 'map-select-dialog';
    overlay.className = 'mm-dialog-overlay';

    var dialog = document.createElement('div');
    dialog.className = 'mm-dialog-box';

    var title = document.createElement('h3');
    title.innerText = "Link to Mind Map";
    title.className = 'mm-dialog-title';
    dialog.appendChild(title);

    var hint = document.createElement('div');
    hint.innerText = "✓ = Linked (click to unlink)";
    hint.className = 'mm-dialog-hint';
    dialog.appendChild(hint);

    var list = document.createElement('div');
    list.className = 'mm-dialog-list';

    mapsList.forEach(function (map) {
        var item = document.createElement('div');
        var checkmark = map.isLinked ? '✓ ' : '';
        item.innerText = checkmark + map.title;

        var bgColor = map.isLinked ? '#e8f5e9' : 'white';
        var hoverColor = map.isLinked ? '#c8e6c9' : '#e3f2fd';

        item.className = 'mm-dialog-list-item';
        item.style.color = map.isLinked ? '#2e7d32' : '#333';
        item.style.background = bgColor;
        item.style.fontWeight = map.isLinked ? 'bold' : 'normal';
        item.onmouseover = function () { this.style.background = hoverColor; };
        item.onmouseout = function () { this.style.background = bgColor; };
        item.onclick = function () {
            overlay.remove();
            if (map.isLinked) {
                // Unlink
                pycmd("unlink_map:" + JSON.stringify({
                    targetMapId: map.id
                }));
            } else {
                // Create link
                pycmd("create_map_link:" + JSON.stringify({
                    targetMapId: map.id
                }));
            }
        };
        list.appendChild(item);
    });

    dialog.appendChild(list);

    var cancelBtn = document.createElement('button');
    cancelBtn.innerText = "Cancel";
    cancelBtn.className = 'mm-dialog-cancel';
    cancelBtn.onclick = function () { overlay.remove(); };
    dialog.appendChild(cancelBtn);

    overlay.appendChild(dialog);
    document.body.appendChild(overlay);

    // Close on click outside dialog
    overlay.onclick = function (e) {
        if (e.target === overlay) overlay.remove();
    };
}

// Called by Python when map link is successfully created
function onMapLinkCreated(targetMapId, linkedNodeId) {
    console.log("Map link created: " + targetMapId + " -> " + linkedNodeId);
    // Refresh node markers
    setTimeout(markLinkedNodes, 300);
}


