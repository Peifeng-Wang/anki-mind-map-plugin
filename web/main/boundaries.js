function validateBoundarySelection() {
    if (MM.state.selectedNodes.length === 0) {
        return { valid: false, reason: 'Select at least 1 node' };
    }

    // Get jsMind nodes and check validity
    var nodes = [];
    var parentId = null;

    for (var i = 0; i < MM.state.selectedNodes.length; i++) {
        var nodeId = MM.state.selectedNodes[i].getAttribute('nodeid');
        var node = MM.state.jm.get_node(nodeId);

        if (!node) return { valid: false, reason: 'Invalid node' };
        if (node.isroot) return { valid: false, reason: 'Cannot include root' };

        // Check if node is a summary node
        if (node.data && node.data.isSummaryNode) {
            return { valid: false, reason: 'Cannot include summary nodes' };
        }

        // For multiple nodes, check they share same parent
        if (MM.state.selectedNodes.length > 1) {
            if (parentId === null) {
                parentId = node.parent;
            } else if (node.parent !== parentId) {
                return { valid: false, reason: 'Nodes must be siblings' };
            }
        }

        nodes.push(node);
    }

    return {
        valid: true,
        nodes: nodes
    };
}

// Check if there is already a special boundary in the map
function hasSpecialBoundary() {
    for (var i = 0; i < MM.state.boundaries.length; i++) {
        if (MM.state.boundaries[i].isSpecial) {
            return true;
        }
    }
    return false;
}

// Create a boundary for selected nodes
function createBoundary() {
    if (!MM.state.jm) return;
    if (MM.state.jm && !MM.state.jm.get_editable()) {
        showToast('Read-only mode');
        return;
    }

    var validation = validateBoundarySelection();
    if (!validation.valid) {
        showToast(validation.reason);
        return;
    }

    var nodes = validation.nodes;
    var nodeIds = nodes.map(function (n) { return n.id; });

    // Create boundary data
    var boundaryData = {
        id: MM.state.boundaryIdPrefix + Date.now(),
        nodeIds: nodeIds,
        color: MM.state.boundaryColor,
        isSpecial: false  // Default not special
    };
    MM.state.boundaries.push(boundaryData);

    // Clear selection
    clearSelection();

    // Render boundaries
    setTimeout(function () {
        renderBoundaries();
    }, 50);

    // Save
    saveHistory();
    scheduleAutoSave();

    showToast('Boundary created');
}

// Toggle special status of a boundary
function toggleBoundarySpecial(boundaryData) {
    if (!boundaryData) return;
    
    // If setting as special, check if there's already a special boundary
    if (!boundaryData.isSpecial) {
        // Unset any existing special boundary
        for (var i = 0; i < MM.state.boundaries.length; i++) {
            if (MM.state.boundaries[i].isSpecial && MM.state.boundaries[i].id !== boundaryData.id) {
                MM.state.boundaries[i].isSpecial = false;
                MM.state.boundaries[i].color = MM.state.boundaryColor; // Reset to default color
            }
        }
    }
    
    // Toggle special status
    boundaryData.isSpecial = !boundaryData.isSpecial;
    
    // Update color based on special status
    if (boundaryData.isSpecial) {
        // Set to red-blue pattern color
        boundaryData.color = 'url(#red-blue-stripe)';
    } else {
        // Reset to default color
        boundaryData.color = MM.state.boundaryColor;
    }
    
    // Re-render boundaries
    renderBoundaries();
    saveHistory();
    
    // Save immediately to ensure special boundary state is persisted
    autoSave();
    
    showToast(boundaryData.isSpecial ? 'Boundary set as link receiver' : 'Boundary unset as link receiver');
}

