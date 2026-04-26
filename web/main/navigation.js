function toggleArrowMode() {
    MM.state.arrowMode = !MM.state.arrowMode;
    if (MM.state.arrowMode) {
        document.getElementById('jsmind_container').style.cursor = 'crosshair';
    } else {
        document.getElementById('jsmind_container').style.cursor = 'default';
        MM.state.arrowStart = null;
    }
}

// Get all nodes at the same depth level and side, sorted by vertical position
function getNodesAtDepth(depth, filterSide) {
    var allNodes = [];
    var zoom = (MM.state.jm.view && MM.state.jm.view.actualZoom) || 1;

    function traverse(node, currentDepth) {
        if (currentDepth === depth) {
            var vd = node._data && node._data.view;
            if (vd && vd.element) {
                allNodes.push({
                    node: node,
                    top: vd.abs_y * zoom,
                    centerY: (vd.abs_y + vd.height / 2) * zoom,
                    centerX: (vd.abs_x + vd.width / 2) * zoom
                });
            }
        }

        if (node.children && currentDepth < depth) {
            for (var i = 0; i < node.children.length; i++) {
                var childId = (typeof node.children[i] === 'string') ? node.children[i] : node.children[i].id;
                var childNode = MM.state.jm.get_node(childId);
                if (childNode) {
                    traverse(childNode, currentDepth + 1);
                }
            }
        }
    }

    var root = MM.state.jm.get_root();
    traverse(root, 0);

    // Filter by side if specified
    if (filterSide !== null && filterSide !== undefined) {
        var rootVd = root._data && root._data.view;
        if (rootVd) {
            var rootCenterX = (rootVd.abs_x + rootVd.width / 2) * zoom;
            allNodes = allNodes.filter(function (item) {
                if (filterSide === 'left') {
                    return item.centerX < rootCenterX;
                } else if (filterSide === 'right') {
                    return item.centerX > rootCenterX;
                } else if (filterSide === 'center') {
                    return item.node.id === root.id;
                }
                return true;
            });
        }
    }

    // Sort by vertical position
    allNodes.sort(function (a, b) { return a.centerY - b.centerY; });
    return allNodes;
}

// Get node depth
function getNodeDepth(node) {
    var depth = 0;
    var current = node;
    while (current.parent) {
        depth++;
        current = MM.state.jm.get_node(current.parent);
        if (!current) break;
    }
    return depth;
}

// Get node side relative to root
function getNodeSide(node) {
    if (node.isroot) return 'center';

    var root = MM.state.jm.get_root();
    var rootVd = root._data && root._data.view;
    var nodeVd = node._data && node._data.view;

    if (!rootVd || !nodeVd) return null;

    var zoom = (MM.state.jm.view && MM.state.jm.view.actualZoom) || 1;
    var rootCenterX = (rootVd.abs_x + rootVd.width / 2) * zoom;
    var nodeCenterX = (nodeVd.abs_x + nodeVd.width / 2) * zoom;

    return nodeCenterX < rootCenterX ? 'left' : 'right';
}

// Get closest child by vertical distance
function getClosestChild(parentNode) {
    if (!parentNode.children || parentNode.children.length === 0) return null;

    var parentVd = parentNode._data && parentNode._data.view;
    if (!parentVd) return null;

    var zoom = (MM.state.jm.view && MM.state.jm.view.actualZoom) || 1;
    var parentCenterY = (parentVd.abs_y + parentVd.height / 2) * zoom;

    var closest = null;
    var minDist = Infinity;

    for (var i = 0; i < parentNode.children.length; i++) {
        var childId = (typeof parentNode.children[i] === 'string') ? parentNode.children[i] : parentNode.children[i].id;
        var childNode = MM.state.jm.get_node(childId);
        if (!childNode) continue;

        var childVd = childNode._data && childNode._data.view;
        if (childVd && childNode._data.view.element) {
            var childCenterY = (childVd.abs_y + childVd.height / 2) * zoom;
            var dist = Math.abs(childCenterY - parentCenterY);

            if (dist < minDist || (dist === minDist && closest === null)) {
                minDist = dist;
                closest = childNode;
            }
        }
    }

    return closest;
}

