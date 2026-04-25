function showToast(message) {
    var status = document.getElementById('auto-save-status');
    if (status) {
        status.textContent = message;
        status.style.opacity = '1';
        setTimeout(function () {
            status.style.opacity = '0';
        }, 1500);
    }
}

function setupMultiSelection() {
    var container = document.getElementById('jsmind_container');

    container.addEventListener('mousedown', function (e) {
        if (e.button === 2 && e.ctrlKey) {
            isSelecting = true;
            selectionStart = { x: e.clientX, y: e.clientY };

            if (!selectionBox) {
                selectionBox = document.createElement('div');
                selectionBox.style.cssText = 'position:fixed; border:2px dashed #4dc4ff; background:rgba(77,196,255,0.1); pointer-events:none; z-index:9999;';
                document.body.appendChild(selectionBox);
            }

            selectionBox.style.left = e.clientX + 'px';
            selectionBox.style.top = e.clientY + 'px';
            selectionBox.style.width = '0px';
            selectionBox.style.height = '0px';
            selectionBox.style.display = 'block';

            e.preventDefault();
        }
    });

    document.addEventListener('mousemove', function (e) {
        if (isSelecting && selectionBox) {
            var width = Math.abs(e.clientX - selectionStart.x);
            var height = Math.abs(e.clientY - selectionStart.y);
            var left = Math.min(e.clientX, selectionStart.x);
            var top = Math.min(e.clientY, selectionStart.y);

            selectionBox.style.left = left + 'px';
            selectionBox.style.top = top + 'px';
            selectionBox.style.width = width + 'px';
            selectionBox.style.height = height + 'px';
        }
    });

    document.addEventListener('mouseup', function (e) {
        if (isSelecting) {
            isSelecting = false;
            if (selectionBox) {
                selectionBox.style.display = 'none';
            }

            selectNodesInBox(selectionStart.x, selectionStart.y, e.clientX, e.clientY);
        }
    });
}

function selectNodesInBox(x1, y1, x2, y2) {
    clearSelection();
    var nodes = document.querySelectorAll('jmnode');
    var minX = Math.min(x1, x2);
    var maxX = Math.max(x1, x2);
    var minY = Math.min(y1, y2);
    var maxY = Math.max(y1, y2);

    nodes.forEach(function (node) {
        var rect = node.getBoundingClientRect();
        if (rect.left >= minX && rect.right <= maxX &&
            rect.top >= minY && rect.bottom <= maxY) {
            node.classList.add('selected-multi');
            selectedNodes.push(node);
        }
    });
}

function clearSelection() {
    selectedNodes.forEach(function (node) {
        node.classList.remove('selected-multi');
    });
    selectedNodes = [];

    // Also deselect any selected boundary
    if (selectedBoundary) {
        var selectedBoundaryElem = document.querySelector('.boundary-box.selected');
        if (selectedBoundaryElem) {
            selectedBoundaryElem.classList.remove('selected');
        }
        selectedBoundary = null;
    }
}

// ========== SUMMARY BRACE FEATURE ==========

// Setup Shift+Click multi-selection for nodes
function setupShiftClickSelection() {
    var container = document.getElementById('jsmind_container');
    if (!container) return;

    // Use mousedown for more reliable capture before jsMind handles it
    container.addEventListener('mousedown', function (e) {
        // Only handle shift+click on nodes
        if (!e.shiftKey) return;
        if (isEditing) return;
        if (e.button !== 0) return; // Only left click

        var nodeElement = e.target.closest('jmnode');
        if (!nodeElement) return;

        // Skip floating nodes
        var nodeId = nodeElement.getAttribute('nodeid');
        if (nodeId && nodeId.startsWith('floating_')) return;

        // Skip summary nodes for selection
        if (nodeId && nodeId.startsWith('summary_')) return;

        e.preventDefault();
        e.stopPropagation();
        e.stopImmediatePropagation();

        // Add to multi-selection
        addToMultiSelection(nodeElement);
    }, true);

    // Also handle click to ensure selection works
    container.addEventListener('click', function (e) {
        if (!e.shiftKey) return;
        if (isEditing) return;

        var nodeElement = e.target.closest('jmnode');
        if (!nodeElement) return;

        var nodeId = nodeElement.getAttribute('nodeid');
        if (nodeId && (nodeId.startsWith('floating_') || nodeId.startsWith('summary_'))) return;

        // Prevent default behavior
        e.preventDefault();
        e.stopPropagation();
    }, true);
}

// Add node to multi-selection
function addToMultiSelection(nodeElement) {
    if (!nodeElement) return;

    // Toggle selection
    if (nodeElement.classList.contains('selected-multi')) {
        // Remove from selection
        nodeElement.classList.remove('selected-multi');
        var idx = selectedNodes.indexOf(nodeElement);
        if (idx > -1) selectedNodes.splice(idx, 1);
    } else {
        // Add to selection
        nodeElement.classList.add('selected-multi');
        if (selectedNodes.indexOf(nodeElement) === -1) {
            selectedNodes.push(nodeElement);
        }
    }

    console.log('Multi-selection count:', selectedNodes.length);
}

// Check if selected nodes are valid for summary (siblings only, no consecutive requirement)