// Render all boundaries
function renderBoundaries() {
    // Remove existing boundary SVGs and definitions
    var existingBoundaries = document.querySelectorAll('.boundary-box');
    existingBoundaries.forEach(function (el) { el.remove(); });
    
    var existingDefs = document.querySelector('#boundary-patterns');
    if (existingDefs) existingDefs.remove();

    if (!MM.state.jm || !MM.state.jm.view) return;

    var container = document.getElementById('jsmind_container');
    if (!container) return;

    var panel = getJsMindPanelEl() || container.querySelector('.jsmind-inner');
    if (!panel) return;

    var boundaryLayer = getOrCreateOverlayLayer(panel, 'boundary-overlay-layer', 5, 'auto', true);
    if (!boundaryLayer) return;
    
    // Create SVG definitions for patterns (only once)
    var svgDefs = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
    svgDefs.id = 'boundary-patterns';
    svgDefs.style.cssText = 'position: absolute; width: 0; height: 0;';
    
    var defs = document.createElementNS('http://www.w3.org/2000/svg', 'defs');
    
    // Red-blue stripe pattern
    var pattern = document.createElementNS('http://www.w3.org/2000/svg', 'pattern');
    pattern.id = 'red-blue-stripe';
    pattern.setAttribute('patternUnits', 'userSpaceOnUse');
    pattern.setAttribute('width', '10');
    pattern.setAttribute('height', '10');
    pattern.setAttribute('patternTransform', 'rotate(45)');
    
    // Red stripe
    var redRect = document.createElementNS('http://www.w3.org/2000/svg', 'rect');
    redRect.setAttribute('width', '5');
    redRect.setAttribute('height', '10');
    redRect.setAttribute('fill', '#ef4444'); // Red
    
    // Blue stripe
    var blueRect = document.createElementNS('http://www.w3.org/2000/svg', 'rect');
    blueRect.setAttribute('x', '5');
    blueRect.setAttribute('width', '5');
    blueRect.setAttribute('height', '10');
    blueRect.setAttribute('fill', '#3b82f6'); // Blue
    
    pattern.appendChild(redRect);
    pattern.appendChild(blueRect);
    defs.appendChild(pattern);
    svgDefs.appendChild(defs);
    panel.appendChild(svgDefs);

    // Filter out invalid boundaries
    MM.state.boundaries = MM.state.boundaries.filter(function (boundaryData) {
        var validNodes = boundaryData.nodeIds.filter(function (id) {
            return MM.state.jm.get_node(id) !== null;
        });
        if (validNodes.length === 0) {
            return false;
        }
        boundaryData.nodeIds = validNodes;
        return true;
    });

    // Sort boundaries by size (smaller/inner first)
    var sortedBoundaries = MM.state.boundaries.slice().sort(function (a, b) {
        return a.nodeIds.length - b.nodeIds.length;
    });

    // Render each boundary
    sortedBoundaries.forEach(function (boundaryData) {
        renderSingleBoundary(boundaryData, panel, container, boundaryLayer);
    });
}

