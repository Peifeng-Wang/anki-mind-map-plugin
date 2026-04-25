function validateSummarySelection() {
    if (selectedNodes.length < 2) {
        return { valid: false, reason: 'Select at least 2 nodes' };
    }

    // Get jsMind nodes and check they share same parent
    var nodes = [];
    var parentId = null;

    for (var i = 0; i < selectedNodes.length; i++) {
        var nodeId = selectedNodes[i].getAttribute('nodeid');
        var node = jm.get_node(nodeId);

        if (!node) return { valid: false, reason: 'Invalid node' };
        if (node.isroot) return { valid: false, reason: 'Cannot include root' };

        // Check if node is a summary node
        if (node.data && node.data.isSummaryNode) {
            return { valid: false, reason: 'Cannot include summary nodes' };
        }

        if (parentId === null) {
            parentId = node.parent;
        } else if (node.parent !== parentId) {
            return { valid: false, reason: 'Nodes must be siblings' };
        }

        nodes.push(node);
    }

    // All nodes are valid siblings - no consecutive check needed
    var parentNode = jm.get_node(parentId);
    if (!parentNode) return { valid: false, reason: 'Parent not found' };

    return {
        valid: true,
        nodes: nodes,
        parent: parentNode
    };
}

function ensureSummaryWrapper(summaryElement, nodesContainer) {
    if (!summaryElement) return null;
    var parent = summaryElement.parentElement;
    if (parent && parent.getAttribute && parent.getAttribute('data-summary-wrapper') === 'true') {
        // Normalize older wrapper/node styles to the current, zoom-stable layout.
        parent.style.position = 'absolute';
        parent.style.display = 'inline-block';
        parent.style.overflow = '';
        parent.style.width = '';
        parent.style.height = '';
        parent.style.pointerEvents = 'none';

        summaryElement.style.position = 'relative';
        summaryElement.style.left = '';
        summaryElement.style.top = '';
        summaryElement.style.pointerEvents = 'auto';
        return parent;
    }

    var wrapper = document.createElement('div');
    wrapper.setAttribute('data-summary-wrapper', 'true');
    wrapper.style.cssText = [
        'position:absolute',
        'left:' + (summaryElement.style.left || '0px'),
        'top:' + (summaryElement.style.top || '0px'),
        'display:inline-block',
        'z-index:2',
        'pointer-events:none'
    ].join(';') + ';';

    // Place the wrapper where the node currently is, then reset the node to be wrapper-sized.
    var insertParent = nodesContainer || parent;
    if (!insertParent) return null;
    insertParent.insertBefore(wrapper, summaryElement);
    wrapper.appendChild(summaryElement);

    // jmnode defaults to position:absolute from jsmind.css; override for stable wrapper sizing.
    summaryElement.style.position = 'relative';
    summaryElement.style.left = '';
    summaryElement.style.top = '';
    summaryElement.style.pointerEvents = 'auto';

    return wrapper;
}

function removeSummaryElementAndWrapper(summaryElement) {
    if (!summaryElement) return;
    var wrapper = summaryElement.parentElement;
    if (wrapper && wrapper.getAttribute && wrapper.getAttribute('data-summary-wrapper') === 'true') {
        if (wrapper.parentNode) wrapper.parentNode.removeChild(wrapper);
        return;
    }
    if (summaryElement.parentNode) summaryElement.parentNode.removeChild(summaryElement);
}

function getSummarySizeInMap(summaryElement) {
    var z = (jm && jm.view && jm.view.actualZoom) || 1;
    if (!z) z = 1;

    var w = 0, h = 0;
    if (summaryElement && summaryElement.isConnected) {
        var rect = summaryElement.getBoundingClientRect();
        if (rect && rect.width && rect.height) {
            w = rect.width / z;
            h = rect.height / z;
        }
    }
    if (!w) w = 80;
    if (!h) h = 30;
    return { w: w, h: h };
}

