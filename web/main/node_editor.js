document.addEventListener('keydown', function (e) {
    if (isEditing) {
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
    if (isEditing) {
        return;
    }

    // Handle floating node deletion
    if ((e.key === 'Delete' || e.key === 'Backspace') && selectedFloatingNode) {
        if (jm && !jm.get_editable()) return;
        e.preventDefault();
        console.log('Global delete handler - deleting floating node:', selectedFloatingNode.id);
        removeFloatingNode(selectedFloatingNode);
        selectedFloatingNode = null;
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
    if (matchHotkey(e, hotkeyConfig.toggle_collapse)) {
        if (toggleSelectedNodeCollapse()) {
            e.preventDefault();
            return;
        }
        // No children: do nothing
    }

    // Save hotkey
    if (matchHotkey(e, hotkeyConfig.save)) {
        e.preventDefault();
        saveMap();
        return;
    }

    // Refresh hotkey
    if (matchHotkey(e, hotkeyConfig.refresh)) {
        e.preventDefault();
        refreshMap();
        return;
    }

    // Focus root hotkey
    if (matchHotkey(e, hotkeyConfig.focus_root)) {
        e.preventDefault();
        if (jm) {
            var root = jm.get_root();
            if (root) {
                jm.select_node(root.id);
                scrollToNode(root.id);
            }
        }
        return;
    }

    // Create summary hotkey
    if (matchHotkey(e, hotkeyConfig.create_summary)) {
        e.preventDefault();
        if (jm && !jm.get_editable()) return;
        if (selectedNodes.length >= 2) {
            createSummary();
        } else {
            showToast('Select multiple nodes first (Shift+Click)');
        }
        return;
    }

    // Create boundary hotkey
    if (matchHotkey(e, hotkeyConfig.create_boundary)) {
        e.preventDefault();
        if (jm && !jm.get_editable()) return;
        if (selectedNodes.length >= 1) {
            createBoundary();
        } else {
            showToast('Select at least 1 node (Shift+Click)');
        }
        return;
    }

    // Delete boundary with Delete key
    if (e.key === 'Delete' || e.key === 'Backspace') {
        if (selectedBoundary) {
            e.preventDefault();
            deleteBoundary(selectedBoundary);
            return;
        }
    }

    if ((e.ctrlKey || e.metaKey) && e.key === 'z' && !e.shiftKey) {
        if (jm && !jm.get_editable()) return;
        e.preventDefault();
        undo();
        return;
    }

    if ((e.ctrlKey || e.metaKey) && (e.key === 'y' || (e.key === 'z' && e.shiftKey))) {
        if (jm && !jm.get_editable()) return;
        e.preventDefault();
        redo();
        return;
    }

    if ((e.ctrlKey || e.metaKey) && e.key === 'l') {
        e.preventDefault();
        toggleArrowMode();
        return;
    }

    if (!jm) return;
    var selected = jm.get_selected_node();
    if (!selected) return;

    if (!jm.get_editable() && (e.key === ' ' || e.key === 'Enter' || e.key === 'Tab' || e.key === 'Delete' || e.key === 'Backspace')) {
        return;
    }

    // Space key: Enter edit mode
    if (e.key === ' ' && !isEditing) {
        e.preventDefault();
        enterEditMode(selected);
        return;
    }

    // Enter key behavior depends on whether we're editing
    if (e.key === 'Enter') {
        e.preventDefault();
        if (isEditing) {
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
            jm.remove_node(selected);

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

// Enter edit mode for a node
function enterEditMode(node) {
    if (!node || isEditing) return;

    isEditing = true;
    editingNodeId = node.id;
    removeCustomContextMenu();

    // Get the node element directly
    var nodeElement = document.querySelector('jmnode[nodeid="' + node.id + '"]');
    if (!nodeElement) {
        isEditing = false;
        editingNodeId = null;
        return;
    }

    // Get current content and convert <br> to newlines
    var currentContent = node.topic;
    var plainText = currentContent.replace(/<br\s*\/?>/gi, '\n');

    // Store original HTML
    var originalHTML = nodeElement.innerHTML;

    // Clear node and prepare for editing
    nodeElement.innerHTML = '';
    nodeElement.style.padding = '0';
    nodeElement.style.display = 'inline-block';

    // Create textarea
    var textarea = document.createElement('textarea');
    textarea.id = 'input-box';
    textarea.value = plainText;

    // Get computed styles from node
    var computedStyle = window.getComputedStyle(nodeElement);

    // Apply styles to textarea
    textarea.style.cssText = `
        box-sizing: border-box;
        margin: 0;
        padding: 8px;
        border: 2px solid #4A90E2;
        border-radius: 4px;
        outline: none;
        background: #fff;
        font-family: ${computedStyle.fontFamily};
        font-size: ${computedStyle.fontSize};
        font-weight: ${computedStyle.fontWeight};
        color: #000;
        line-height: 1.5;
        resize: none;
        overflow: hidden;
        white-space: pre-wrap;
        word-wrap: break-word;
        min-width: 120px;
        min-height: 30px;
        max-width: 500px;
    `;

    // Add textarea to node
    nodeElement.appendChild(textarea);

    // Auto-resize function - REAL-TIME
    function autoResize() {
        if (!textarea || !textarea.parentNode) return;

        // Create hidden div for measurement
        var measureDiv = document.createElement('div');
        measureDiv.style.cssText = `
            position: absolute;
            visibility: hidden;
            white-space: pre-wrap;
            word-wrap: break-word;
            font-family: ${textarea.style.fontFamily};
            font-size: ${textarea.style.fontSize};
            font-weight: ${textarea.style.fontWeight};
            line-height: ${textarea.style.lineHeight};
            padding: ${textarea.style.padding};
            border: ${textarea.style.border};
            box-sizing: border-box;
            max-width: 500px;
        `;
        measureDiv.textContent = textarea.value || 'W';
        document.body.appendChild(measureDiv);

        var width = Math.max(120, Math.min(500, measureDiv.offsetWidth));
        var height = Math.max(30, measureDiv.offsetHeight);
        document.body.removeChild(measureDiv);

        // Apply to both textarea and node
        textarea.style.width = width + 'px';
        textarea.style.height = height + 'px';
        nodeElement.style.width = width + 'px';
        nodeElement.style.height = height + 'px';

        console.log('Resized:', width, 'x', height);
    }

    textarea.focus();
    textarea.select();
    setTimeout(autoResize, 10);

    // Keydown handler
    textarea.addEventListener('keydown', function (e) {
        e.stopPropagation();
        e.stopImmediatePropagation();

        if (matchHotkey(e, hotkeyConfig.bold)) {
            e.preventDefault();
            toggleWrapSelection(textarea, '<b>', '</b>');
            setTimeout(autoResize, 0);
            return false;
        }

        if (matchHotkey(e, hotkeyConfig.italic)) {
            e.preventDefault();
            toggleWrapSelection(textarea, '<i>', '</i>');
            setTimeout(autoResize, 0);
            return false;
        }

        if (matchHotkey(e, hotkeyConfig.inline_code)) {
            e.preventDefault();
            wrapSelectionAsEscapedHtml(textarea, '<code>', '</code>');
            setTimeout(autoResize, 0);
            return false;
        }

        if (matchHotkey(e, hotkeyConfig.code_block)) {
            e.preventDefault();
            wrapSelectionAsEscapedHtml(textarea, '<pre><code>', '</code></pre>');
            setTimeout(autoResize, 0);
            return false;
        }

        // Shift+Enter: insert newline manually
        if (e.key === 'Enter' && e.shiftKey) {
            e.preventDefault();
            var start = textarea.selectionStart;
            var end = textarea.selectionEnd;
            textarea.value = textarea.value.substring(0, start) + '\n' + textarea.value.substring(end);
            textarea.selectionStart = textarea.selectionEnd = start + 1;
            setTimeout(autoResize, 0);
            console.log('Newline inserted');
            return false;
        }

        // Enter: exit
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            exitEditMode();
            return false;
        }

        // Escape: cancel
        if (e.key === 'Escape') {
            e.preventDefault();
            removeCustomContextMenu();
            nodeElement.innerHTML = originalHTML;
            nodeElement.style.width = '';
            nodeElement.style.height = '';
            nodeElement.style.padding = '';
            isEditing = false;
            editingNodeId = null;
            document.getElementById('jsmind_container').focus();
            return false;
        }

        setTimeout(autoResize, 0);
    }, true);

    // Input handler - resize on every input
    textarea.addEventListener('input', function (e) {
        e.stopPropagation();
        autoResize();
    }, true);

    textarea.addEventListener('paste', function () {
        setTimeout(autoResize, 10);
    }, true);

    textarea.addEventListener('mousedown', function (e) {
        e.stopPropagation();
        e.stopImmediatePropagation();
    }, true);

    textarea.addEventListener('click', function (e) {
        e.stopPropagation();
        e.stopImmediatePropagation();
    }, true);

    textarea.addEventListener('contextmenu', function (e) {
        e.preventDefault();
        e.stopPropagation();
        e.stopImmediatePropagation();
        showEditFormattingContextMenu(e.clientX, e.clientY, textarea, function () {
            setTimeout(autoResize, 0);
        });
    }, true);
}

// Exit edit mode
function exitEditMode() {
    if (!isEditing) return;

    removeCustomContextMenu();

    var inputBox = document.getElementById('input-box');
    if (!inputBox || !editingNodeId) {
        isEditing = false;
        editingNodeId = null;
        return;
    }

    var newText = escapeCodeTagsForDisplay(inputBox.value);
    var node = jm.get_node(editingNodeId);

    if (node) {
        var nodeElement = document.querySelector('jmnode[nodeid="' + editingNodeId + '"]');

        if (nodeElement) {
            nodeElement.innerHTML = '';
            nodeElement.style.width = '';
            nodeElement.style.height = '';
            nodeElement.style.padding = '';
            nodeElement.style.whiteSpace = 'normal';
            nodeElement.style.wordWrap = 'break-word';
            nodeElement.style.display = 'inline-block';
            nodeElement.style.maxWidth = '500px';

            if (newText && newText.trim() !== '') {
                // Convert newlines to <br> for display
                var htmlText = newText.replace(/\r?\n/g, '<br>');
                jm.update_node(editingNodeId, htmlText);

                if (jm.view.opts.support_html) {
                    nodeElement.innerHTML = htmlText;
                } else {
                    nodeElement.textContent = htmlText;
                }
            } else {
                if (jm.view.opts.support_html) {
                    nodeElement.innerHTML = node.topic;
                } else {
                    nodeElement.textContent = node.topic;
                }
            }
        }
    }

    isEditing = false;
    editingNodeId = null;

    var container = document.getElementById('jsmind_container');
    if (container) container.focus();

    saveHistory();

    // Auto-save immediately and refresh to fix position
    console.log('Auto-saving after edit...');
    autoSave();

    // Trigger refresh after a brief delay to allow save to complete
    setTimeout(function () {
        console.log('Auto-refreshing to fix node position...');
        refreshMap();
    }, 100);

    setTimeout(renderMath, 300);
}

// Handle clicks during edit mode - capture phase to intercept early
document.addEventListener('mousedown', function (e) {
    if (isEditing && editingNodeId) {
        console.log('Mousedown in edit mode, target:', e.target);

        // Allow interacting with the formatting context menu without leaving edit mode.
        if (isInCustomContextMenu(e.target)) {
            e.stopPropagation();
            e.stopImmediatePropagation();
            return;
        }

        // Get the node element being edited
        var node = jm.get_node(editingNodeId);
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
        e.preventDefault();
        e.stopPropagation();
        e.stopImmediatePropagation();
        exitEditMode();
        return;
    }
}, true);

// Also handle click events to prevent any unwanted behavior
document.addEventListener('click', function (e) {
    if (isEditing && editingNodeId) {
        // Allow clicking menu items without exiting edit mode.
        if (isInCustomContextMenu(e.target)) {
            e.stopPropagation();
            e.stopImmediatePropagation();
            return;
        }

        var node = jm.get_node(editingNodeId);
        if (node && node._data && node._data.view) {
            var nodeElement = node._data.view.element;

            // Only allow clicks inside the node element
            if (!nodeElement || !nodeElement.contains(e.target)) {
                e.preventDefault();
                e.stopPropagation();
                e.stopImmediatePropagation();
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
    if (isEditing) {
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
    if (!isEditing || !editingNodeId) return;

    var textarea = document.getElementById('input-box');
    if (!textarea) return;

    e.preventDefault();
    e.stopPropagation();
    e.stopImmediatePropagation();
    showEditFormattingContextMenu(e.clientX, e.clientY, textarea, function () {
        // Auto-resize is defined inside enterEditMode; trigger input to recalc size.
        textarea.dispatchEvent(new Event('input'));
    });
}, true);

// --- Card Linking Features ---
