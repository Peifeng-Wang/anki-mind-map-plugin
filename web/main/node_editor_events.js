// Document-level event listeners for the editor:
// - keyboard hotkey dispatch (navigation, save, undo/redo, summary/boundary, edit mode toggle)
// - mouse / click guards that arbitrate edit mode (entering, staying, exiting)
// - right-click formatting menu while a node is being edited
//
// The actual edit-mode lifecycle lives in node_editor.js (enterEditMode/exitEditMode);
// this file only wires the events that drive it.

document.addEventListener('keydown', function (e) {
    if (MM.state.isEditing) {
        // Intercept ALL events in capture phase
        e.stopPropagation();
        e.stopImmediatePropagation();

        // Shift+Enter: allow new line
        if (e.key === 'Enter' && e.shiftKey) {
            // Let it pass through to create new line
            return;
        }

        // Enter without Shift: exit edit mode
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            exitEditMode();
        }
        // All other keys (including arrows) work normally in the input
        return;
    }
}, true);  // Use capture phase!

// Regular event listener for non-editing mode
document.addEventListener('keydown', function (e) {
    // Skip if editing
    if (MM.state.isEditing) {
        return;
    }

    // Handle floating node deletion
    if ((e.key === 'Delete' || e.key === 'Backspace') && MM.state.selectedFloatingNode) {
        if (MM.state.jm && !MM.state.jm.get_editable()) return;
        e.preventDefault();
        console.log('Global delete handler - deleting floating node:', MM.state.selectedFloatingNode.id);
        removeFloatingNode(MM.state.selectedFloatingNode);
        MM.state.selectedFloatingNode = null;
        saveHistory();
        scheduleAutoSave();
        return;
    }

    if (e.key === 'ArrowUp') {
        e.preventDefault();
        navigateUp();
        return;
    }

    if (e.key === 'ArrowDown') {
        e.preventDefault();
        navigateDown();
        return;
    }

    if (e.key === 'ArrowLeft') {
        e.preventDefault();
        navigateLeft();
        return;
    }

    if (e.key === 'ArrowRight') {
        e.preventDefault();
        navigateRight();
        return;
    }

    // Toggle collapse/expand for selected node (only if it has children)
    if (matchHotkey(e, MM.state.hotkeyConfig.toggle_collapse)) {
        if (toggleSelectedNodeCollapse()) {
            e.preventDefault();
            return;
        }
        // No children: do nothing
    }

    // Save hotkey
    if (matchHotkey(e, MM.state.hotkeyConfig.save)) {
        e.preventDefault();
        saveMap();
        return;
    }

    // Refresh hotkey
    if (matchHotkey(e, MM.state.hotkeyConfig.refresh)) {
        e.preventDefault();
        refreshMap();
        return;
    }

    // Focus root hotkey
    if (matchHotkey(e, MM.state.hotkeyConfig.focus_root)) {
        e.preventDefault();
        if (MM.state.jm) {
            var root = MM.state.jm.get_root();
            if (root) {
                MM.state.jm.select_node(root.id);
                scrollToNode(root.id);
            }
        }
        return;
    }

    // Create summary hotkey
    if (matchHotkey(e, MM.state.hotkeyConfig.create_summary)) {
        e.preventDefault();
        if (MM.state.jm && !MM.state.jm.get_editable()) return;
        if (MM.state.selectedNodes.length >= 2) {
            createSummary();
        } else {
            showToast('Select multiple nodes first (Shift+Click)');
        }
        return;
    }

    // Create boundary hotkey
    if (matchHotkey(e, MM.state.hotkeyConfig.create_boundary)) {
        e.preventDefault();
        if (MM.state.jm && !MM.state.jm.get_editable()) return;
        if (MM.state.selectedNodes.length >= 1) {
            createBoundary();
        } else {
            showToast('Select at least 1 node (Shift+Click)');
        }
        return;
    }

    // Delete boundary with Delete key
    if (e.key === 'Delete' || e.key === 'Backspace') {
        if (MM.state.selectedBoundary) {
            e.preventDefault();
            deleteBoundary(MM.state.selectedBoundary);
            return;
        }
    }

    if ((e.ctrlKey || e.metaKey) && e.key === 'z' && !e.shiftKey) {
        if (MM.state.jm && !MM.state.jm.get_editable()) return;
        e.preventDefault();
        undo();
        return;
    }

    if ((e.ctrlKey || e.metaKey) && (e.key === 'y' || (e.key === 'z' && e.shiftKey))) {
        if (MM.state.jm && !MM.state.jm.get_editable()) return;
        e.preventDefault();
        redo();
        return;
    }

    if ((e.ctrlKey || e.metaKey) && e.key === 'l') {
        e.preventDefault();
        toggleArrowMode();
        return;
    }

    if (!MM.state.jm) return;
    var selected = MM.state.jm.get_selected_node();
    if (!selected) return;

    if (!MM.state.jm.get_editable() && (e.key === ' ' || e.key === 'Enter' || e.key === 'Tab' || e.key === 'Delete' || e.key === 'Backspace')) {
        return;
    }

    // Space key: Enter edit mode
    if (e.key === ' ' && !MM.state.isEditing) {
        e.preventDefault();
        enterEditMode(selected);
        return;
    }

    // Enter key behavior depends on whether we're editing
    if (e.key === 'Enter') {
        e.preventDefault();
        if (MM.state.isEditing) {
            // Exit edit mode
            exitEditMode();
        } else {
            // Add sibling (original behavior)
            addSibling();
        }
        return;
    }

    if (e.key === 'Tab') {
        e.preventDefault();
        addChild();
    } else if (e.key === 'Delete' || e.key === 'Backspace') {
        e.preventDefault();
        if (selected && !selected.isroot) {
            // Check if this is a summary node - use special deletion
            if (selected.data && selected.data.isSummaryNode) {
                deleteSummaryNode(selected.id);
                return;
            }

            // Check if this is a map-linked node and notify backend
            if (selected.data && selected.data.isMapLink && selected.data.sourceMapId) {
                pycmd("delete_map_link:" + JSON.stringify({
                    sourceMapId: selected.data.sourceMapId,
                    linkedNodeId: selected.id
                }));
            }
            MM.state.jm.remove_node(selected);

            // Re-render braces in case deleted node was part of a summary
            renderSummaryBraces();

            saveHistory();
            scheduleAutoSave();
        }
    }

});