// Scroll node into view smoothly (XMind-style)
function scrollToNode(nodeId) {
    if (!MM.state.jm || !MM.state.jm.view) return;

    // Get jsMind's scroll container (the actual panel that scrolls)
    var container = MM.state.jm.view.e_panel || getJsMindPanelEl() || document.getElementById('jsmind_container');
    if (!container) return;

    // Cancel any in-progress animation to avoid "fighting" scroll positions when navigating quickly.
    MM.state.scrollToNodeAnimToken++;
    if (MM.state.scrollToNodeAnimRaf) {
        cancelAnimationFrame(MM.state.scrollToNodeAnimRaf);
        MM.state.scrollToNodeAnimRaf = null;
    }

    var targetScrollLeft = null;
    var targetScrollTop = null;

    // Prefer jsMind view coordinates (stable under CSS zoom) over DOM rects.
    var node = MM.state.jm.get_node(nodeId);
    if (node && node._data && node._data.view) {
        var vd = node._data.view;
        if (typeof vd.abs_x === 'number' && typeof vd.abs_y === 'number' &&
            typeof vd.width === 'number' && typeof vd.height === 'number') {
            var zoom = (MM.state.jm.view && MM.state.jm.view.actualZoom) || 1;
            var nodeCenterX = vd.abs_x + vd.width / 2;
            var nodeCenterY = vd.abs_y + vd.height / 2;
            targetScrollLeft = nodeCenterX * zoom - container.clientWidth / 2;
            targetScrollTop = nodeCenterY * zoom - container.clientHeight / 2;
        }
    }

    // Fallback for non-jsMind nodes (should be rare).
    if (targetScrollLeft === null || targetScrollTop === null) {
        var nodeElem = document.querySelector('jmnode[nodeid="' + nodeId + '"]');
        if (!nodeElem) return;

        var nodeRect = nodeElem.getBoundingClientRect();
        var containerRect = container.getBoundingClientRect();

        targetScrollLeft = container.scrollLeft + nodeRect.left - containerRect.left -
            (containerRect.width - nodeRect.width) / 2;
        targetScrollTop = container.scrollTop + nodeRect.top - containerRect.top -
            (containerRect.height - nodeRect.height) / 2;
    }

    // Clamp to scrollable range.
    var maxLeft = Math.max(0, container.scrollWidth - container.clientWidth);
    var maxTop = Math.max(0, container.scrollHeight - container.clientHeight);
    targetScrollLeft = Math.min(maxLeft, Math.max(0, targetScrollLeft));
    targetScrollTop = Math.min(maxTop, Math.max(0, targetScrollTop));

    var startScrollLeft = container.scrollLeft;
    var startScrollTop = container.scrollTop;
    var distanceLeft = targetScrollLeft - startScrollLeft;
    var distanceTop = targetScrollTop - startScrollTop;

    // Skip if already very close (within 5px)
    if (Math.abs(distanceLeft) < 5 && Math.abs(distanceTop) < 5) {
        return;
    }

    // Duration: 400ms for visible but smooth movement
    var duration = 400;
    var startTime = null;
    var token = MM.state.scrollToNodeAnimToken;

    // Easing function: ease-out-cubic for natural deceleration
    function easeOutCubic(t) {
        return 1 - Math.pow(1 - t, 3);
    }

    function animateScroll(currentTime) {
        if (token !== MM.state.scrollToNodeAnimToken) return;
        if (!startTime) startTime = currentTime;
        var elapsed = currentTime - startTime;
        var progress = Math.min(elapsed / duration, 1);
        var eased = easeOutCubic(progress);

        container.scrollLeft = startScrollLeft + distanceLeft * eased;
        container.scrollTop = startScrollTop + distanceTop * eased;

        if (progress < 1) {
            MM.state.scrollToNodeAnimRaf = requestAnimationFrame(animateScroll);
        } else {
            MM.state.scrollToNodeAnimRaf = null;
        }
    }

    MM.state.scrollToNodeAnimRaf = requestAnimationFrame(animateScroll);
}

function navigateUp() {
    if (!MM.state.jm) return;
    var selected = MM.state.jm.get_selected_node();
    if (!selected) return;

    var depth = getNodeDepth(selected);
    var side = getNodeSide(selected);
    var nodesAtDepth = getNodesAtDepth(depth, side);

    var currentIndex = -1;
    for (var i = 0; i < nodesAtDepth.length; i++) {
        if (nodesAtDepth[i].node.id === selected.id) {
            currentIndex = i;
            break;
        }
    }

    if (currentIndex > 0) {
        var targetId = nodesAtDepth[currentIndex - 1].node.id;
        MM.state.jm.select_node(targetId);
        scrollToNode(targetId);
    }
}

