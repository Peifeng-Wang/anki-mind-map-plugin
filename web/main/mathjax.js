function countNodes(node) {
    var count = 1;
    if (node.children) {
        for (var i = 0; i < node.children.length; i++) {
            count += countNodes(node.children[i]);
        }
    }
    return count;
}

function renderMath() {
    if (typeof MathJax !== 'undefined' && MathJax.typesetPromise) {
        MathJax.typesetPromise([document.getElementById('jsmind_container')])
            .catch((err) => console.error("MathJax error:", err));
    } else {
        setTimeout(renderMath, 1000);
    }
}

// Mark nodes that are linked to Anki cards or other mind maps
function markLinkedNodes() {
    if (!jm) return;

    try {
        var allNodes = document.querySelectorAll('jmnode');
        allNodes.forEach(function (nodeElement) {
            var nodeId = nodeElement.getAttribute('nodeid');
            if (!nodeId) return;

            var node = jm.get_node(nodeId);
            if (!node) return;

            // Check if node has a linked card (noteId in node.data)
            var hasCard = node.data && node.data.noteId;

            if (hasCard) {
                nodeElement.setAttribute('data-has-card', 'true');
            } else {
                nodeElement.removeAttribute('data-has-card');
            }

            // Check if this is a map-linked node
            var isMapLink = node.data && node.data.isMapLink;
            if (isMapLink) {
                nodeElement.setAttribute('data-is-map-link', 'true');
            } else {
                nodeElement.removeAttribute('data-is-map-link');
            }

            // Check if this root has linked maps
            var hasLinkedMaps = node.isroot && node.data && node.data.linkedMaps && node.data.linkedMaps.length > 0;
            if (hasLinkedMaps) {
                nodeElement.setAttribute('data-has-linked-maps', 'true');
            } else {
                nodeElement.removeAttribute('data-has-linked-maps');
            }
        });
    } catch (e) {
        console.error("Error marking linked nodes:", e);
    }
}