function getSummaryBoxFromBraceData(braceData, summaryElement) {
    if (!braceData) return null;
    var anchorX = braceData.summaryX;
    var anchorY = braceData.summaryY;
    if (typeof anchorX !== 'number' || typeof anchorY !== 'number') return null;

    var size = getSummarySizeInMap(summaryElement);

    var left, right;
    if (braceData.direction === 1) {
        left = anchorX;
        right = anchorX + size.w;
    } else {
        right = anchorX;
        left = anchorX - size.w;
    }
    var top = anchorY - size.h / 2;
    var bottom = anchorY + size.h / 2;
    return { left: left, right: right, top: top, bottom: bottom };
}


// Create a summary for selected nodes

function createSummary() {
    if (!jm) return;
    if (jm && !jm.get_editable()) {
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

    // Helper function to find rightmost/leftmost X of a node and all its descendants
    function findOuterXRecursive(node, dir) {
        var extreme = null;
        if (!node || !isMindNodeVisible(node)) return extreme;
        var box = getNodeBoxFromView(node);
        if (!box) return extreme;

        if (dir === 1) { // right side - find rightmost
            extreme = box.right;
        } else { // left side - find leftmost
            extreme = box.left;
        }

        if (node.expanded === false) return extreme;

        // Check all children
        if (node.children && node.children.length > 0) {
            for (var c = 0; c < node.children.length; c++) {
                var childExtreme = findOuterXRecursive(node.children[c], dir);
                if (childExtreme !== null) {
                    if (dir === 1) {
                        if (extreme === null || childExtreme > extreme) extreme = childExtreme;
                    } else {
                        if (extreme === null || childExtreme < extreme) extreme = childExtreme;
                    }
                }
            }
        }

        return extreme;
    }

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
        var nodeOuterX = findOuterXRecursive(nodes[i], direction);
        if (nodeOuterX !== null) {
            if (direction === 1) { // right side
                if (nodeOuterX > outerX) outerX = nodeOuterX;
            } else { // left side
                if (i === 0 || nodeOuterX < outerX) outerX = nodeOuterX;
            }
        }
    }


    // Create summary node as a floating-style special node
    var summaryNodeId = summaryBraceIdPrefix + Date.now();

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
        color: braceColor,
        summaryX: summaryAnchorX,
        summaryY: braceTipY,
        summaryTopic: 'Summary'
    };
    summaryBraces.push(braceData);

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
        if (jm && !jm.get_editable()) return;
        e.preventDefault();
        e.stopPropagation();

        // Deselect jsMind nodes
        jm.select_clear();

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
        if (jm && !jm.get_editable()) return;
        e.preventDefault();
        e.stopPropagation();
        enterSummaryEditMode(element, braceData);
    });

    // Keyboard events
    element.addEventListener('keydown', function (e) {
        if (jm && !jm.get_editable()) return;

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
    var idx = summaryBraces.indexOf(braceData);
    if (idx > -1) {
        summaryBraces.splice(idx, 1);
    }

    // Redraw
    renderSummaryBraces();
    saveHistory();
    scheduleAutoSave();
}


// Mark summary nodes with data attribute for CSS styling
function markSummaryNodes() {
    if (!jm) return;

    var allNodes = document.querySelectorAll('jmnode');
    allNodes.forEach(function (nodeElement) {
        var nodeId = nodeElement.getAttribute('nodeid');
        if (!nodeId) return;

        var node = jm.get_node(nodeId);
        if (!node) return;

        if (node.data && node.data.isSummaryNode) {
            nodeElement.setAttribute('data-is-summary', 'true');
            // Apply brace color to node
            var color = node.data.braceColor || braceColor;
            nodeElement.style.setProperty('--summary-color', color);
        } else {
            nodeElement.removeAttribute('data-is-summary');
        }
    });
}

// Render all summary braces
function renderSummaryBraces() {
    // Remove existing brace SVGs
    var existingBraces = document.querySelectorAll('.summary-brace');
    existingBraces.forEach(function (el) { el.remove(); });

    if (!jm || !jm.view) return;

    var container = document.getElementById('jsmind_container');
    if (!container) return;

    var panel = getJsMindPanelEl() || container.querySelector('.jsmind-inner');
    if (!panel) return;

    // Summary overlay lives under <jmnodes> to share zoom/position with nodes.
    var nodesEl = getJsMindNodesEl() || panel.querySelector('jmnodes');
    if (!nodesEl) return;

    // Migrate from older versions that placed the layer under panel.
    var legacy = panel.querySelector('#summary-overlay-layer');
    if (legacy && legacy.parentNode === panel) legacy.remove();

    var summaryLayer = getOrCreateOverlayLayer(nodesEl, 'summary-overlay-layer', 1, 'none', false);
    if (!summaryLayer) return;

    // Filter out invalid braces (require at least 2 source nodes)
    summaryBraces = summaryBraces.filter(function (braceData) {
        var validNodes = braceData.summarizedNodeIds.filter(function (id) {
            return jm.get_node(id) !== null;
        });
        // If less than 2 nodes remain, remove the summary brace and its node
        if (validNodes.length < 2) {
            // Remove the summary node element
            var summaryElement = document.querySelector('jmnode[nodeid="' + braceData.summaryNodeId + '"]');
            removeSummaryElementAndWrapper(summaryElement);
            return false;
        }
        // Update the summarized node IDs to only include valid ones
        braceData.summarizedNodeIds = validNodes;
        return true;
    });

    // Auto-detect siblings that should be added to existing braces
    summaryBraces.forEach(function (braceData) {
        if (braceData.summarizedNodeIds.length === 0) return;

        // Get the parent of summarized nodes
        var firstNodeId = braceData.summarizedNodeIds[0];
        var firstNode = jm.get_node(firstNodeId);
        if (!firstNode || !firstNode.parent) return;

        var parentNode = firstNode.parent;
        var siblings = parentNode.children || [];

        // Get vertical range of current summarized nodes (map coordinate space; independent of zoom).
        var minY = Infinity, maxY = -Infinity;

        braceData.summarizedNodeIds.forEach(function (nodeId) {
            var node = jm.get_node(nodeId);
            if (!node || !isMindNodeVisible(node)) return;
            var box = getNodeBoxFromView(node);
            if (!box) return;
            if (box.top < minY) minY = box.top;
            if (box.bottom > maxY) maxY = box.bottom;
        });
        if (minY === Infinity || maxY === -Infinity) return;

        // Check each sibling to see if it falls within the vertical range
        siblings.forEach(function (sibling) {
            // Skip if already in the list or is a summary node
            if (braceData.summarizedNodeIds.indexOf(sibling.id) !== -1) return;
            if (sibling.id.startsWith('summary_')) return;
            if (sibling.data && sibling.data.isSummaryNode) return;

            // Check direction matches
            if (sibling._data && sibling._data.layout) {
                if (sibling._data.layout.direction !== braceData.direction) return;
            }

            // Get sibling position
            if (!sibling._data || !sibling._data.view) return;
            if (!isMindNodeVisible(sibling)) return;
            var sibBox = getNodeBoxFromView(sibling);
            if (!sibBox) return;
            var sibMidY = (sibBox.top + sibBox.bottom) / 2;

            // If sibling's center is within the brace vertical range, add it
            if (sibMidY >= minY && sibMidY <= maxY) {
                braceData.summarizedNodeIds.push(sibling.id);
            }
        });
    });

    summaryBraces.forEach(function (braceData) {
        renderSingleBrace(braceData, panel, container, summaryLayer);
    });
}

// Render a single brace
function renderSingleBrace(braceData, panel, container, summaryLayer) {
    // Get positions of summarized nodes
    var minY = Infinity, maxY = -Infinity;
    var outerX = null;
    var validNodeCount = 0;

    // Helper function to find rightmost/leftmost X of a node and all its descendants
    function findOuterXRecursive(node, dir) {
        var extreme = null;
        if (!node || !isMindNodeVisible(node)) return extreme;
        var box = getNodeBoxFromView(node);
        if (!box) return extreme;

        if (dir === 1) {
            extreme = box.right;
        } else {
            extreme = box.left;
        }

        // If the node is collapsed, its descendants are not visible and should not affect overlays.
        if (node.expanded === false) return extreme;

        if (node.children && node.children.length > 0) {
            for (var c = 0; c < node.children.length; c++) {
                var childExtreme = findOuterXRecursive(node.children[c], dir);
                if (childExtreme !== null) {
                    if (dir === 1) {
                        if (extreme === null || childExtreme > extreme) extreme = childExtreme;
                    } else {
                        if (extreme === null || childExtreme < extreme) extreme = childExtreme;
                    }
                }
            }
        }

        return extreme;
    }

    for (var i = 0; i < braceData.summarizedNodeIds.length; i++) {
        var nodeId = braceData.summarizedNodeIds[i];
        var node = jm.get_node(nodeId);
        if (!node || !isMindNodeVisible(node)) continue;
        var box = getNodeBoxFromView(node);
        if (!box) continue;

        validNodeCount++;
        var nodeTop = box.top;
        var nodeBottom = box.bottom;

        // Vertical range: only selected nodes
        if (nodeTop < minY) minY = nodeTop;
        if (nodeBottom > maxY) maxY = nodeBottom;

        // Horizontal position: include all descendants
        var nodeOuterX = findOuterXRecursive(node, braceData.direction);
        if (nodeOuterX !== null) {
            if (braceData.direction === 1) { // right side
                if (outerX === null || nodeOuterX > outerX) outerX = nodeOuterX;
            } else { // left side
                if (outerX === null || nodeOuterX < outerX) outerX = nodeOuterX;
            }
        }
    }

    // If summarized nodes are hidden (e.g. parent collapsed), hide the floating summary node and skip drawing.
    if (validNodeCount < 2 || outerX === null || minY === Infinity || maxY === -Infinity) {
        var existingSummary = document.querySelector('jmnode[nodeid="' + braceData.summaryNodeId + '"]');
        if (existingSummary) {
            var wrap = existingSummary.parentElement;
            if (wrap && wrap.getAttribute && wrap.getAttribute('data-summary-wrapper') === 'true') {
                wrap.style.visibility = 'hidden';
            } else {
                existingSummary.style.visibility = 'hidden';
            }
        }
        return;
    }


    // Calculate brace position
    var braceWidth = 25;
    var padding = 8;
    var height = maxY - minY;
    var braceTipY = (minY + maxY) / 2; // Vertical center of brace tip

    // Check if summary element exists, if not create it
    var nodesContainer = getJsMindNodesEl() || container.querySelector('jmnodes');
    var summaryElement = document.querySelector('jmnode[nodeid="' + braceData.summaryNodeId + '"]');

    if (!summaryElement && nodesContainer) {
        summaryElement = document.createElement('jmnode');
        summaryElement.setAttribute('nodeid', braceData.summaryNodeId);
        summaryElement.innerHTML = braceData.summaryTopic || 'Summary';
        summaryElement.setAttribute('data-is-summary', 'true');
        summaryElement.setAttribute('data-brace-color', braceData.color || braceColor);
        // Override default jmnode absolute positioning so wrapper can size to content.
        summaryElement.style.position = 'relative';
        summaryElement.style.pointerEvents = 'auto';

        nodesContainer.appendChild(summaryElement);
        ensureSummaryWrapper(summaryElement, nodesContainer);

        // Setup interaction
        setupSummaryNodeInteraction(summaryElement, braceData);
    }

    // Calculate summary node position in map space. The wrapper handles centering without relying on measurements.
    var spacing = 50;
    var summaryAnchorX = (braceData.direction === 1)
        ? (outerX + braceWidth + spacing)
        : (outerX - braceWidth - spacing);

    // Update stored position
    braceData.summaryX = summaryAnchorX;
    braceData.summaryY = braceTipY;

    // Update position of summary element
    if (summaryElement) {
        var wrap = ensureSummaryWrapper(summaryElement, nodesContainer);
        if (wrap) {
            wrap.style.left = summaryAnchorX + 'px';
            wrap.style.top = braceTipY + 'px';
            wrap.style.transform = (braceData.direction === 1)
                ? 'translate(0, -50%)'
                : 'translate(-100%, -50%)';
            wrap.style.visibility = 'visible';
        } else {
            summaryElement.style.position = 'absolute';
            summaryElement.style.left = summaryAnchorX + 'px';
            summaryElement.style.top = braceTipY + 'px';
            summaryElement.style.visibility = 'visible';
        }
    }

    // For line routing we connect to the wrapper anchor:
    // - direction=1 (right): anchor is the summary's left edge
    // - direction!=1 (left): anchor is the summary's right edge
    var summaryLeft = summaryAnchorX;
    var summaryRight = summaryAnchorX;

    // Create SVG for brace
    var svg = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
    svg.classList.add('summary-brace');
    svg.setAttribute('data-brace-id', braceData.id);

    // Calculate SVG position and size
    var svgLeft, svgWidth;
    if (braceData.direction === 1) { // right side
        svgLeft = outerX + padding;
        svgWidth = Math.max(braceWidth + 20, summaryLeft - svgLeft + 10);
    } else { // left side
        svgLeft = Math.min(summaryRight - 10, outerX - braceWidth - padding - 20);
        svgWidth = outerX - padding - svgLeft;
    }

    svg.style.cssText = 'position:absolute; pointer-events:none; z-index:1; overflow:visible;';
    svg.style.left = svgLeft + 'px';
    svg.style.top = (minY - 5) + 'px';
    svg.style.width = Math.max(svgWidth, 50) + 'px';
    svg.style.height = (height + 10) + 'px';

    // Draw curly brace path
    var path = document.createElementNS('http://www.w3.org/2000/svg', 'path');
    var localMidY = (height + 10) / 2;
    var curveRadius = Math.min(15, height / 4);

    var d;
    if (braceData.direction === 1) { // right side - opening brace {
        d = 'M 5 5' +
            ' Q ' + (5 + curveRadius) + ' 5, ' + (5 + curveRadius) + ' ' + (5 + curveRadius) +
            ' L ' + (5 + curveRadius) + ' ' + (localMidY - curveRadius) +
            ' Q ' + (5 + curveRadius) + ' ' + localMidY + ', ' + (5 + curveRadius * 2) + ' ' + localMidY +
            ' Q ' + (5 + curveRadius) + ' ' + localMidY + ', ' + (5 + curveRadius) + ' ' + (localMidY + curveRadius) +
            ' L ' + (5 + curveRadius) + ' ' + (height + 5 - curveRadius) +
            ' Q ' + (5 + curveRadius) + ' ' + (height + 5) + ', 5 ' + (height + 5);
    } else { // left side - closing brace }
        var braceX = Math.max(svgWidth, 50) - 5;
        d = 'M ' + braceX + ' 5' +
            ' Q ' + (braceX - curveRadius) + ' 5, ' + (braceX - curveRadius) + ' ' + (5 + curveRadius) +
            ' L ' + (braceX - curveRadius) + ' ' + (localMidY - curveRadius) +
            ' Q ' + (braceX - curveRadius) + ' ' + localMidY + ', ' + (braceX - curveRadius * 2) + ' ' + localMidY +
            ' Q ' + (braceX - curveRadius) + ' ' + localMidY + ', ' + (braceX - curveRadius) + ' ' + (localMidY + curveRadius) +
            ' L ' + (braceX - curveRadius) + ' ' + (height + 5 - curveRadius) +
            ' Q ' + (braceX - curveRadius) + ' ' + (height + 5) + ', ' + braceX + ' ' + (height + 5);
    }

    path.setAttribute('d', d);
    path.setAttribute('stroke', braceData.color || braceColor);
    path.setAttribute('stroke-width', '3');
    path.setAttribute('fill', 'none');
    path.setAttribute('stroke-linecap', 'round');
    path.setAttribute('stroke-linejoin', 'round');

    svg.appendChild(path);

    // Draw line from brace tip to summary node
    var line = document.createElementNS('http://www.w3.org/2000/svg', 'path');
    var lineMidY = localMidY;
    var lineEndX, lineStartX;

    if (braceData.direction === 1) {
        lineStartX = 5 + curveRadius * 2;
        lineEndX = summaryLeft - svgLeft - 5;
    } else {
        lineStartX = Math.max(svgWidth, 50) - 5 - curveRadius * 2;
        lineEndX = summaryRight - svgLeft + 5;
    }

    // Keep line horizontal for natural connection (same Y as brace tip)
    var lineY = lineMidY;

    line.setAttribute('d', 'M ' + lineStartX + ' ' + lineY + ' L ' + lineEndX + ' ' + lineY);
    line.setAttribute('stroke', braceData.color || braceColor);
    line.setAttribute('stroke-width', '2');
    line.setAttribute('fill', 'none');

    svg.appendChild(line);


    summaryLayer.appendChild(svg);
}


// Delete a summary and its brace
function deleteSummaryNode(nodeId) {
    // Find and remove the brace
    var braceIndex = -1;
    for (var i = 0; i < summaryBraces.length; i++) {
        if (summaryBraces[i].summaryNodeId === nodeId) {
            braceIndex = i;
            break;
        }
    }

    if (braceIndex > -1) {
        summaryBraces.splice(braceIndex, 1);
    }

    // Remove the floating summary node element
    var summaryElement = document.querySelector('jmnode[nodeid="' + nodeId + '"]');
    removeSummaryElementAndWrapper(summaryElement);

    // Redraw
    renderSummaryBraces();
    saveHistory();
    scheduleAutoSave();
}


// Show context menu for multi-selection
function showMultiSelectionContextMenu(x, y) {
    var existing = document.getElementById('custom-context-menu');
    if (existing) existing.remove();

    var menu = document.createElement('div');
    menu.id = 'custom-context-menu';
    menu.style.cssText = 'position:fixed; left:' + x + 'px; top:' + y + 'px; background:white; border:1px solid #ccc; box-shadow:2px 2px 5px rgba(0,0,0,0.2); z-index:10000; padding:5px 0; border-radius:4px; min-width:180px;';

    function createMenuItem(text, onClick, disabled) {
        var item = document.createElement('div');
        item.innerText = text;
        item.style.cssText = 'padding:8px 15px; cursor:' + (disabled ? 'default' : 'pointer') + '; font-family:sans-serif; font-size:14px; color:' + (disabled ? '#999' : '#333') + ';';
        if (!disabled) {
            item.onmouseover = function () { this.style.background = '#f0f0f0'; };
            item.onmouseout = function () { this.style.background = 'white'; };
            item.onclick = function () {
                onClick();
                menu.remove();
            };
        }
        return item;
    }

    var validation = validateSummarySelection();

    if (validation.valid) {
        menu.appendChild(createMenuItem('Create Summary', function () {
            createSummary();
        }));
    } else {
        menu.appendChild(createMenuItem(validation.reason, null, true));
    }

    // Separator
    var sep = document.createElement('div');
    sep.style.cssText = 'height:1px; background:#eee; margin:4px 0;';
    menu.appendChild(sep);

    // Boundary option
    var boundaryValidation = validateBoundarySelection();
    if (boundaryValidation.valid) {
        menu.appendChild(createMenuItem('Create Boundary', function () {
            createBoundary();
        }));
    } else {
        menu.appendChild(createMenuItem('Boundary: ' + boundaryValidation.reason, null, true));
    }

    // Separator
    var sep2 = document.createElement('div');
    sep2.style.cssText = 'height:1px; background:#eee; margin:4px 0;';
    menu.appendChild(sep2);

    menu.appendChild(createMenuItem('Clear Selection', function () {
        clearSelection();
    }));

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

// ========== END SUMMARY BRACE FEATURE ==========

// ========== BOUNDARY FEATURE ==========

