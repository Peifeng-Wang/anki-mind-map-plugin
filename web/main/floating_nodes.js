function loadFloatingNode(nodeData) {
    if (!jm) return;

    var container = document.getElementById('jsmind_container');
    if (!container) return;

    var nodesContainer = getJsMindNodesEl();
    if (!nodesContainer) return;

    // Create node element
    var nodeElement = document.createElement('jmnode');
    nodeElement.setAttribute('nodeid', nodeData.id);
    nodeElement.innerHTML = nodeData.topic || ''; // Use saved topic or empty
    nodeElement.style.position = 'absolute';
    nodeElement.style.left = nodeData.x + 'px';
    nodeElement.style.top = nodeData.y + 'px';
    nodeElement.style.padding = '10px 15px';
    nodeElement.style.backgroundColor = '#fff';
    nodeElement.style.border = '3px solid #000'; // Black border for floating nodes
    nodeElement.style.borderRadius = '5px';
    nodeElement.style.cursor = 'move';
    nodeElement.style.zIndex = '2';
    nodeElement.style.boxShadow = '0 2px 8px rgba(0,0,0,0.2)';
    nodeElement.style.minWidth = '80px';
    nodeElement.style.textAlign = 'center';
    nodeElement.style.fontSize = '14px';
    nodeElement.style.color = '#000';
    nodeElement.style.display = 'inline-block';
    nodeElement.style.whiteSpace = 'pre-wrap';
    nodeElement.style.wordWrap = 'break-word';

    // Add to container
    nodesContainer.appendChild(nodeElement);

    // Store floating node data
    var floatingNode = {
        id: nodeData.id,
        element: nodeElement,
        topic: nodeData.topic,
        x: nodeData.x,
        y: nodeData.y,
        children: [],
        isFloating: true
    };
    floatingNodes.push(floatingNode);

    // Setup drag and edit functionality
    setupFloatingNodeDrag(floatingNode);
    setupFloatingNodeEdit(floatingNode);
}

// Setup floating nodes functionality
function setupFloatingNodes() {
    var container = document.getElementById('jsmind_container');
    if (!container) return;

    // Double-click on empty space to create floating node
    container.addEventListener('dblclick', function (e) {
        if (jm && !jm.get_editable()) return;
        if (typeof enableFloatingNodesFromPython !== 'undefined' && !enableFloatingNodesFromPython) {
            return;
        }
        // Check if clicked on empty space (not on a node)
        var target = e.target;
        if (target.tagName && target.tagName.toLowerCase() === 'jmnode') {
            return; // Clicked on a node, ignore
        }

        // Create floating node at click position
        createFloatingNode(e.clientX, e.clientY);
        e.preventDefault();
        e.stopPropagation();
    });
}

