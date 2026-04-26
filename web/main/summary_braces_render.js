// Summary brace rendering: marking summary nodes, drawing the SVG braces,
// and re-anchoring the floating summary node to the current layout.

// Mark summary nodes with data attribute for CSS styling
function markSummaryNodes() {
    if (!MM.state.jm) return;

    var allNodes = document.querySelectorAll('jmnode');
    allNodes.forEach(function (nodeElement) {
        var nodeId = nodeElement.getAttribute('nodeid');
        if (!nodeId) return;

        var node = MM.state.jm.get_node(nodeId);
        if (!node) return;

        if (node.data && node.data.isSummaryNode) {
            nodeElement.setAttribute('data-is-summary', 'true');
            // Apply brace color to node
            var color = node.data.braceColor || MM.state.braceColor;
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

    if (!MM.state.jm || !MM.state.jm.view) return;

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
    MM.state.summaryBraces = MM.state.summaryBraces.filter(function (braceData) {
        var validNodes = braceData.summarizedNodeIds.filter(function (id) {
            return MM.state.jm.get_node(id) !== null;
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
    MM.state.summaryBraces.forEach(function (braceData) {
        if (braceData.summarizedNodeIds.length === 0) return;

        // Get the parent of summarized nodes
        var firstNodeId = braceData.summarizedNodeIds[0];
        var firstNode = MM.state.jm.get_node(firstNodeId);
        if (!firstNode || !firstNode.parent) return;

        var parentNode = firstNode.parent;
        var siblings = parentNode.children || [];

        // Get vertical range of current summarized nodes (map coordinate space; independent of zoom).
        var minY = Infinity, maxY = -Infinity;

        braceData.summarizedNodeIds.forEach(function (nodeId) {
            var node = MM.state.jm.get_node(nodeId);
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

    MM.state.summaryBraces.forEach(function (braceData) {
        renderSingleBrace(braceData, panel, container, summaryLayer);
    });
}

// Render a single brace
function renderSingleBrace(braceData, panel, container, summaryLayer) {
    // Get positions of summarized nodes
    var minY = Infinity, maxY = -Infinity;
    var outerX = null;
    var validNodeCount = 0;

    for (var i = 0; i < braceData.summarizedNodeIds.length; i++) {
        var nodeId = braceData.summarizedNodeIds[i];
        var node = MM.state.jm.get_node(nodeId);
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
        var nodeOuterX = findOuterXFromNode(node, braceData.direction);
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
        summaryElement.setAttribute('data-brace-color', braceData.color || MM.state.braceColor);
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
    path.setAttribute('stroke', braceData.color || MM.state.braceColor);
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
    line.setAttribute('stroke', braceData.color || MM.state.braceColor);
    line.setAttribute('stroke-width', '2');
    line.setAttribute('fill', 'none');

    svg.appendChild(line);


    summaryLayer.appendChild(svg);
}