// Calculate bounding box for nodes and all descendants
function calculateBoundaryBBox(nodeIds) {
    var minX = Infinity, maxX = -Infinity;
    var minY = Infinity, maxY = -Infinity;
    var validCount = 0;

    // Recursive function to get bounds of node and all children
    function getNodeBounds(node) {
        if (!node || !isMindNodeVisible(node)) return;
        var box = getNodeBoxFromView(node);
        if (!box) return;

        if (box.left < minX) minX = box.left;
        if (box.right > maxX) maxX = box.right;
        if (box.top < minY) minY = box.top;
        if (box.bottom > maxY) maxY = box.bottom;
        validCount++;

        // Recursively check children
        if (node.expanded === false) return;
        if (node.children && node.children.length > 0) {
            for (var i = 0; i < node.children.length; i++) {
                getNodeBounds(node.children[i]);
            }
        }
    }

    // Process each node in the boundary
    for (var i = 0; i < nodeIds.length; i++) {
        var node = MM.state.jm.get_node(nodeIds[i]);
        getNodeBounds(node);
    }

    // Check for summary braces that might be attached to these nodes
    MM.state.summaryBraces.forEach(function (braceData) {
        // Check if any summarized nodes are in our boundary
        var hasOverlap = braceData.summarizedNodeIds.some(function (id) {
            return nodeIds.indexOf(id) !== -1;
        });

        if (hasOverlap) {
            // Include the summary node position
            var summaryElem = document.querySelector('jmnode[nodeid="' + braceData.summaryNodeId + '"]');
            if (!isVisibleForOverlay(summaryElem)) return;
            var wrap = summaryElem.parentElement;
            if (wrap && wrap.getAttribute && wrap.getAttribute('data-summary-wrapper') === 'true' && wrap.style.visibility === 'hidden') {
                return;
            }
            var sBox = getSummaryBoxFromBraceData(braceData, summaryElem);
            if (sBox && isFinite(sBox.left) && isFinite(sBox.right) && isFinite(sBox.top) && isFinite(sBox.bottom)) {
                if (sBox.left < minX) minX = sBox.left;
                if (sBox.right > maxX) maxX = sBox.right;
                if (sBox.top < minY) minY = sBox.top;
                if (sBox.bottom > maxY) maxY = sBox.bottom;
            }
        }
    });

    if (validCount === 0) return null;

    return { minX: minX, maxX: maxX, minY: minY, maxY: maxY };
}

// Render a single boundary
function renderSingleBoundary(boundaryData, panel, container, boundaryLayer) {
    var bbox = calculateBoundaryBBox(boundaryData.nodeIds);
    if (!bbox) return;

    // Add padding around the boundary
    var padding = 12;
    var minX = bbox.minX - padding;
    var maxX = bbox.maxX + padding;
    var minY = bbox.minY - padding;
    var maxY = bbox.maxY + padding;

    var width = maxX - minX;
    var height = maxY - minY;

    // Create SVG for boundary
    var svg = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
    svg.classList.add('boundary-box');
    svg.setAttribute('data-boundary-id', boundaryData.id);

    svg.style.cssText = 'position:absolute; overflow:visible; z-index:5;';
    svg.style.left = minX + 'px';
    svg.style.top = minY + 'px';
    svg.style.width = width + 'px';
    svg.style.height = height + 'px';

    // Two-layer rect:
    // - fill rect is non-interactive so nodes inside the boundary remain clickable
    // - stroke rect is interactive so users can still select the boundary via its outline
    var fillRect = document.createElementNS('http://www.w3.org/2000/svg', 'rect');
    fillRect.classList.add('boundary-fill');
    fillRect.setAttribute('x', '1');
    fillRect.setAttribute('y', '1');
    fillRect.setAttribute('width', Math.max(0, width - 2) + '');
    fillRect.setAttribute('height', Math.max(0, height - 2) + '');
    fillRect.setAttribute('rx', '8');
    fillRect.setAttribute('ry', '8');

    // Invisible hit target to make selecting the boundary easier without blocking node clicks.
    // Kept as a stroke-only rect so only the outline area is clickable.
    var hitRect = document.createElementNS('http://www.w3.org/2000/svg', 'rect');
    hitRect.classList.add('boundary-hit');
    hitRect.setAttribute('x', '1');
    hitRect.setAttribute('y', '1');
    hitRect.setAttribute('width', Math.max(0, width - 2) + '');
    hitRect.setAttribute('height', Math.max(0, height - 2) + '');
    hitRect.setAttribute('rx', '8');
    hitRect.setAttribute('ry', '8');
    hitRect.setAttribute('fill', 'none');
    hitRect.setAttribute('stroke', 'transparent');
    hitRect.setAttribute('stroke-width', '14');

    var strokeRect = document.createElementNS('http://www.w3.org/2000/svg', 'rect');
    strokeRect.classList.add('boundary-stroke');
    strokeRect.setAttribute('x', '1');
    strokeRect.setAttribute('y', '1');
    strokeRect.setAttribute('width', Math.max(0, width - 2) + '');
    strokeRect.setAttribute('height', Math.max(0, height - 2) + '');
    strokeRect.setAttribute('rx', '8');
    strokeRect.setAttribute('ry', '8');
    strokeRect.setAttribute('fill', 'none');

    // Set color based on special status
    if (boundaryData.isSpecial && boundaryData.color === 'url(#red-blue-stripe)') {
        strokeRect.setAttribute('stroke', 'url(#red-blue-stripe)');
        strokeRect.setAttribute('stroke-width', '3');
        strokeRect.setAttribute('stroke-dasharray', '6,3');
        fillRect.setAttribute('fill', 'rgba(239, 68, 68, 0.1)'); // Light red background
    } else {
        strokeRect.setAttribute('stroke', boundaryData.color || MM.state.boundaryColor);
        strokeRect.setAttribute('stroke-width', '2.5');
        strokeRect.setAttribute('stroke-dasharray', '8,4');
        fillRect.setAttribute('fill', 'rgba(239, 68, 68, 0.05)');
    }

    svg.appendChild(fillRect);
    svg.appendChild(hitRect);
    svg.appendChild(strokeRect);

    // Add click handler for selection on the boundary outline only
    hitRect.addEventListener('click', function (e) {
        e.stopPropagation();
        selectBoundary(boundaryData, svg);
    });

    // Add context menu handler
    hitRect.addEventListener('contextmenu', function (e) {
        e.preventDefault();
        e.stopPropagation();
        selectBoundary(boundaryData, svg);
        showBoundaryContextMenu(e.clientX, e.clientY, boundaryData);
    });

    boundaryLayer.appendChild(svg);
}

