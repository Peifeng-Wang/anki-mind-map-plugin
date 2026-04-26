// Summary brace DOM / geometry helpers.
// Selection validation, wrapper management, sizing, and the shared
// rightmost/leftmost-descendant finder used during creation and rendering.

function validateSummarySelection() {
    if (MM.state.selectedNodes.length < 2) {
        return { valid: false, reason: 'Select at least 2 nodes' };
    }

    // Get jsMind nodes and check they share same parent
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

        if (parentId === null) {
            parentId = node.parent;
        } else if (node.parent !== parentId) {
            return { valid: false, reason: 'Nodes must be siblings' };
        }

        nodes.push(node);
    }

    // All nodes are valid siblings - no consecutive check needed
    var parentNode = MM.state.jm.get_node(parentId);
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
    var z = (MM.state.jm && MM.state.jm.view && MM.state.jm.view.actualZoom) || 1;
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

// Find the rightmost (dir === 1) or leftmost X of a node and all its visible descendants.
// Used by createSummary (anchor placement) and renderSingleBrace (re-anchor on layout).
// Skips collapsed branches because their descendants are hidden.
function findOuterXFromNode(node, dir) {
    var extreme = null;
    if (!node || !isMindNodeVisible(node)) return extreme;
    var box = getNodeBoxFromView(node);
    if (!box) return extreme;

    if (dir === 1) {
        extreme = box.right;
    } else {
        extreme = box.left;
    }

    if (node.expanded === false) return extreme;

    if (node.children && node.children.length > 0) {
        for (var c = 0; c < node.children.length; c++) {
            var childExtreme = findOuterXFromNode(node.children[c], dir);
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