// Create a floating node (independent node without parent)
function createFloatingNode(clientX, clientY) {
    if (!jm) return;

    var container = document.getElementById('jsmind_container');
    if (!container) return;

    var jview = jm.view;

    // Get the nodes container
    var nodesContainer = getJsMindNodesEl();
    if (!nodesContainer) return;

    // Calculate position relative to the scrolling panel
    // Try to get e_panel from view, or find it by class
    var e_panel = (jview && jview.e_panel) || getJsMindPanelEl() || container.querySelector('.jsmind-inner');

    if (!e_panel) {
        console.error("Could not find scrolling panel");
        return;
    }

    var panelRect = e_panel.getBoundingClientRect();
    var zoom = (jview && jview.actualZoom) || 1;

    // Convert client X/Y to canvas coordinates
    // Correct formula: (Relative Screen Pos / Zoom) + Scroll Offset
    var canvasX = (clientX - panelRect.left) / zoom + e_panel.scrollLeft;
    var canvasY = (clientY - panelRect.top) / zoom + e_panel.scrollTop;

    // Create node element
    var nodeId = floatingNodeIdPrefix + Date.now();
    var nodeElement = document.createElement('jmnode');
    nodeElement.setAttribute('nodeid', nodeId);
    nodeElement.innerHTML = ''; // Empty node
    nodeElement.style.position = 'absolute';
    nodeElement.style.padding = '10px 15px';
    nodeElement.style.backgroundColor = '#fff';
    nodeElement.style.border = '3px solid #000';
    nodeElement.style.borderRadius = '5px';
    nodeElement.style.cursor = 'move';
    nodeElement.style.zIndex = '2';
    nodeElement.style.boxShadow = '0 2px 8px rgba(0,0,0,0.2)';
    nodeElement.style.minWidth = '80px';
    nodeElement.style.textAlign = 'center';
    nodeElement.style.fontSize = '14px';
    nodeElement.style.color = '#000';
    nodeElement.style.display = 'inline-block';
    nodeElement.style.whiteSpace = 'pre-wrap';
    nodeElement.style.wordWrap = 'break-word';

    // Set initial position
    nodeElement.style.left = canvasX + 'px';
    nodeElement.style.top = canvasY + 'px';

    // Add to container
    nodesContainer.appendChild(nodeElement);

    // Store floating node data
    var floatingNode = {
        id: nodeId,
        element: nodeElement,
        topic: '',
        x: canvasX,
        y: canvasY,
        children: [],
        isFloating: true
    };
    floatingNodes.push(floatingNode);

    // Adjust position after rendering to center on click point
    setTimeout(function () {
        var actualWidth = nodeElement.offsetWidth;
        var actualHeight = nodeElement.offsetHeight;
        var centeredX = canvasX - actualWidth / 2;
        var centeredY = canvasY - actualHeight / 2;

        nodeElement.style.left = centeredX + 'px';
        nodeElement.style.top = centeredY + 'px';

        floatingNode.x = centeredX;
        floatingNode.y = centeredY;
    }, 0);

    // Setup drag and edit functionality
    setupFloatingNodeDrag(floatingNode);
    setupFloatingNodeEdit(floatingNode);

    // Select the new node
    selectFloatingNode(floatingNode);

    saveHistory();
    scheduleAutoSave();
}

// Setup drag functionality for floating node
function setupFloatingNodeDrag(floatingNode) {
    var element = floatingNode.element;
    var isDragging = false;
    var offsetX, offsetY;
    var mouseMoveHandler, mouseUpHandler;
    var originalTransition = '';

    element.addEventListener('mousedown', function (e) {
        if (jm && !jm.get_editable()) return;
        if (e.target !== element && e.target.parentElement !== element) return;
        if (isEditing) return; // Don't drag while editing

        isDragging = true;
        element.style.cursor = 'grabbing';

        // Disable transition during drag to prevent lag/delay
        originalTransition = element.style.transition;
        element.style.transition = 'none';

        e.preventDefault();
        e.stopPropagation();

        // Get view parameters
        var jview = jm.view;
        var zoom = (jview && jview.actualZoom) || 1;

        // For floating nodes, use style.left/top (actual position) not offsetLeft/Top
        var currentLeft = parseFloat(element.style.left) || 0;
        var currentTop = parseFloat(element.style.top) || 0;

        // Calculate offset exactly like jsMind does for regular nodes
        // offset = (clientX / zoom) - current position
        offsetX = e.clientX / zoom - currentLeft;
        offsetY = e.clientY / zoom - currentTop;

        var frameCount = 0; // For throttling attach check

        // Add event listeners for this drag session
        mouseMoveHandler = function (e) {
            if (!isDragging) return;

            // Get current zoom
            var currentZoom = (jview && jview.actualZoom) || 1;

            // Calculate position exactly like jsMind does for regular nodes
            // position = (clientX / zoom) - offset
            var px = e.clientX / currentZoom - offsetX;
            var py = e.clientY / currentZoom - offsetY;

            element.style.left = px + 'px';
            element.style.top = py + 'px';

            floatingNode.x = px;
            floatingNode.y = py;

            // Check attach less frequently for performance (every 5 frames)
            frameCount++;
            if (frameCount % 5 === 0) {
                checkAttachToNode(floatingNode);
            }

            e.preventDefault();
            e.stopPropagation();
        };

        mouseUpHandler = function (e) {
            if (!isDragging) return;

            isDragging = false;
            element.style.cursor = 'move';

            // Restore transition
            element.style.transition = originalTransition;

            // Try to attach to nearby node
            tryAttachToNode(floatingNode);

            saveHistory();
            scheduleAutoSave();

            // Remove event listeners
            document.removeEventListener('mousemove', mouseMoveHandler);
            document.removeEventListener('mouseup', mouseUpHandler);
        };

        document.addEventListener('mousemove', mouseMoveHandler);
        document.addEventListener('mouseup', mouseUpHandler);
    });
}


