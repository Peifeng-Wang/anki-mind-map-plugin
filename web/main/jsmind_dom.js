function getJsMindPanelEl() {
    if (MM.state.jm && MM.state.jm.view && MM.state.jm.view.e_panel) return MM.state.jm.view.e_panel;
    var container = document.getElementById('jsmind_container');
    if (!container) return null;
    return container.querySelector('.jsmind-inner');
}

function getJsMindNodesEl() {
    if (MM.state.jm && MM.state.jm.view && MM.state.jm.view.e_nodes) return MM.state.jm.view.e_nodes;
    var panel = getJsMindPanelEl();
    if (!panel) return null;
    return panel.querySelector('jmnodes');
}

// Older versions created extra <jmnodes> outside the jsMind panel; those won't be zoomed/scrolled correctly.
function migrateLegacyCustomNodesIntoJsMindNodes() {
    if (!MM.state.jm) return;
    var container = document.getElementById('jsmind_container');
    if (!container) return;
    var nodesEl = getJsMindNodesEl();
    if (!nodesEl) return;

    var allNodesEls = Array.prototype.slice.call(container.querySelectorAll('jmnodes'));
    allNodesEls.forEach(function (el) {
        if (el === nodesEl) return;

        // Move only custom nodes we create (avoid touching jsMind's own nodes container).
        var directChildren = Array.prototype.slice.call(el.children || []);
        directChildren.forEach(function (n) {
            if (!n || !n.tagName) return;
            var tag = n.tagName.toLowerCase();
            if (tag === 'jmnode') {
                var id = n.getAttribute('nodeid') || '';
                if (id.startsWith(MM.state.floatingNodeIdPrefix) || id.startsWith(MM.state.summaryBraceIdPrefix)) {
                    nodesEl.appendChild(n);
                }
                return;
            }
            if (n.getAttribute && n.getAttribute('data-summary-wrapper') === 'true') {
                nodesEl.appendChild(n);
            }
        });

        // Remove the legacy container if it is now empty.
        if (el.children.length === 0 && el.parentNode) {
            el.parentNode.removeChild(el);
        }
    });

    // Remove duplicate summary overlay layers if they exist.
    var summaryLayers = Array.prototype.slice.call(container.querySelectorAll('#summary-overlay-layer'));
    summaryLayers.forEach(function (layer) {
        if (layer.parentNode !== nodesEl && layer.parentNode) {
            layer.parentNode.removeChild(layer);
        }
    });
}

// Hotkey configuration (loaded from config, defaults here)