// Select a boundary
function selectBoundary(boundaryData, svgElement) {
    // Deselect previous boundary
    var previousSelected = document.querySelector('.boundary-box.selected');
    if (previousSelected) {
        previousSelected.classList.remove('selected');
    }

    // Select this boundary
    MM.state.selectedBoundary = boundaryData;
    svgElement.classList.add('selected');

    // Deselect jsMind nodes
    if (MM.state.jm) MM.state.jm.select_clear();
    clearSelection();
}

// Delete a boundary
function deleteBoundary(boundaryData) {
    var idx = MM.state.boundaries.indexOf(boundaryData);
    if (idx > -1) {
        MM.state.boundaries.splice(idx, 1);
    }

    MM.state.selectedBoundary = null;
    renderBoundaries();
    saveHistory();
    scheduleAutoSave();
    showToast('Boundary deleted');
}

// Show context menu for boundary
function showBoundaryContextMenu(x, y, boundaryData) {
    var existing = document.getElementById('custom-context-menu');
    if (existing) existing.remove();

    var menu = document.createElement('div');
    menu.id = 'custom-context-menu';
    menu.style.cssText = 'position:fixed; left:' + x + 'px; top:' + y + 'px; background:white; border:1px solid #ccc; box-shadow:2px 2px 5px rgba(0,0,0,0.2); z-index:10000; padding:5px 0; border-radius:4px; min-width:180px;';

    function createMenuItem(text, onClick) {
        var item = document.createElement('div');
        item.innerText = text;
        item.style.cssText = 'padding:8px 15px; cursor:pointer; font-family:sans-serif; font-size:14px; color:#333;';
        item.onmouseover = function () { this.style.background = '#f0f0f0'; };
        item.onmouseout = function () { this.style.background = 'white'; };
        item.onclick = function () {
            onClick();
            menu.remove();
        };
        return item;
    }

    // Add special boundary toggle option
    if (boundaryData.isSpecial) {
        menu.appendChild(createMenuItem('Unset as Link Receiver', function () {
            toggleBoundarySpecial(boundaryData);
        }));
    } else {
        menu.appendChild(createMenuItem('Set as Link Receiver', function () {
            toggleBoundarySpecial(boundaryData);
        }));
    }
    
    menu.appendChild(createMenuItem('Delete Boundary', function () {
        deleteBoundary(boundaryData);
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

// ========== END BOUNDARY FEATURE ==========