// Check if floating node is close to any jsMind node
function checkAttachToNode(floatingNode) {
    var element = floatingNode.element;
    var rect = element.getBoundingClientRect();
    var centerX = rect.left + rect.width / 2;
    var centerY = rect.top + rect.height / 2;

    var allJsNodes = document.querySelectorAll('jmnode:not([nodeid^="floating_"])');
    var closestNode = null;
    var minDistance = 100; // Threshold distance in pixels

    for (var i = 0; i < allJsNodes.length; i++) {
        var node = allJsNodes[i];
        var nodeRect = node.getBoundingClientRect();
        var nodeCenterX = nodeRect.left + nodeRect.width / 2;
        var nodeCenterY = nodeRect.top + nodeRect.height / 2;

        var distance = Math.sqrt(
            Math.pow(centerX - nodeCenterX, 2) +
            Math.pow(centerY - nodeCenterY, 2)
        );

        if (distance < minDistance) {
            minDistance = distance;
            closestNode = node;
        }
    }

    // Visual feedback when close to a node
    if (closestNode && minDistance < 80) {
        element.style.borderColor = '#4dc4ff';
        element.style.borderWidth = '3px';
        closestNode.style.boxShadow = '0 0 10px #4dc4ff';
    } else {
        element.style.borderColor = '#000';
        // Clear all node shadows
        allJsNodes.forEach(function (node) {
            node.style.boxShadow = '';
        });
    }
}

// Try to attach floating node to nearby jsMind node
function tryAttachToNode(floatingNode) {
    var element = floatingNode.element;
    var rect = element.getBoundingClientRect();
    var centerX = rect.left + rect.width / 2;
    var centerY = rect.top + rect.height / 2;

    var allJsNodes = document.querySelectorAll('jmnode:not([nodeid^="floating_"])');
    var closestNode = null;
    var minDistance = 80; // Threshold distance

    for (var i = 0; i < allJsNodes.length; i++) {
        var node = allJsNodes[i];
        var nodeRect = node.getBoundingClientRect();
        var nodeCenterX = nodeRect.left + nodeRect.width / 2;
        var nodeCenterY = nodeRect.top + nodeRect.height / 2;

        var distance = Math.sqrt(
            Math.pow(centerX - nodeCenterX, 2) +
            Math.pow(centerY - nodeCenterY, 2)
        );

        if (distance < minDistance) {
            minDistance = distance;
            closestNode = node;
        }
    }

    if (closestNode) {
        // Attach to the closest node
        var targetNodeId = closestNode.getAttribute('nodeid');
        var targetNode = jm.get_node(targetNodeId);

        if (targetNode) {
            // Add as child to jsMind
            var newNodeId = 'node_' + Date.now();
            jm.add_node(targetNode, newNodeId, floatingNode.topic);

            // Remove floating node
            removeFloatingNode(floatingNode);

            // Select the new node
            jm.select_node(newNodeId);

            // Clear shadows
            allJsNodes.forEach(function (node) {
                node.style.boxShadow = '';
            });

            setTimeout(renderMath, 300);
        }
    } else {
        // Reset border color
        element.style.borderColor = '#000';
    }
}

// Remove floating node
function removeFloatingNode(floatingNode) {
    if (floatingNode.element && floatingNode.element.parentNode) {
        floatingNode.element.parentNode.removeChild(floatingNode.element);
    }

    var index = floatingNodes.indexOf(floatingNode);
    if (index > -1) {
        floatingNodes.splice(index, 1);
    }
}

