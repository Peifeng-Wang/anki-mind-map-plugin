// Summary brace commands: create, edit, delete summary nodes (and their braces).

// Create a summary for selected nodes
function createSummary() {
    if (!MM.state.jm) return;
    if (MM.state.jm && !MM.state.jm.get_editable()) {
        showToast('Read-only mode');
        return;
    }

    var validation = validateSummarySelection();
    if (!validation.valid) {
        showToast(validation.reason);
        return;
    }

    var nodes = validation.nodes;

    // Calculate brace data based on selected nodes positions
    var direction = nodes[0]._data.layout.direction;
    var nodeIds = nodes.map(function (n) { return n.id; });

    // minY/maxY: vertical range covers only selected nodes
    // outerX: horizontal position based on ALL descendants of selected nodes
    var minY = Infinity, maxY = -Infinity, outerX = 0;

    for (var i = 0; i < nodes.length; i++) {
        if (!nodes[i] || !isMindNodeVisible(nodes[i])) continue;
        var nodeBox = getNodeBoxFromView(nodes[i]);
        if (!nodeBox) continue;
        var nodeTop = nodeBox.top;
        var nodeBottom = nodeBox.bottom;

        // Vertical range: only selected nodes
        if (nodeTop < minY) minY = nodeTop;
        if (nodeBottom > maxY) maxY = nodeBottom;

        // Horizontal position: include all descendants
        var nodeOuterX = findOuterXFromNode(nodes[i], direction);
        if (nodeOuterX !== null) {
            if (direction === 1) { // right side
                if (nodeOuterX > outerX) outerX = nodeOuterX;
            } else { // left side
                if (i === 0 || nodeOuterX < outerX) outerX = nodeOuterX;
            }
        }
    }


    // Create summary node as a floating-style special node
    var summaryNodeId = MM.state.summaryBraceIdPrefix + Date.now();

    // Position for the summary node (after the brace)
    var braceWidth = 40;
    var spacing = 50;
    var braceTipY = (minY + maxY) / 2; // Vertical center of brace tip
    var summaryAnchorX = (direction === 1)
        ? (outerX + braceWidth + spacing)
        : (outerX - braceWidth - spacing);

    // Create the summary node element
    var nodesContainer = getJsMindNodesEl();
    if (!nodesContainer) return;

    var summaryElement = document.createElement('jmnode');
    summaryElement.setAttribute('nodeid', summaryNodeId);
    summaryElement.innerHTML = 'Summary';
    // Override default jmnode absolute positioning so wrapper can size to content.
    summaryElement.style.position = 'relative';
    summaryElement.style.pointerEvents = 'auto';
    summaryElement.setAttribute('data-is-summary', 'true');

    nodesContainer.appendChild(summaryElement);
    var summaryWrapper = ensureSummaryWrapper(summaryElement, nodesContainer);
    if (!summaryWrapper) return;

    // Position using a wrapper so theme hover transforms on <jmnode> don't break alignment.
    summaryWrapper.style.left = summaryAnchorX + 'px';
    summaryWrapper.style.top = braceTipY + 'px';
    summaryWrapper.style.transform = (direction === 1)
        ? 'translate(0, -50%)'
        : 'translate(-100%, -50%)';
    summaryWrapper.style.visibility = 'visible';

    // Store brace data with summary node info
    var braceData = {
        id: 'brace_' + Date.now(),
        summarizedNodeIds: nodeIds,
        summaryNodeId: summaryNodeId,
        direction: direction,
        color: MM.state.braceColor,
        summaryX: summaryAnchorX,
        summaryY: braceTipY,
        summaryTopic: 'Summary'
    };
    MM.state.summaryBraces.push(braceData);

    // Setup edit and drag for the summary node
    setupSummaryNodeInteraction(summaryElement, braceData);

    // Clear selection
    clearSelection();

    // Redraw braces
    setTimeout(function () {
        renderSummaryBraces();
    }, 50);

    // Save
    saveHistory();
    scheduleAutoSave();

    showToast('Summary created');
}

// Setup interaction for summary node (edit, drag, delete)
function setupSummaryNodeInteraction(element, braceData) {
    // Click to select
    element.addEventListener('click', function (e) {
        if (MM.state.jm && !MM.state.jm.get_editable()) return;
        e.preventDefault();
        e.stopPropagation();

        // Deselect jsMind nodes
        MM.state.jm.select_clear();

        // Visual selection
        document.querySelectorAll('jmnode[data-is-summary="true"]').forEach(function (el) {
            el.style.outline = 'none';
        });
        element.style.outline = '3px solid #60a5fa';
        element.setAttribute('tabindex', '0');
        element.focus();
    });

    // Double-click to edit
    element.addEventListener('dblclick', function (e) {
        if (MM.state.jm && !MM.state.jm.get_editable()) return;
        e.preventDefault();
        e.stopPropagation();
        enterSummaryEditMode(element, braceData);
    });

    // Keyboard events
    element.addEventListener('keydown', function (e) {
        if (MM.state.jm && !MM.state.jm.get_editable()) return;

        // Space: edit
        if (e.key === ' ') {
            e.preventDefault();
            enterSummaryEditMode(element, braceData);
        }
        // Delete/Backspace: remove
        else if (e.key === 'Delete' || e.key === 'Backspace') {
            e.preventDefault();
            deleteSummaryByElement(element, braceData);
        }
    });
}

// Enter edit mode for summary node
function enterSummaryEditMode(element, braceData) {
    var currentText = braceData.summaryTopic || 'Summary';

    var input = document.createElement('textarea');
    input.value = currentText;
    input.style.cssText = 'width:100%;height:100%;border:none;outline:none;background:transparent;font-family:inherit;font-size:inherit;text-align:center;resize:none;padding:0;margin:0;color:white;';

    element.innerHTML = '';
    element.appendChild(input);
    input.focus();
    input.select();

    function saveEdit() {
        var newText = input.value || 'Summary';
        braceData.summaryTopic = newText;
        element.innerHTML = newText;
        saveHistory();
        scheduleAutoSave();
    }

    input.addEventListener('keydown', function (e) {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            saveEdit();
        } else if (e.key === 'Escape') {
            e.preventDefault();
            element.innerHTML = currentText;
        }
        e.stopPropagation();
    });

    input.addEventListener('blur', function () {
        saveEdit();
    });
}

// Delete summary by element reference
function deleteSummaryByElement(element, braceData) {
    removeSummaryElementAndWrapper(element);

    // Remove from braces array
    var idx = MM.state.summaryBraces.indexOf(braceData);
    if (idx > -1) {
        MM.state.summaryBraces.splice(idx, 1);
    }

    // Redraw
    renderSummaryBraces();
    saveHistory();
    scheduleAutoSave();
}

// Delete a summary and its brace by summary-node id
function deleteSummaryNode(nodeId) {
    // Find and remove the brace
    var braceIndex = -1;
    for (var i = 0; i < MM.state.summaryBraces.length; i++) {
        if (MM.state.summaryBraces[i].summaryNodeId === nodeId) {
            braceIndex = i;
            break;
        }
    }

    if (braceIndex > -1) {
        MM.state.summaryBraces.splice(braceIndex, 1);
    }

    // Remove the floating summary node element
    var summaryElement = document.querySelector('jmnode[nodeid="' + nodeId + '"]');
    removeSummaryElementAndWrapper(summaryElement);

    // Redraw
    renderSummaryBraces();
    saveHistory();
    scheduleAutoSave();
}