function navigateDown() {
    if (!MM.state.jm) return;
    var selected = MM.state.jm.get_selected_node();
    if (!selected) return;

    var depth = getNodeDepth(selected);
    var side = getNodeSide(selected);
    var nodesAtDepth = getNodesAtDepth(depth, side);

    var currentIndex = -1;
    for (var i = 0; i < nodesAtDepth.length; i++) {
        if (nodesAtDepth[i].node.id === selected.id) {
            currentIndex = i;
            break;
        }
    }

    if (currentIndex >= 0 && currentIndex < nodesAtDepth.length - 1) {
        var targetId = nodesAtDepth[currentIndex + 1].node.id;
        MM.state.jm.select_node(targetId);
        scrollToNode(targetId);
    }
}

function navigateLeft() {
    if (!MM.state.jm) return;
    var selected = MM.state.jm.get_selected_node();
    if (!selected) return;

    // If at root, go to left-side closest child
    if (selected.isroot) {
        if (selected.children && selected.children.length > 0) {
            var rootVd = selected._data && selected._data.view;
            if (!rootVd) return;
            var zoom = (MM.state.jm.view && MM.state.jm.view.actualZoom) || 1;
            var rootCenterX = (rootVd.abs_x + rootVd.width / 2) * zoom;
            var rootCenterY = (rootVd.abs_y + rootVd.height / 2) * zoom;

            var leftChildren = [];
            for (var i = 0; i < selected.children.length; i++) {
                var childId = (typeof selected.children[i] === 'string') ? selected.children[i] : selected.children[i].id;
                var childNode = MM.state.jm.get_node(childId);
                if (!childNode) continue;
                var childVd = childNode._data && childNode._data.view;
                if (childVd && childNode._data.view.element) {
                    var childCenterX = (childVd.abs_x + childVd.width / 2) * zoom;
                    if (childCenterX < rootCenterX) {
                        var childCenterY = (childVd.abs_y + childVd.height / 2) * zoom;
                        var dist = Math.abs(childCenterY - rootCenterY);
                        leftChildren.push({ id: childId, dist: dist });
                    }
                }
            }

            if (leftChildren.length > 0) {
                leftChildren.sort(function (a, b) { return a.dist - b.dist; });
                MM.state.jm.select_node(leftChildren[0].id);
                scrollToNode(leftChildren[0].id);
            }
        }
        return;
    }

    // For non-root nodes: determine if on left or right side of root
    var side = getNodeSide(selected);

    if (side === 'left') {
        // Left side: left arrow goes to children
        var child = getClosestChild(selected);
        if (child) {
            MM.state.jm.select_node(child.id);
            scrollToNode(child.id);
        }
    } else {
        // Right side: left arrow goes to parent
        if (selected.parent) {
            MM.state.jm.select_node(selected.parent);
            scrollToNode(selected.parent.id);
        }
    }
}

function navigateRight() {
    if (!MM.state.jm) return;
    var selected = MM.state.jm.get_selected_node();
    if (!selected) return;

    // If at root, go to right-side closest child
    if (selected.isroot) {
        if (selected.children && selected.children.length > 0) {
            var rootVd = selected._data && selected._data.view;
            if (!rootVd) return;
            var zoom = (MM.state.jm.view && MM.state.jm.view.actualZoom) || 1;
            var rootCenterX = (rootVd.abs_x + rootVd.width / 2) * zoom;
            var rootCenterY = (rootVd.abs_y + rootVd.height / 2) * zoom;

            var rightChildren = [];
            for (var i = 0; i < selected.children.length; i++) {
                var childId = (typeof selected.children[i] === 'string') ? selected.children[i] : selected.children[i].id;
                var childNode = MM.state.jm.get_node(childId);
                if (!childNode) continue;
                var childVd = childNode._data && childNode._data.view;
                if (childVd && childNode._data.view.element) {
                    var childCenterX = (childVd.abs_x + childVd.width / 2) * zoom;
                    if (childCenterX > rootCenterX) {
                        var childCenterY = (childVd.abs_y + childVd.height / 2) * zoom;
                        var dist = Math.abs(childCenterY - rootCenterY);
                        rightChildren.push({ id: childId, dist: dist });
                    }
                }
            }

            if (rightChildren.length > 0) {
                rightChildren.sort(function (a, b) { return a.dist - b.dist; });
                MM.state.jm.select_node(rightChildren[0].id);
                scrollToNode(rightChildren[0].id);
            }
        }
        return;
    }

    // For non-root nodes: determine if on left or right side of root
    var side = getNodeSide(selected);

    if (side === 'left') {
        // Left side: right arrow goes to parent
        if (selected.parent) {
            MM.state.jm.select_node(selected.parent);
            scrollToNode(selected.parent.id);
        }
    } else {
        // Right side: right arrow goes to children
        var child = getClosestChild(selected);
        if (child) {
            MM.state.jm.select_node(child.id);
            scrollToNode(child.id);
        }
    }
}