// Setup edit functionality for floating node
function setupFloatingNodeEdit(floatingNode) {
    var element = floatingNode.element;

    // Click to select
    element.addEventListener('click', function (e) {
        if (jm && !jm.get_editable()) return;
        selectFloatingNode(floatingNode);
        e.preventDefault();
        e.stopPropagation();
    });

    // Double-click to edit
    element.addEventListener('dblclick', function (e) {
        if (jm && !jm.get_editable()) return;
        enterFloatingNodeEditMode(floatingNode);
        e.preventDefault();
        e.stopPropagation();
    });

    // Keyboard events
    element.addEventListener('keydown', function (e) {
        if (isEditing) return;
        if (jm && !jm.get_editable()) return;

        console.log('Key pressed on floating node:', e.key, 'Node:', floatingNode.id);

        // Space: edit
        if (e.key === ' ') {
            e.preventDefault();
            e.stopPropagation();
            enterFloatingNodeEditMode(floatingNode);
        }
        // Tab: add child
        else if (e.key === 'Tab') {
            e.preventDefault();
            e.stopPropagation();
            addChildToFloatingNode(floatingNode);
        }
        // Delete/Backspace: remove
        else if (e.key === 'Delete' || e.key === 'Backspace') {
            e.preventDefault();
            e.stopPropagation();
            console.log('Deleting floating node:', floatingNode.id);
            removeFloatingNode(floatingNode);
            saveHistory();
            scheduleAutoSave();
        }
    });
}

// Currently selected floating node
var selectedFloatingNode = null;

// Select floating node
function selectFloatingNode(floatingNode) {
    // Deselect all floating nodes
    floatingNodes.forEach(function (node) {
        node.element.style.outline = 'none';
        node.isSelected = false;
    });

    // Select this one
    floatingNode.element.style.outline = '2px solid #4dc4ff';
    floatingNode.element.setAttribute('tabindex', '0');
    floatingNode.element.focus();
    floatingNode.isSelected = true;
    selectedFloatingNode = floatingNode;

    console.log('Selected floating node:', floatingNode.id);
}

// Enter edit mode for floating node
function enterFloatingNodeEditMode(floatingNode) {
    if (isEditing) return;

    isEditing = true;
    var element = floatingNode.element;
    var currentText = floatingNode.topic;

    // Create input
    var input = document.createElement('textarea');
    input.value = currentText;
    input.style.cssText = `
        width: 100%;
        height: 100%;
        border: none;
        outline: none;
        background: transparent;
        font-family: inherit;
        font-size: inherit;
        text-align: center;
        resize: none;
        padding: 0;
        margin: 0;
    `;

    element.innerHTML = '';
    element.appendChild(input);
    input.focus();
    input.select();

    // Save on Enter
    input.addEventListener('keydown', function (e) {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            exitFloatingNodeEditMode(floatingNode, input.value);
        } else if (e.key === 'Escape') {
            e.preventDefault();
            exitFloatingNodeEditMode(floatingNode, currentText);
        }
        e.stopPropagation();
    });

    // Save on blur
    input.addEventListener('blur', function () {
        exitFloatingNodeEditMode(floatingNode, input.value);
    });
}

// Exit edit mode for floating node
function exitFloatingNodeEditMode(floatingNode, newText) {
    if (!isEditing) return;

    isEditing = false;
    floatingNode.topic = newText || ''; // Keep empty if no text
    floatingNode.element.innerHTML = floatingNode.topic; // Use innerHTML to match jsMind

    saveHistory();
    scheduleAutoSave();
}

// Add floating node as child (when Tab is pressed on floating node)
function addChildToFloatingNode(floatingNode) {
    // Convert floating node to jsMind node first
    var root = jm.get_root();
    var newParentId = 'node_' + Date.now();
    jm.add_node(root, newParentId, floatingNode.topic);

    // Remove floating node
    removeFloatingNode(floatingNode);

    // Add child
    var childId = 'node_' + Date.now() + '_child';
    var parentNode = jm.get_node(newParentId);
    jm.add_node(parentNode, childId, 'New Child');
    jm.select_node(childId);

    setTimeout(renderMath, 300);
    saveHistory();
    scheduleAutoSave();
}
