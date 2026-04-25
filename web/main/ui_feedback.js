function escapeHtml(text) {
    return String(text)
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#039;');
}

function removeCustomContextMenu() {
    var existing = document.getElementById('custom-context-menu');
    if (existing) existing.remove();
}

function isInCustomContextMenu(target) {
    var menu = document.getElementById('custom-context-menu');
    if (!menu || !target) return false;
    return menu === target || menu.contains(target);
}

function isVisibleForOverlay(elem) {
    if (!elem || !elem.isConnected) return false;
    // jmnode elements are absolutely positioned; when jsMind hides nodes it typically uses display:none/visibility:hidden.
    var style = window.getComputedStyle(elem);
    if (style.display === 'none' || style.visibility === 'hidden') return false;
    var rect = elem.getBoundingClientRect();
    if ((rect.width === 0 && rect.height === 0) || rect.bottom === rect.top) return false;
    return true;
}

function isMindNodeVisible(node) {
    if (!jm || !node) return false;
    if (typeof jm.is_node_visible === 'function') {
        try {
            return jm.is_node_visible(node);
        } catch (e) {
            // fall through to DOM check
        }
    }
    if (node._data && node._data.view && node._data.view.element) {
        return isVisibleForOverlay(node._data.view.element);
    }
    return false;
}

function getNodeBoxFromView(node) {
    if (!node || !node._data || !node._data.view) return null;
    var vd = node._data.view;
    if (typeof vd.abs_x !== 'number' || typeof vd.abs_y !== 'number') return null;
    if (typeof vd.width !== 'number' || typeof vd.height !== 'number') return null;
    return {
        left: vd.abs_x,
        right: vd.abs_x + vd.width,
        top: vd.abs_y,
        bottom: vd.abs_y + vd.height
    };
}

function getElementBoxFromClientRectInMap(elem) {
    if (!elem || !elem.isConnected) return null;
    if (!jm || !jm.view) return null;

    var panel = getJsMindPanelEl();
    if (!panel) return null;

    var rect = elem.getBoundingClientRect();
    if (!rect) return null;

    var panelRect = panel.getBoundingClientRect();
    if (!panelRect) return null;

    var z = (jm.view && jm.view.actualZoom) || 1;
    if (!z) z = 1;

    // Screen = panel origin + (map * zoom - scroll). Solve for map.
    var left = (rect.left - panelRect.left + panel.scrollLeft) / z;
    var top = (rect.top - panelRect.top + panel.scrollTop) / z;
    var right = (rect.right - panelRect.left + panel.scrollLeft) / z;
    var bottom = (rect.bottom - panelRect.top + panel.scrollTop) / z;

    return { left: left, right: right, top: top, bottom: bottom };
}

function getOrCreateOverlayLayer(parent, layerId, zIndex, pointerEvents, setZoomOnLayer) {
    if (!parent) return null;
    var layer = parent.querySelector('#' + layerId);
    if (!layer) {
        layer = document.createElement('div');
        layer.id = layerId;
        layer.style.cssText = [
            'position:absolute',
            'left:0',
            'top:0',
            'width:1px',
            'height:1px',
            'overflow:visible',
            'z-index:' + zIndex,
            'pointer-events:' + pointerEvents
        ].join(';') + ';';
        parent.appendChild(layer);
    }
    // Keep in sync with current map zoom (newly-created layers won't be touched until the next zoom).
    // Note: if the layer is placed under an element that is already zoomed (e.g. under <jmnodes>),
    // setZoomOnLayer must be false to avoid double-scaling.
    if (setZoomOnLayer && jm && jm.view && typeof jm.view.actualZoom === 'number') {
        layer.style.zoom = jm.view.actualZoom;
    } else {
        // Clear any stale zoom from older versions or mismatched callers.
        layer.style.zoom = '';
    }
    return layer;
}

function scheduleNodeEditAutoSave() {
    if (autoSaveTimeout) {
        clearTimeout(autoSaveTimeout);
    }
    autoSaveTimeout = setTimeout(function () {
        console.log('Auto-saving after node edit...');
        autoSave();
    }, 300);
}

function installUpdateNodeTracking(logPrefix) {
    if (!jm || typeof jm.update_node !== 'function') return;

    if (jm.update_node._ankiMindMapTracksChanges) {
        jm.update_node._ankiMindMapLogPrefix = logPrefix;
        return;
    }

    var originalUpdateNode = jm.update_node;
    var trackedUpdateNode = function (nodeid, topic) {
        var result = originalUpdateNode.call(jm, nodeid, topic);
        changedNodes.add(nodeid);
        console.log(trackedUpdateNode._ankiMindMapLogPrefix, nodeid, 'New topic:', topic);
        scheduleNodeEditAutoSave();
        return result;
    };

    trackedUpdateNode._ankiMindMapTracksChanges = true;
    trackedUpdateNode._ankiMindMapLogPrefix = logPrefix;
    trackedUpdateNode._ankiMindMapOriginal = originalUpdateNode;
    jm.update_node = trackedUpdateNode;
}