document.addEventListener('blur', function (e) {
    if (e.target.id === 'input-box') {
        saveHistory();
        scheduleAutoSave();
    }
}, true);

// Handle clicks during edit mode - capture phase to intercept early
document.addEventListener('mousedown', function (e) {
    if (MM.state.isEditing && MM.state.editingNodeId) {
        console.log('Mousedown in edit mode, target:', e.target);

        // Allow interacting with the formatting context menu without leaving edit mode.
        if (isInCustomContextMenu(e.target)) {
            e.stopPropagation();
            e.stopImmediatePropagation();
            return;
        }

        // Get the node element being edited
        var node = MM.state.jm.get_node(MM.state.editingNodeId);
        if (node && node._data && node._data.view) {
            var nodeElement = node._data.view.element;
            console.log('Node element:', nodeElement);
            console.log('Contains target?', nodeElement.contains(e.target));

            // Check if click is inside the node element (which contains the input box)
            if (nodeElement && nodeElement.contains(e.target)) {
                // Click inside node/input - allow normal behavior (cursor positioning)
                console.log('Click inside node - allowing');
                e.stopPropagation();
                e.stopImmediatePropagation();
                return;
            }
        }

        // Click outside node - exit edit mode
        console.log('Click outside node - exiting edit mode');
        swallowEvent(e);
        exitEditMode();
        return;
    }
}, true);

// Also handle click events to prevent any unwanted behavior
document.addEventListener('click', function (e) {
    if (MM.state.isEditing && MM.state.editingNodeId) {
        // Allow clicking menu items without exiting edit mode.
        if (isInCustomContextMenu(e.target)) {
            e.stopPropagation();
            e.stopImmediatePropagation();
            return;
        }

        var node = MM.state.jm.get_node(MM.state.editingNodeId);
        if (node && node._data && node._data.view) {
            var nodeElement = node._data.view.element;

            // Only allow clicks inside the node element
            if (!nodeElement || !nodeElement.contains(e.target)) {
                swallowEvent(e);
                return;
            }
        }
        // Click inside - stop propagation
        e.stopPropagation();
        e.stopImmediatePropagation();
        return;
    }
}, true);

// Regular click handler for non-editing mode
document.addEventListener('click', function (e) {
    // Don't interfere if editing
    if (MM.state.isEditing) {
        return;
    }

    var container = document.getElementById('jsmind_container');
    if (container) container.focus();

    if (!e.ctrlKey && !e.shiftKey) {
        clearSelection();
    }
});

// While editing a node, right-click anywhere should show formatting options (instead of node actions).
document.addEventListener('contextmenu', function (e) {
    if (!MM.state.isEditing || !MM.state.editingNodeId) return;

    var textarea = document.getElementById('input-box');
    if (!textarea) return;

    swallowEvent(e);
    showEditFormattingContextMenu(e.clientX, e.clientY, textarea, function () {
        // Auto-resize is defined inside enterEditMode; trigger input to recalc size.
        textarea.dispatchEvent(new Event('input'));
    });
}, true);
