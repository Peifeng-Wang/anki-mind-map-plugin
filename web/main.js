var jm = null;
var autoSaveTimeout = null;
var autoSaveDelay = 2000;

var mindMapHistory = [];
var mindMapHistoryIndex = -1;
var maxHistory = 50;
var mindMapHistoryStateStrings = [];

var selectedNodes = [];
var isEditing = false;
var editingNodeId = null;
var selectionBox = null;
var isSelecting = false;
var selectionStart = { x: 0, y: 0 };

var arrows = [];
var arrowMode = false;
var arrowStart = null;

// Floating nodes (nodes without parent)
var floatingNodes = [];
var floatingNodeIdPrefix = 'floating_';

// Summary braces data
var summaryBraces = [];
var summaryBraceIdPrefix = 'summary_';
var braceColor = '#3b82f6';

// Boundary data
var boundaries = [];
var boundaryIdPrefix = 'boundary_';
var boundaryColor = '#ef4444';
var selectedBoundary = null;

// Track changed node IDs (for syncing to cards)
var changedNodes = new Set();
var overlayRenderTimer = null;
var overlayRenderRaf = null;
var overlayRenderTimer2 = null;
var overlayRenderRaf2 = null;
var scrollToNodeAnimToken = 0;
var scrollToNodeAnimRaf = null;

function getJsMindPanelEl() {
    if (jm && jm.view && jm.view.e_panel) return jm.view.e_panel;
    var container = document.getElementById('jsmind_container');
    if (!container) return null;
    return container.querySelector('.jsmind-inner');
}

function getJsMindNodesEl() {
    if (jm && jm.view && jm.view.e_nodes) return jm.view.e_nodes;
    var panel = getJsMindPanelEl();
    if (!panel) return null;
    return panel.querySelector('jmnodes');
}

// Older versions created extra <jmnodes> outside the jsMind panel; those won't be zoomed/scrolled correctly.
function migrateLegacyCustomNodesIntoJsMindNodes() {
    if (!jm) return;
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
                if (id.startsWith(floatingNodeIdPrefix) || id.startsWith(summaryBraceIdPrefix)) {
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
var hotkeyConfig = {
    save: 'Ctrl+S',
    refresh: 'F5',
    focus_root: 'Ctrl+R',
    create_summary: 'Ctrl+Shift+S',
    create_boundary: 'Ctrl+Shift+B',
    bold: 'Ctrl+B',
    italic: 'Ctrl+I',
    inline_code: 'Ctrl+`',
    code_block: 'Ctrl+Shift+`',
    toggle_collapse: '`'
};


// Match hotkey event against config string
function matchHotkey(e, hotkeyString) {
    if (!hotkeyString) return false;

    var parts = hotkeyString.split('+');
    var key = parts[parts.length - 1];
    var needsCtrl = parts.includes('Ctrl');
    var needsMeta = parts.includes('Meta') || parts.includes('Cmd');
    var needsShift = parts.includes('Shift');
    var needsAlt = parts.includes('Alt');

    var eventKey = e.key;

    // For non-F-keys, do case-insensitive comparison
    if (!key.match(/^F\d+$/)) {
        key = key.toLowerCase();
        eventKey = eventKey.toLowerCase();
    }

    // Some keys produce a different character when Shift is held (e.g. ` -> ~).
    // Allow matching config strings that use the unshifted character.
    var shiftedToUnshifted = {
        '~': '`',
        '!': '1',
        '@': '2',
        '#': '3',
        '$': '4',
        '%': '5',
        '^': '6',
        '&': '7',
        '*': '8',
        '(': '9',
        ')': '0',
        '_': '-',
        '+': '=',
        '{': '[',
        '}': ']',
        '|': '\\',
        ':': ';',
        '"': '\'',
        '<': ',',
        '>': '.',
        '?': '/'
    };

    var keyMatches = (eventKey === key) ||
        (needsShift && shiftedToUnshifted[eventKey] && shiftedToUnshifted[eventKey] === key);

    return keyMatches &&
        (e.ctrlKey || e.metaKey) === (needsCtrl || needsMeta) &&
        e.shiftKey === needsShift &&
        e.altKey === needsAlt;
}

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

function toggleWrapSelection(textarea, openTag, closeTag) {
    var value = textarea.value;
    var start = textarea.selectionStart;
    var end = textarea.selectionEnd;

    if (start === end) {
        textarea.value = value.substring(0, start) + openTag + closeTag + value.substring(end);
        textarea.selectionStart = textarea.selectionEnd = start + openTag.length;
        return;
    }

    var before = value.substring(0, start);
    var selected = value.substring(start, end);
    var after = value.substring(end);

    var hasWrap =
        start >= openTag.length &&
        value.substring(start - openTag.length, start) === openTag &&
        value.substring(end, end + closeTag.length) === closeTag;

    if (hasWrap) {
        textarea.value =
            value.substring(0, start - openTag.length) +
            selected +
            value.substring(end + closeTag.length);
        textarea.selectionStart = start - openTag.length;
        textarea.selectionEnd = end - openTag.length;
        return;
    }

    textarea.value = before + openTag + selected + closeTag + after;
    textarea.selectionStart = start + openTag.length;
    textarea.selectionEnd = end + openTag.length;
}

function wrapSelectionAsEscapedHtml(textarea, openTag, closeTag) {
    var value = textarea.value;
    var start = textarea.selectionStart;
    var end = textarea.selectionEnd;

    if (start === end) {
        textarea.value = value.substring(0, start) + openTag + closeTag + value.substring(end);
        textarea.selectionStart = textarea.selectionEnd = start + openTag.length;
        return;
    }

    var before = value.substring(0, start);
    var selected = value.substring(start, end);
    var after = value.substring(end);

    textarea.value = before + openTag + selected + closeTag + after;
    // Keep the original selection (inside the tags).
    textarea.selectionStart = start + openTag.length;
    textarea.selectionEnd = end + openTag.length;
}

function escapeCodeTagsForDisplay(text) {
    // Escape any content inside <code>...</code> and <pre><code>...</code></pre>.
    // This lets users type raw code in the textarea without manually HTML-escaping it.
    var blocks = [];
    var token = '__CODE_ESC_' + Date.now() + '_' + Math.random().toString(16).slice(2) + '__';

    function stash(html) {
        blocks.push(html);
        return token + (blocks.length - 1) + token;
    }

    var out = String(text);

    // Process code blocks first so the inline <code> regex won't touch them.
    out = out.replace(/<pre><code>([\s\S]*?)<\/code><\/pre>/gi, function (_m, inner) {
        return stash('<pre><code>' + escapeHtml(inner) + '</code></pre>');
    });

    out = out.replace(/<code>([\s\S]*?)<\/code>/gi, function (_m, inner) {
        return stash('<code>' + escapeHtml(inner) + '</code>');
    });

    out = out.replace(new RegExp(token + '(\\d+)' + token, 'g'), function (_m, idx) {
        return blocks[Number(idx)] || '';
    });

    return out;
}

function showEditFormattingContextMenu(x, y, textarea, onResize) {

    var selectionSnapshot = {
        start: textarea.selectionStart,
        end: textarea.selectionEnd
    };

    function runWithSelection(action) {
        textarea.focus();
        textarea.selectionStart = selectionSnapshot.start;
        textarea.selectionEnd = selectionSnapshot.end;
        action();
        selectionSnapshot.start = textarea.selectionStart;
        selectionSnapshot.end = textarea.selectionEnd;
        if (typeof onResize === 'function') onResize();
    }

    var menu = document.createElement('div');
    menu.id = 'custom-context-menu';
    menu.style.cssText = `
        position: fixed;
        left: ${x}px;
        top: ${y}px;
        background: white;
        border: 1px solid #ccc;
        box-shadow: 2px 2px 5px rgba(0,0,0,0.2);
        z-index: 10000;
        padding: 5px 0;
        border-radius: 4px;
        min-width: 160px;
    `;

    function createMenuItem(text, onClick) {
        var item = document.createElement('div');
        item.innerText = text;
        item.style.cssText = `
            padding: 8px 15px;
            cursor: pointer;
            font-family: sans-serif;
            font-size: 14px;
            color: #333;
        `;
        item.onmouseover = function () { this.style.background = '#f0f0f0'; };
        item.onmouseout = function () { this.style.background = 'white'; };
        // Keep focus in the textarea while interacting with the menu.
        item.addEventListener('mousedown', function (ev) {
            ev.preventDefault();
            ev.stopPropagation();
            ev.stopImmediatePropagation();
        }, true);
        item.onclick = function () {
            onClick();
            menu.remove();
        };
        return item;
    }

    menu.appendChild(createMenuItem('Bold', function () {
        runWithSelection(function () { toggleWrapSelection(textarea, '<b>', '</b>'); });
    }));
    menu.appendChild(createMenuItem('Italic', function () {
        runWithSelection(function () { toggleWrapSelection(textarea, '<i>', '</i>'); });
    }));
    menu.appendChild(createMenuItem('Inline Code', function () {
        runWithSelection(function () { wrapSelectionAsEscapedHtml(textarea, '<code>', '</code>'); });
    }));
    menu.appendChild(createMenuItem('Code Block', function () {
        runWithSelection(function () { wrapSelectionAsEscapedHtml(textarea, '<pre><code>', '</code></pre>'); });
    }));

    document.body.appendChild(menu);

    // Close on click elsewhere.
    var closeHandler = function (e) {
        if (!menu.contains(e.target)) {
            menu.remove();
            document.removeEventListener('click', closeHandler, true);
        }
    };
    setTimeout(function () { document.addEventListener('click', closeHandler, true); }, 0);
}

// Called from Python (Qt shortcuts) and can also be used by other JS code.
window.applyTextFormatting = function (action) {
    if (!action) return;
    if (!isEditing || !editingNodeId) return;

    var textarea = document.getElementById('input-box');
    if (!textarea) return;

    textarea.focus();

    if (action === 'bold') {
        toggleWrapSelection(textarea, '<b>', '</b>');
    } else if (action === 'italic') {
        toggleWrapSelection(textarea, '<i>', '</i>');
    } else if (action === 'inline_code') {
        wrapSelectionAsEscapedHtml(textarea, '<code>', '</code>');
    } else if (action === 'code_block') {
        wrapSelectionAsEscapedHtml(textarea, '<pre><code>', '</code></pre>');
    }

    // Trigger the existing input listener to re-measure the textarea.
    textarea.dispatchEvent(new Event('input'));
};

// Fallback: capture hotkeys at document level during edit mode (some environments don't deliver them to textarea).
document.addEventListener('keydown', function (e) {
    if (!isEditing || !editingNodeId) return;

    if (matchHotkey(e, hotkeyConfig.bold)) {
        e.preventDefault();
        e.stopPropagation();
        e.stopImmediatePropagation();
        window.applyTextFormatting('bold');
        return;
    }
    if (matchHotkey(e, hotkeyConfig.italic)) {
        e.preventDefault();
        e.stopPropagation();
        e.stopImmediatePropagation();
        window.applyTextFormatting('italic');
        return;
    }
    if (matchHotkey(e, hotkeyConfig.inline_code)) {
        e.preventDefault();
        e.stopPropagation();
        e.stopImmediatePropagation();
        window.applyTextFormatting('inline_code');
        return;
    }
    if (matchHotkey(e, hotkeyConfig.code_block)) {
        e.preventDefault();
        e.stopPropagation();
        e.stopImmediatePropagation();
        window.applyTextFormatting('code_block');
        return;
    }
}, true);

function initEditor(data) {
    try {
        if (typeof jsMind === 'undefined') {
            alert("Error: jsMind library not loaded");
            return;
        }

        if (typeof data === 'string') {
            data = JSON.parse(data);
        }

        if (data.nodeData) {
            data = {
                "meta": { "name": "map", "author": "anki", "version": "0.2" },
                "format": "node_tree",
                "data": { "id": "root", "topic": data.nodeData.topic || "Map" }
            };
        }

        jm = new jsMind({
            container: 'jsmind_container',
            theme: 'modern-premium',
            editable: true,
            support_html: true,
            view: {
                draggable: true,
                line_width: 3,
                line_color: (typeof lineColorFromPython !== 'undefined' ? lineColorFromPython : 'rgba(139, 92, 246, 0.6)')
            },
            shortcut: { enable: false }
        });

        jm.add_event_listener(function (type, data) {
            if (type === 3) {
                console.log('Detected change...');
                window.saveHistory();
                scheduleAutoSave();
            }
        });

        jm.show(data);
        saveHistory();
        migrateLegacyCustomNodesIntoJsMindNodes();

        if (data.data && data.data.id) {
            jm.select_node(data.data.id);
        }

        // Create overlay layers early so zoom changes keep them in sync.
        var containerEl = document.getElementById('jsmind_container');
        var panelEl = getJsMindPanelEl();
        var nodesEl = getJsMindNodesEl();
        if (nodesEl) {
            // Put summary overlay under <jmnodes> so it inherits the same zoom as nodes.
            getOrCreateOverlayLayer(nodesEl, 'summary-overlay-layer', 1, 'none', false);
        }
        if (panelEl) {
            // Boundary overlay stays at panel level and is zoomed directly.
            getOrCreateOverlayLayer(panelEl, 'boundary-overlay-layer', 5, 'auto', true);
        }

        setTimeout(() => {
            document.getElementById('jsmind_container').focus();
        }, 100);

        setTimeout(renderMath, 500);
        setupMultiSelection();
        setupFloatingNodes();
        setupShiftClickSelection();

        // Load brace color from config if available
        if (typeof braceColorFromPython !== 'undefined') {
            braceColor = braceColorFromPython;
        }

        // Load floating nodes if they exist
        if (data.floatingNodes && Array.isArray(data.floatingNodes)) {
            data.floatingNodes.forEach(function (nodeData) {
                loadFloatingNode(nodeData);
            });
        }

        // Load summary braces if they exist
        if (data.summaryBraces && Array.isArray(data.summaryBraces)) {
            summaryBraces = data.summaryBraces;
            setTimeout(function () {
                renderSummaryBraces();
                markSummaryNodes();
            }, 200);
        }

        // Load boundaries if they exist
        if (data.boundaries && Array.isArray(data.boundaries)) {
            boundaries = data.boundaries;
            // Load boundary color from config if available
            if (typeof boundaryColorFromPython !== 'undefined') {
                boundaryColor = boundaryColorFromPython;
            }
            setTimeout(function () {
                renderBoundaries();
            }, 250);
        }

        jm.add_event_listener(function (type, data) {
            if (type === 3) {
                console.log('Detected change, saving history...');
                saveHistory();
                scheduleAutoSave();
            }
        });

        function scheduleOverlayRerender() {
            if (overlayRenderTimer) {
                clearTimeout(overlayRenderTimer);
                overlayRenderTimer = null;
            }
            if (overlayRenderRaf) {
                cancelAnimationFrame(overlayRenderRaf);
                overlayRenderRaf = null;
            }
            if (overlayRenderTimer2) {
                clearTimeout(overlayRenderTimer2);
                overlayRenderTimer2 = null;
            }
            if (overlayRenderRaf2) {
                cancelAnimationFrame(overlayRenderRaf2);
                overlayRenderRaf2 = null;
            }

            // Defer to the next frame so zoom/style updates have settled.
            overlayRenderTimer = setTimeout(function () {
                overlayRenderRaf = requestAnimationFrame(function () {
                    renderSummaryBraces();
                    renderBoundaries();
                });
            }, 0);

            // Qt WebEngine can apply style.zoom asynchronously at extreme values; do a second pass after a short delay.
            overlayRenderTimer2 = setTimeout(function () {
                overlayRenderRaf2 = requestAnimationFrame(function () {
                    renderSummaryBraces();
                    renderBoundaries();
                });
            }, 80);
        }

        // Re-render braces when layout changes
        jm.add_event_listener(function (type, data) {
            if (type === 1 || type === 2) { // show or resize events
                scheduleOverlayRerender();
            }
        });

        // Drag-to-pan (jsMind draggable canvas) can change view offsets without emitting show/resize events.
        // Keep overlays in sync by rerendering on scroll and at the end of a drag.
        if (panelEl) {
            panelEl.addEventListener('scroll', function () {
                scheduleOverlayRerender();
            }, { passive: true });
        }
        if (containerEl) {
            containerEl.addEventListener('mouseup', function () {
                scheduleOverlayRerender();
            }, true);
            containerEl.addEventListener('mouseleave', function () {
                scheduleOverlayRerender();
            }, true);
        }

        console.log("jsMind initialized");

        installUpdateNodeTracking('Node changed:');

        // Mark nodes linked to cards after initial render
        setTimeout(markLinkedNodes, 100);


    } catch (e) {
        alert("Error: " + e);
        console.error(e);
    }
}

// Load a floating node from saved data
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

window.saveHistory = function () {
    if (!jm) return;

    try {
        if (!Array.isArray(mindMapHistory)) {
            mindMapHistory = [];
            mindMapHistoryStateStrings = [];
            mindMapHistoryIndex = -1;
        }

        var mindMapData = jm.get_data('node_tree');
        var floatingData = floatingNodes.map(function (n) {
            return { id: n.id, topic: n.topic, x: n.x, y: n.y };
        });

        var currentState = {
            mind: mindMapData,
            floating: floatingData
        };
        var currentStateStr = JSON.stringify(currentState);

        if (mindMapHistoryIndex >= 0 && mindMapHistory[mindMapHistoryIndex]) {
            var lastStateStr = mindMapHistoryStateStrings[mindMapHistoryIndex];
            if (typeof lastStateStr !== 'string') {
                lastStateStr = JSON.stringify(mindMapHistory[mindMapHistoryIndex]);
                mindMapHistoryStateStrings[mindMapHistoryIndex] = lastStateStr;
            }
            if (currentStateStr === lastStateStr) return;
        }

        if (mindMapHistoryIndex < mindMapHistory.length - 1) {
            mindMapHistory = mindMapHistory.slice(0, mindMapHistoryIndex + 1);
            mindMapHistoryStateStrings = mindMapHistoryStateStrings.slice(0, mindMapHistoryIndex + 1);
        }

        mindMapHistory.push(JSON.parse(currentStateStr));
        mindMapHistoryStateStrings.push(currentStateStr);

        if (mindMapHistory.length > maxHistory) {
            mindMapHistory.shift();
            mindMapHistoryStateStrings.shift();
        } else {
            mindMapHistoryIndex++;
        }

        console.log("History saved. Total steps: " + mindMapHistory.length);
    } catch (e) {
        console.error("Error saving history:", e);
    }
};

function restoreState(state) {
    if (!state) return;
    console.log("Restoring state...");

    var panel = jm.view.e_panel;

    var lastScrollX = panel.scrollLeft;
    var lastScrollY = panel.scrollTop;

    var selectedNode = jm.get_selected_node();
    var lastSelectedId = selectedNode ? selectedNode.id : null;

    if (state.mind) {
        jm.show(state.mind);
    }

    floatingNodes = [];
    var container = document.getElementById('jsmind_container');
    var oldNodes = container.querySelectorAll('jmnode[nodeid^="floating_"]');
    oldNodes.forEach(function (el) { el.remove(); });

    if (state.floating && Array.isArray(state.floating)) {
        state.floating.forEach(function (nodeData) {
            loadFloatingNode(nodeData);
        });
    }

    if (panel) {
        panel.scrollLeft = lastScrollX;
        panel.scrollTop = lastScrollY;
    }

    if (lastSelectedId) {
        var node = jm.get_node(lastSelectedId);
        if (node) {
            jm.select_node(lastSelectedId);
        } else {
            jm.select_clear();
        }
    } else {
        jm.select_clear();
    }
}

window.undo = function () {
    console.log("Undo trigger received. Index: " + mindMapHistoryIndex);
    if (mindMapHistoryIndex > 0) {
        mindMapHistoryIndex--;
        restoreState(mindMapHistory[mindMapHistoryIndex]);
        scheduleAutoSave();
    } else {
        console.log("Nothing to undo");
    }
};

window.redo = function () {
    console.log("Redo trigger received. Index: " + mindMapHistoryIndex);
    if (mindMapHistoryIndex < mindMapHistory.length - 1) {
        mindMapHistoryIndex++;
        restoreState(mindMapHistory[mindMapHistoryIndex]);
        scheduleAutoSave();
    }
};

function scheduleAutoSave() {
    if (autoSaveTimeout) {
        clearTimeout(autoSaveTimeout);
    }

    autoSaveTimeout = setTimeout(function () {
        autoSave();
    }, autoSaveDelay);
}

function collectFloatingNodesData() {
    return floatingNodes.map(function (node) {
        return {
            id: node.id,
            topic: node.topic,
            x: node.x,
            y: node.y
        };
    });
}

function collectChangedNodesData() {
    var changedNodesData = [];
    changedNodes.forEach(function (nodeId) {
        var node = jm.get_node(nodeId);
        if (!node) return;

        // jsMind stores custom data in node.data
        var noteId = node.data && node.data.noteId;
        var isMapLink = node.data && node.data.isMapLink;
        var sourceMapId = node.data && node.data.sourceMapId;
        var hasLinkedMaps = node.isroot && node.data && node.data.linkedMaps;

        // Include nodes with linked cards
        if (noteId) {
            changedNodesData.push({
                id: nodeId,
                topic: node.topic,
                noteId: noteId
            });
        }

        // Include map-linked nodes for sync
        if (isMapLink && sourceMapId) {
            changedNodesData.push({
                id: nodeId,
                topic: node.topic,
                isMapLink: true,
                sourceMapId: sourceMapId
            });
        }

        // Include root nodes with linkedMaps for sync
        if (hasLinkedMaps) {
            changedNodesData.push({
                id: nodeId,
                topic: node.topic,
                hasLinkedMaps: true,
                linkedMaps: node.data.linkedMaps
            });
        }
    });
    return changedNodesData;
}

function buildSavePayload() {
    var mind_data = jm.get_data('node_tree');
    var container = document.getElementById('jsmind_container');

    return {
        data: mind_data,
        image_html: container ? container.innerHTML : "",
        arrows: arrows,
        floatingNodes: collectFloatingNodesData(),
        summaryBraces: summaryBraces,
        boundaries: boundaries,
        changedNodes: collectChangedNodesData()
    };
}

function autoSave() {
    if (!jm) return;

    try {
        var payload = buildSavePayload();

        console.log('AutoSaving... Data nodes count:', payload.data.data ? countNodes(payload.data.data) : 0);
        console.log('Changed nodes to sync:', payload.changedNodes);

        pycmd("save:" + JSON.stringify(payload));

        // Clear change records
        changedNodes.clear();

        var status = document.getElementById('auto-save-status');
        if (status) {
            status.style.opacity = '1';
            setTimeout(function () {
                status.style.opacity = '0';
            }, 1500);
        }
    } catch (e) {
        console.error("Auto-save error:", e);
    }
}

// Helper function to count nodes
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

function addChild() {
    if (!jm) return;
    var selected = jm.get_selected_node();
    if (!selected) {
        alert("Please select a node first");
        return;
    }
    var newId = 'node_' + Date.now();
    jm.add_node(selected, newId, 'New Child');
    jm.select_node(newId);
    setTimeout(renderMath, 300);
    saveHistory();
    scheduleAutoSave();
}

function addSibling() {
    if (!jm) return;
    var selected = jm.get_selected_node();
    if (!selected || selected.isroot) {
        alert("Cannot add sibling to root");
        return;
    }
    // Cannot add sibling to summary node
    if (selected.data && selected.data.isSummaryNode) {
        showToast('Cannot add sibling to summary node');
        return;
    }
    var parent = jm.get_node(selected.parent);
    if (!parent) return;
    var newId = 'node_' + Date.now();
    jm.add_node(parent, newId, 'New Sibling');
    jm.select_node(newId);
    setTimeout(renderMath, 300);
    saveHistory();
    scheduleAutoSave();
}

function saveMap() {
    if (!jm) return;
    try {
        var payload = buildSavePayload();

        console.log('Changed nodes to sync:', payload.changedNodes);

        pycmd("save:" + JSON.stringify(payload));


        // Clear change records
        changedNodes.clear();

        var status = document.getElementById('auto-save-status');
        if (status) {
            status.textContent = 'Saved!';
            status.style.opacity = '1';
            setTimeout(function () {
                status.textContent = 'Auto-saved';
                status.style.opacity = '0';
            }, 2000);
        }
    } catch (e) {
        alert("Error saving: " + e);
    }
}

// Center view on root node
function centerRoot() {
    if (!jm) return;

    var root = jm.get_root();
    if (!root) return;

    // Select root node
    jm.select_node(root);

    // Use jsMind's built-in centering by calling show with keep_center=true
    jm.view.show(true);
}

// Refresh mind map data from database
function refreshMap() {
    if (!jm) return;

    console.log('Requesting data refresh...');
    // Request fresh data from Python
    pycmd("refresh_data");
}

// Toggle fullscreen mode (maximize window in Anki)
function toggleFullscreen() {
    // Use Qt's fullscreen API via pycmd
    // The browser Fullscreen API doesn't work properly in QtWebEngine
    if (typeof pycmd !== 'undefined') {
        pycmd('toggle_fullscreen');
    }
}

// Update fullscreen button text when fullscreen state changes
document.addEventListener('fullscreenchange', updateFullscreenButton);
document.addEventListener('webkitfullscreenchange', updateFullscreenButton);
document.addEventListener('mozfullscreenchange', updateFullscreenButton);
document.addEventListener('MSFullscreenChange', updateFullscreenButton);

function updateFullscreenButton() {
    var btn = document.getElementById('fullscreen-btn');
    if (btn) {
        if (document.fullscreenElement || document.webkitFullscreenElement ||
            document.mozFullScreenElement || document.msFullscreenElement) {
            btn.textContent = '⛶ Exit Fullscreen';
        } else {
            btn.textContent = '⛶ Fullscreen';
        }
    }
}


// Reload mind map with fresh data
function reloadMapData(data) {
    if (!jm) return;

    try {
        console.log('Reloading map with fresh data...');
        console.log('Data nodes count:', data.data ? countNodes(data.data) : 0);

        // Save current selected node
        var selectedNode = jm.get_selected_node();
        var selectedId = selectedNode ? selectedNode.id : null;

        // Save current scroll position
        var container = jm.view.e_panel;
        var scrollLeft = container ? container.scrollLeft : 0;
        var scrollTop = container ? container.scrollTop : 0;
        console.log('Saved scroll position:', scrollLeft, scrollTop);

        // Reload the data
        jm.show(data);

        // Re-setup the update_node override after reload
        installUpdateNodeTracking('Node changed after reload:');

        // Restore scroll position
        if (container) {
            container.scrollLeft = scrollLeft;
            container.scrollTop = scrollTop;
            console.log('Restored scroll position:', scrollLeft, scrollTop);
        }

        // Restore selection only if there was a selected node
        if (selectedId) {
            var node = jm.get_node(selectedId);
            if (node) {
                jm.select_node(selectedId);
                console.log('Restored selection:', selectedId);
            }
        }

        // Re-render math
        setTimeout(renderMath, 300);

        // Mark linked nodes after reload
        setTimeout(markLinkedNodes, 400);

        // Show success message
        showToast('Refreshed!');
        console.log('Map refreshed successfully');
    } catch (e) {
        console.error('Error reloading map:', e);
        alert('Error refreshing map: ' + e);
    }
}

// Show toast message
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

// Check if selected nodes are valid for boundary (siblings only, or single node)
function validateBoundarySelection() {
    if (selectedNodes.length === 0) {
        return { valid: false, reason: 'Select at least 1 node' };
    }

    // Get jsMind nodes and check validity
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

        // For multiple nodes, check they share same parent
        if (selectedNodes.length > 1) {
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
    for (var i = 0; i < boundaries.length; i++) {
        if (boundaries[i].isSpecial) {
            return true;
        }
    }
    return false;
}

// Create a boundary for selected nodes
function createBoundary() {
    if (!jm) return;
    if (jm && !jm.get_editable()) {
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
        id: boundaryIdPrefix + Date.now(),
        nodeIds: nodeIds,
        color: boundaryColor,
        isSpecial: false  // Default not special
    };
    boundaries.push(boundaryData);

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
        for (var i = 0; i < boundaries.length; i++) {
            if (boundaries[i].isSpecial && boundaries[i].id !== boundaryData.id) {
                boundaries[i].isSpecial = false;
                boundaries[i].color = boundaryColor; // Reset to default color
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
        boundaryData.color = boundaryColor;
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

    if (!jm || !jm.view) return;

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
    boundaries = boundaries.filter(function (boundaryData) {
        var validNodes = boundaryData.nodeIds.filter(function (id) {
            return jm.get_node(id) !== null;
        });
        if (validNodes.length === 0) {
            return false;
        }
        boundaryData.nodeIds = validNodes;
        return true;
    });

    // Sort boundaries by size (smaller/inner first)
    var sortedBoundaries = boundaries.slice().sort(function (a, b) {
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
        var node = jm.get_node(nodeIds[i]);
        getNodeBounds(node);
    }

    // Check for summary braces that might be attached to these nodes
    summaryBraces.forEach(function (braceData) {
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
        strokeRect.setAttribute('stroke', boundaryData.color || boundaryColor);
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
    selectedBoundary = boundaryData;
    svgElement.classList.add('selected');

    // Deselect jsMind nodes
    if (jm) jm.select_clear();
    clearSelection();
}

// Delete a boundary
function deleteBoundary(boundaryData) {
    var idx = boundaries.indexOf(boundaryData);
    if (idx > -1) {
        boundaries.splice(idx, 1);
    }

    selectedBoundary = null;
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

function toggleArrowMode() {
    arrowMode = !arrowMode;
    if (arrowMode) {
        document.getElementById('jsmind_container').style.cursor = 'crosshair';
    } else {
        document.getElementById('jsmind_container').style.cursor = 'default';
        arrowStart = null;
    }
}

// Get all nodes at the same depth level and side, sorted by vertical position
function getNodesAtDepth(depth, filterSide) {
    var allNodes = [];

    function traverse(node, currentDepth) {
        if (currentDepth === depth) {
            var elem = document.querySelector('jmnode[nodeid="' + node.id + '"]');
            if (elem) {
                var rect = elem.getBoundingClientRect();
                allNodes.push({
                    node: node,
                    top: rect.top,
                    centerY: rect.top + rect.height / 2,
                    centerX: rect.left + rect.width / 2
                });
            }
        }

        if (node.children && currentDepth < depth) {
            for (var i = 0; i < node.children.length; i++) {
                var childId = (typeof node.children[i] === 'string') ? node.children[i] : node.children[i].id;
                var childNode = jm.get_node(childId);
                if (childNode) {
                    traverse(childNode, currentDepth + 1);
                }
            }
        }
    }

    var root = jm.get_root();
    traverse(root, 0);

    // Filter by side if specified
    if (filterSide !== null && filterSide !== undefined) {
        var rootElem = document.querySelector('jmnode[nodeid="' + root.id + '"]');
        if (rootElem) {
            var rootCenterX = rootElem.getBoundingClientRect().left + rootElem.getBoundingClientRect().width / 2;
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
        current = jm.get_node(current.parent);
        if (!current) break;
    }
    return depth;
}

// Get node side relative to root
function getNodeSide(node) {
    if (node.isroot) return 'center';

    var root = jm.get_root();
    var rootElem = document.querySelector('jmnode[nodeid="' + root.id + '"]');
    var nodeElem = document.querySelector('jmnode[nodeid="' + node.id + '"]');

    if (!rootElem || !nodeElem) return null;

    var rootCenterX = rootElem.getBoundingClientRect().left + rootElem.getBoundingClientRect().width / 2;
    var nodeCenterX = nodeElem.getBoundingClientRect().left + nodeElem.getBoundingClientRect().width / 2;

    return nodeCenterX < rootCenterX ? 'left' : 'right';
}

// Get closest child by vertical distance
function getClosestChild(parentNode) {
    if (!parentNode.children || parentNode.children.length === 0) return null;

    var parentElem = document.querySelector('jmnode[nodeid="' + parentNode.id + '"]');
    if (!parentElem) return null;

    var parentRect = parentElem.getBoundingClientRect();
    var parentCenterY = parentRect.top + parentRect.height / 2;

    var closest = null;
    var minDist = Infinity;

    for (var i = 0; i < parentNode.children.length; i++) {
        var childId = (typeof parentNode.children[i] === 'string') ? parentNode.children[i] : parentNode.children[i].id;
        var childNode = jm.get_node(childId);
        if (!childNode) continue;

        var childElem = document.querySelector('jmnode[nodeid="' + childId + '"]');
        if (childElem) {
            var childRect = childElem.getBoundingClientRect();
            var childCenterY = childRect.top + childRect.height / 2;
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
    if (!jm || !jm.view) return;

    // Get jsMind's scroll container (the actual panel that scrolls)
    var container = jm.view.e_panel || getJsMindPanelEl() || document.getElementById('jsmind_container');
    if (!container) return;

    // Cancel any in-progress animation to avoid "fighting" scroll positions when navigating quickly.
    scrollToNodeAnimToken++;
    if (scrollToNodeAnimRaf) {
        cancelAnimationFrame(scrollToNodeAnimRaf);
        scrollToNodeAnimRaf = null;
    }

    var targetScrollLeft = null;
    var targetScrollTop = null;

    // Prefer jsMind view coordinates (stable under CSS zoom) over DOM rects.
    var node = jm.get_node(nodeId);
    if (node && node._data && node._data.view) {
        var vd = node._data.view;
        if (typeof vd.abs_x === 'number' && typeof vd.abs_y === 'number' &&
            typeof vd.width === 'number' && typeof vd.height === 'number') {
            var zoom = (jm.view && jm.view.actualZoom) || 1;
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
    var token = scrollToNodeAnimToken;

    // Easing function: ease-out-cubic for natural deceleration
    function easeOutCubic(t) {
        return 1 - Math.pow(1 - t, 3);
    }

    function animateScroll(currentTime) {
        if (token !== scrollToNodeAnimToken) return;
        if (!startTime) startTime = currentTime;
        var elapsed = currentTime - startTime;
        var progress = Math.min(elapsed / duration, 1);
        var eased = easeOutCubic(progress);

        container.scrollLeft = startScrollLeft + distanceLeft * eased;
        container.scrollTop = startScrollTop + distanceTop * eased;

        if (progress < 1) {
            scrollToNodeAnimRaf = requestAnimationFrame(animateScroll);
        } else {
            scrollToNodeAnimRaf = null;
        }
    }

    scrollToNodeAnimRaf = requestAnimationFrame(animateScroll);
}

function navigateUp() {
    if (!jm) return;
    var selected = jm.get_selected_node();
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
        jm.select_node(targetId);
        scrollToNode(targetId);
    }
}

function navigateDown() {
    if (!jm) return;
    var selected = jm.get_selected_node();
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
        jm.select_node(targetId);
        scrollToNode(targetId);
    }
}

function navigateLeft() {
    if (!jm) return;
    var selected = jm.get_selected_node();
    if (!selected) return;

    // If at root, go to left-side closest child
    if (selected.isroot) {
        if (selected.children && selected.children.length > 0) {
            var rootElem = document.querySelector('jmnode[nodeid="' + selected.id + '"]');
            if (!rootElem) return;
            var rootRect = rootElem.getBoundingClientRect();
            var rootCenterX = rootRect.left + rootRect.width / 2;
            var rootCenterY = rootRect.top + rootRect.height / 2;

            var leftChildren = [];
            for (var i = 0; i < selected.children.length; i++) {
                var childId = (typeof selected.children[i] === 'string') ? selected.children[i] : selected.children[i].id;
                var childElem = document.querySelector('jmnode[nodeid="' + childId + '"]');
                if (childElem) {
                    var childRect = childElem.getBoundingClientRect();
                    var childCenterX = childRect.left + childRect.width / 2;
                    if (childCenterX < rootCenterX) {
                        var childCenterY = childRect.top + childRect.height / 2;
                        var dist = Math.abs(childCenterY - rootCenterY);
                        leftChildren.push({ id: childId, dist: dist });
                    }
                }
            }

            if (leftChildren.length > 0) {
                leftChildren.sort(function (a, b) { return a.dist - b.dist; });
                jm.select_node(leftChildren[0].id);
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
            jm.select_node(child.id);
            scrollToNode(child.id);
        }
    } else {
        // Right side: left arrow goes to parent
        if (selected.parent) {
            jm.select_node(selected.parent);
            scrollToNode(selected.parent.id);
        }
    }
}

function navigateRight() {
    if (!jm) return;
    var selected = jm.get_selected_node();
    if (!selected) return;

    // If at root, go to right-side closest child
    if (selected.isroot) {
        if (selected.children && selected.children.length > 0) {
            var rootElem = document.querySelector('jmnode[nodeid="' + selected.id + '"]');
            if (!rootElem) return;
            var rootRect = rootElem.getBoundingClientRect();
            var rootCenterX = rootRect.left + rootRect.width / 2;
            var rootCenterY = rootRect.top + rootRect.height / 2;

            var rightChildren = [];
            for (var i = 0; i < selected.children.length; i++) {
                var childId = (typeof selected.children[i] === 'string') ? selected.children[i] : selected.children[i].id;
                var childElem = document.querySelector('jmnode[nodeid="' + childId + '"]');
                if (childElem) {
                    var childRect = childElem.getBoundingClientRect();
                    var childCenterX = childRect.left + childRect.width / 2;
                    if (childCenterX > rootCenterX) {
                        var childCenterY = childRect.top + childRect.height / 2;
                        var dist = Math.abs(childCenterY - rootCenterY);
                        rightChildren.push({ id: childId, dist: dist });
                    }
                }
            }

            if (rightChildren.length > 0) {
                rightChildren.sort(function (a, b) { return a.dist - b.dist; });
                jm.select_node(rightChildren[0].id);
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
            jm.select_node(selected.parent);
            scrollToNode(selected.parent.id);
        }
    } else {
        // Right side: right arrow goes to children
        var child = getClosestChild(selected);
        if (child) {
            jm.select_node(child.id);
            scrollToNode(child.id);
        }
    }
}

// Add a capture-phase listener to intercept ALL keydown events when editing
document.addEventListener('keydown', function (e) {
    if (isEditing) {
        // Intercept ALL events in capture phase
        e.stopPropagation();
        e.stopImmediatePropagation();

        // Shift+Enter: allow new line
        if (e.key === 'Enter' && e.shiftKey) {
            // Let it pass through to create new line
            return;
        }

        // Enter without Shift: exit edit mode
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            exitEditMode();
        }
        // All other keys (including arrows) work normally in the input
        return;
    }
}, true);  // Use capture phase!

// Regular event listener for non-editing mode
document.addEventListener('keydown', function (e) {
    // Skip if editing
    if (isEditing) {
        return;
    }

    // Handle floating node deletion
    if ((e.key === 'Delete' || e.key === 'Backspace') && selectedFloatingNode) {
        if (jm && !jm.get_editable()) return;
        e.preventDefault();
        console.log('Global delete handler - deleting floating node:', selectedFloatingNode.id);
        removeFloatingNode(selectedFloatingNode);
        selectedFloatingNode = null;
        saveHistory();
        scheduleAutoSave();
        return;
    }

    if (e.key === 'ArrowUp') {
        e.preventDefault();
        navigateUp();
        return;
    }

    if (e.key === 'ArrowDown') {
        e.preventDefault();
        navigateDown();
        return;
    }

    if (e.key === 'ArrowLeft') {
        e.preventDefault();
        navigateLeft();
        return;
    }

    if (e.key === 'ArrowRight') {
        e.preventDefault();
        navigateRight();
        return;
    }

    // Toggle collapse/expand for selected node (only if it has children)
    if (matchHotkey(e, hotkeyConfig.toggle_collapse)) {
        if (toggleSelectedNodeCollapse()) {
            e.preventDefault();
            return;
        }
        // No children: do nothing
    }

    // Save hotkey
    if (matchHotkey(e, hotkeyConfig.save)) {
        e.preventDefault();
        saveMap();
        return;
    }

    // Refresh hotkey
    if (matchHotkey(e, hotkeyConfig.refresh)) {
        e.preventDefault();
        refreshMap();
        return;
    }

    // Focus root hotkey
    if (matchHotkey(e, hotkeyConfig.focus_root)) {
        e.preventDefault();
        if (jm) {
            var root = jm.get_root();
            if (root) {
                jm.select_node(root.id);
                scrollToNode(root.id);
            }
        }
        return;
    }

    // Create summary hotkey
    if (matchHotkey(e, hotkeyConfig.create_summary)) {
        e.preventDefault();
        if (jm && !jm.get_editable()) return;
        if (selectedNodes.length >= 2) {
            createSummary();
        } else {
            showToast('Select multiple nodes first (Shift+Click)');
        }
        return;
    }

    // Create boundary hotkey
    if (matchHotkey(e, hotkeyConfig.create_boundary)) {
        e.preventDefault();
        if (jm && !jm.get_editable()) return;
        if (selectedNodes.length >= 1) {
            createBoundary();
        } else {
            showToast('Select at least 1 node (Shift+Click)');
        }
        return;
    }

    // Delete boundary with Delete key
    if (e.key === 'Delete' || e.key === 'Backspace') {
        if (selectedBoundary) {
            e.preventDefault();
            deleteBoundary(selectedBoundary);
            return;
        }
    }

    if ((e.ctrlKey || e.metaKey) && e.key === 'z' && !e.shiftKey) {
        if (jm && !jm.get_editable()) return;
        e.preventDefault();
        undo();
        return;
    }

    if ((e.ctrlKey || e.metaKey) && (e.key === 'y' || (e.key === 'z' && e.shiftKey))) {
        if (jm && !jm.get_editable()) return;
        e.preventDefault();
        redo();
        return;
    }

    if ((e.ctrlKey || e.metaKey) && e.key === 'l') {
        e.preventDefault();
        toggleArrowMode();
        return;
    }

    if (!jm) return;
    var selected = jm.get_selected_node();
    if (!selected) return;

    if (!jm.get_editable() && (e.key === ' ' || e.key === 'Enter' || e.key === 'Tab' || e.key === 'Delete' || e.key === 'Backspace')) {
        return;
    }

    // Space key: Enter edit mode
    if (e.key === ' ' && !isEditing) {
        e.preventDefault();
        enterEditMode(selected);
        return;
    }

    // Enter key behavior depends on whether we're editing
    if (e.key === 'Enter') {
        e.preventDefault();
        if (isEditing) {
            // Exit edit mode
            exitEditMode();
        } else {
            // Add sibling (original behavior)
            addSibling();
        }
        return;
    }

    if (e.key === 'Tab') {
        e.preventDefault();
        addChild();
    } else if (e.key === 'Delete' || e.key === 'Backspace') {
        e.preventDefault();
        if (selected && !selected.isroot) {
            // Check if this is a summary node - use special deletion
            if (selected.data && selected.data.isSummaryNode) {
                deleteSummaryNode(selected.id);
                return;
            }

            // Check if this is a map-linked node and notify backend
            if (selected.data && selected.data.isMapLink && selected.data.sourceMapId) {
                pycmd("delete_map_link:" + JSON.stringify({
                    sourceMapId: selected.data.sourceMapId,
                    linkedNodeId: selected.id
                }));
            }
            jm.remove_node(selected);

            // Re-render braces in case deleted node was part of a summary
            renderSummaryBraces();

            saveHistory();
            scheduleAutoSave();
        }
    }

});

document.addEventListener('blur', function (e) {
    if (e.target.id === 'input-box') {
        saveHistory();
        scheduleAutoSave();
    }
}, true);

// Enter edit mode for a node
function enterEditMode(node) {
    if (!node || isEditing) return;

    isEditing = true;
    editingNodeId = node.id;
    removeCustomContextMenu();

    // Get the node element directly
    var nodeElement = document.querySelector('jmnode[nodeid="' + node.id + '"]');
    if (!nodeElement) {
        isEditing = false;
        editingNodeId = null;
        return;
    }

    // Get current content and convert <br> to newlines
    var currentContent = node.topic;
    var plainText = currentContent.replace(/<br\s*\/?>/gi, '\n');

    // Store original HTML
    var originalHTML = nodeElement.innerHTML;

    // Clear node and prepare for editing
    nodeElement.innerHTML = '';
    nodeElement.style.padding = '0';
    nodeElement.style.display = 'inline-block';

    // Create textarea
    var textarea = document.createElement('textarea');
    textarea.id = 'input-box';
    textarea.value = plainText;

    // Get computed styles from node
    var computedStyle = window.getComputedStyle(nodeElement);

    // Apply styles to textarea
    textarea.style.cssText = `
        box-sizing: border-box;
        margin: 0;
        padding: 8px;
        border: 2px solid #4A90E2;
        border-radius: 4px;
        outline: none;
        background: #fff;
        font-family: ${computedStyle.fontFamily};
        font-size: ${computedStyle.fontSize};
        font-weight: ${computedStyle.fontWeight};
        color: #000;
        line-height: 1.5;
        resize: none;
        overflow: hidden;
        white-space: pre-wrap;
        word-wrap: break-word;
        min-width: 120px;
        min-height: 30px;
        max-width: 500px;
    `;

    // Add textarea to node
    nodeElement.appendChild(textarea);

    // Auto-resize function - REAL-TIME
    function autoResize() {
        if (!textarea || !textarea.parentNode) return;

        // Create hidden div for measurement
        var measureDiv = document.createElement('div');
        measureDiv.style.cssText = `
            position: absolute;
            visibility: hidden;
            white-space: pre-wrap;
            word-wrap: break-word;
            font-family: ${textarea.style.fontFamily};
            font-size: ${textarea.style.fontSize};
            font-weight: ${textarea.style.fontWeight};
            line-height: ${textarea.style.lineHeight};
            padding: ${textarea.style.padding};
            border: ${textarea.style.border};
            box-sizing: border-box;
            max-width: 500px;
        `;
        measureDiv.textContent = textarea.value || 'W';
        document.body.appendChild(measureDiv);

        var width = Math.max(120, Math.min(500, measureDiv.offsetWidth));
        var height = Math.max(30, measureDiv.offsetHeight);
        document.body.removeChild(measureDiv);

        // Apply to both textarea and node
        textarea.style.width = width + 'px';
        textarea.style.height = height + 'px';
        nodeElement.style.width = width + 'px';
        nodeElement.style.height = height + 'px';

        console.log('Resized:', width, 'x', height);
    }

    textarea.focus();
    textarea.select();
    setTimeout(autoResize, 10);

    // Keydown handler
    textarea.addEventListener('keydown', function (e) {
        e.stopPropagation();
        e.stopImmediatePropagation();

        if (matchHotkey(e, hotkeyConfig.bold)) {
            e.preventDefault();
            toggleWrapSelection(textarea, '<b>', '</b>');
            setTimeout(autoResize, 0);
            return false;
        }

        if (matchHotkey(e, hotkeyConfig.italic)) {
            e.preventDefault();
            toggleWrapSelection(textarea, '<i>', '</i>');
            setTimeout(autoResize, 0);
            return false;
        }

        if (matchHotkey(e, hotkeyConfig.inline_code)) {
            e.preventDefault();
            wrapSelectionAsEscapedHtml(textarea, '<code>', '</code>');
            setTimeout(autoResize, 0);
            return false;
        }

        if (matchHotkey(e, hotkeyConfig.code_block)) {
            e.preventDefault();
            wrapSelectionAsEscapedHtml(textarea, '<pre><code>', '</code></pre>');
            setTimeout(autoResize, 0);
            return false;
        }

        // Shift+Enter: insert newline manually
        if (e.key === 'Enter' && e.shiftKey) {
            e.preventDefault();
            var start = textarea.selectionStart;
            var end = textarea.selectionEnd;
            textarea.value = textarea.value.substring(0, start) + '\n' + textarea.value.substring(end);
            textarea.selectionStart = textarea.selectionEnd = start + 1;
            setTimeout(autoResize, 0);
            console.log('Newline inserted');
            return false;
        }

        // Enter: exit
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            exitEditMode();
            return false;
        }

        // Escape: cancel
        if (e.key === 'Escape') {
            e.preventDefault();
            removeCustomContextMenu();
            nodeElement.innerHTML = originalHTML;
            nodeElement.style.width = '';
            nodeElement.style.height = '';
            nodeElement.style.padding = '';
            isEditing = false;
            editingNodeId = null;
            document.getElementById('jsmind_container').focus();
            return false;
        }

        setTimeout(autoResize, 0);
    }, true);

    // Input handler - resize on every input
    textarea.addEventListener('input', function (e) {
        e.stopPropagation();
        autoResize();
    }, true);

    textarea.addEventListener('paste', function () {
        setTimeout(autoResize, 10);
    }, true);

    textarea.addEventListener('mousedown', function (e) {
        e.stopPropagation();
        e.stopImmediatePropagation();
    }, true);

    textarea.addEventListener('click', function (e) {
        e.stopPropagation();
        e.stopImmediatePropagation();
    }, true);

    textarea.addEventListener('contextmenu', function (e) {
        e.preventDefault();
        e.stopPropagation();
        e.stopImmediatePropagation();
        showEditFormattingContextMenu(e.clientX, e.clientY, textarea, function () {
            setTimeout(autoResize, 0);
        });
    }, true);
}

// Exit edit mode
function exitEditMode() {
    if (!isEditing) return;

    removeCustomContextMenu();

    var inputBox = document.getElementById('input-box');
    if (!inputBox || !editingNodeId) {
        isEditing = false;
        editingNodeId = null;
        return;
    }

    var newText = escapeCodeTagsForDisplay(inputBox.value);
    var node = jm.get_node(editingNodeId);

    if (node) {
        var nodeElement = document.querySelector('jmnode[nodeid="' + editingNodeId + '"]');

        if (nodeElement) {
            nodeElement.innerHTML = '';
            nodeElement.style.width = '';
            nodeElement.style.height = '';
            nodeElement.style.padding = '';
            nodeElement.style.whiteSpace = 'normal';
            nodeElement.style.wordWrap = 'break-word';
            nodeElement.style.display = 'inline-block';
            nodeElement.style.maxWidth = '500px';

            if (newText && newText.trim() !== '') {
                // Convert newlines to <br> for display
                var htmlText = newText.replace(/\r?\n/g, '<br>');
                jm.update_node(editingNodeId, htmlText);

                if (jm.view.opts.support_html) {
                    nodeElement.innerHTML = htmlText;
                } else {
                    nodeElement.textContent = htmlText;
                }
            } else {
                if (jm.view.opts.support_html) {
                    nodeElement.innerHTML = node.topic;
                } else {
                    nodeElement.textContent = node.topic;
                }
            }
        }
    }

    isEditing = false;
    editingNodeId = null;

    var container = document.getElementById('jsmind_container');
    if (container) container.focus();

    saveHistory();

    // Auto-save immediately and refresh to fix position
    console.log('Auto-saving after edit...');
    autoSave();

    // Trigger refresh after a brief delay to allow save to complete
    setTimeout(function () {
        console.log('Auto-refreshing to fix node position...');
        refreshMap();
    }, 100);

    setTimeout(renderMath, 300);
}

// Handle clicks during edit mode - capture phase to intercept early
document.addEventListener('mousedown', function (e) {
    if (isEditing && editingNodeId) {
        console.log('Mousedown in edit mode, target:', e.target);

        // Allow interacting with the formatting context menu without leaving edit mode.
        if (isInCustomContextMenu(e.target)) {
            e.stopPropagation();
            e.stopImmediatePropagation();
            return;
        }

        // Get the node element being edited
        var node = jm.get_node(editingNodeId);
        if (node && node._data && node._data.view) {
            var nodeElement = node._data.view.element;
            console.log('Node element:', nodeElement);
            console.log('Contains target?', nodeElement.contains(e.target));

            // Check if click is inside the node element (which contains the input box)
            if (nodeElement && nodeElement.contains(e.target)) {
                // Click inside node/input - allow normal behavior (cursor positioning)
                console.log('Click inside node - allowing');
                e.stopPropagation();
                e.stopImmediatePropagation();
                return;
            }
        }

        // Click outside node - exit edit mode
        console.log('Click outside node - exiting edit mode');
        e.preventDefault();
        e.stopPropagation();
        e.stopImmediatePropagation();
        exitEditMode();
        return;
    }
}, true);

// Also handle click events to prevent any unwanted behavior
document.addEventListener('click', function (e) {
    if (isEditing && editingNodeId) {
        // Allow clicking menu items without exiting edit mode.
        if (isInCustomContextMenu(e.target)) {
            e.stopPropagation();
            e.stopImmediatePropagation();
            return;
        }

        var node = jm.get_node(editingNodeId);
        if (node && node._data && node._data.view) {
            var nodeElement = node._data.view.element;

            // Only allow clicks inside the node element
            if (!nodeElement || !nodeElement.contains(e.target)) {
                e.preventDefault();
                e.stopPropagation();
                e.stopImmediatePropagation();
                return;
            }
        }
        // Click inside - stop propagation
        e.stopPropagation();
        e.stopImmediatePropagation();
        return;
    }
}, true);

// Regular click handler for non-editing mode
document.addEventListener('click', function (e) {
    // Don't interfere if editing
    if (isEditing) {
        return;
    }

    var container = document.getElementById('jsmind_container');
    if (container) container.focus();

    if (!e.ctrlKey && !e.shiftKey) {
        clearSelection();
    }
});

// While editing a node, right-click anywhere should show formatting options (instead of node actions).
document.addEventListener('contextmenu', function (e) {
    if (!isEditing || !editingNodeId) return;

    var textarea = document.getElementById('input-box');
    if (!textarea) return;

    e.preventDefault();
    e.stopPropagation();
    e.stopImmediatePropagation();
    showEditFormattingContextMenu(e.clientX, e.clientY, textarea, function () {
        // Auto-resize is defined inside enterEditMode; trigger input to recalc size.
        textarea.dispatchEvent(new Event('input'));
    });
}, true);

// --- Card Linking Features ---

function toggleSelectedNodeCollapse() {
    if (!jm) return false;

    var selected = jm.get_selected_node();
    if (!selected) return false;

    if (!selected.children || selected.children.length === 0) {
        return false;
    }

    if (typeof jm.toggle_node === 'function') {
        jm.toggle_node(selected.id);
        renderSummaryBraces();
        renderBoundaries();
        return true;
    }

    // Fallback for older builds (should not be needed with bundled jsMind).
    if (selected.expanded && typeof jm.collapse_node === 'function') {
        jm.collapse_node(selected.id);
        renderSummaryBraces();
        renderBoundaries();
        return true;
    }
    if (!selected.expanded && typeof jm.expand_node === 'function') {
        jm.expand_node(selected.id);
        renderSummaryBraces();
        renderBoundaries();
        return true;
    }

    return false;
}

// Context Menu for Jumping to Card and Map Linking
document.addEventListener('contextmenu', function (e) {
    var target = e.target;
    // Find if we clicked on a node
    var nodeElement = target.closest('jmnode');
    if (nodeElement) {
        e.preventDefault();

        // Check if we have multiple nodes selected
        if (selectedNodes.length > 1) {
            showMultiSelectionContextMenu(e.clientX, e.clientY);
            return;
        }

        var nodeId = nodeElement.getAttribute('nodeid');
        var node = jm.get_node(nodeId);

        // Gather node properties
        var noteId = (node.data && node.data.noteId) || node.noteId;
        var isRoot = node.isroot;
        var isMapLink = node.data && node.data.isMapLink;
        var sourceMapId = node.data && node.data.sourceMapId;
        var linkedMaps = isRoot && node.data && node.data.linkedMaps;

        showNodeContextMenu(e.clientX, e.clientY, {
            nodeId: nodeId,
            noteId: noteId,
            isRoot: isRoot,
            isMapLink: isMapLink,
            sourceMapId: sourceMapId,
            linkedMaps: linkedMaps || []
        });

    }
});

// Pending callback for map selection
var pendingMapLinkCallback = null;

function showNodeContextMenu(x, y, nodeInfo) {
    // Remove existing menu
    var existing = document.getElementById('custom-context-menu');
    if (existing) existing.remove();

    var menu = document.createElement('div');
    menu.id = 'custom-context-menu';
    menu.style.cssText = `
        position: fixed;
        left: ${x}px;
        top: ${y}px;
        background: white;
        border: 1px solid #ccc;
        box-shadow: 2px 2px 5px rgba(0,0,0,0.2);
        z-index: 10000;
        padding: 5px 0;
        border-radius: 4px;
        min-width: 180px;
    `;

    var hasItems = false;

    // Helper function to create menu item
    function createMenuItem(text, onClick) {
        var item = document.createElement('div');
        item.innerText = text;
        item.style.cssText = `
            padding: 8px 15px;
            cursor: pointer;
            font-family: sans-serif;
            font-size: 14px;
            color: #333;
        `;
        item.onmouseover = function () { this.style.background = '#f0f0f0'; };
        item.onmouseout = function () { this.style.background = 'white'; };
        item.onclick = function () {
            onClick();
            menu.remove();
        };
        return item;
    }

    // 1. If node has a linked card, show "Jump to Card"
    if (nodeInfo.noteId) {
        menu.appendChild(createMenuItem("Jump to Card", function () {
            pycmd("jump_to_card:" + nodeInfo.noteId);
        }));
        hasItems = true;
    }

    // 2. If this is a map-linked node, show "Jump to Source Map"
    if (nodeInfo.isMapLink && nodeInfo.sourceMapId) {
        menu.appendChild(createMenuItem("Jump to Source Mind Map", function () {
            pycmd("jump_to_map:" + JSON.stringify({
                targetMapId: nodeInfo.sourceMapId,
                focusNodeId: "root"
            }));
        }));
        hasItems = true;
    }

    // 3. If this is root node with linkedMaps, show submenu for jumping
    if (nodeInfo.isRoot && nodeInfo.linkedMaps && nodeInfo.linkedMaps.length > 0) {
        // Add separator if there are other items
        if (hasItems) {
            var sep = document.createElement('div');
            sep.style.cssText = 'height: 1px; background: #eee; margin: 4px 0;';
            menu.appendChild(sep);
        }

        // Add header for linked maps
        var header = document.createElement('div');
        header.innerText = "Jump to Linked Maps:";
        header.style.cssText = `
            padding: 4px 15px;
            font-family: sans-serif;
            font-size: 12px;
            color: #888;
        `;
        menu.appendChild(header);

        nodeInfo.linkedMaps.forEach(function (link) {
            var displayName = link.targetMapTitle || ("Map " + link.targetMapId);
            menu.appendChild(createMenuItem("  → " + displayName, function () {
                pycmd("jump_to_map:" + JSON.stringify({
                    targetMapId: link.targetMapId,
                    focusNodeId: link.linkedNodeId
                }));
            }));
        });
        hasItems = true;
    }

    // 4. If this is root node (not in read-only mode), show "Link to Other Mind Map"
    if (nodeInfo.isRoot && jm && jm.get_editable()) {
        // Add separator if there are other items
        if (hasItems) {
            var sep = document.createElement('div');
            sep.style.cssText = 'height: 1px; background: #eee; margin: 4px 0;';
            menu.appendChild(sep);
        }

        menu.appendChild(createMenuItem("Link to Other Mind Map", function () {
            // Request editable maps list from Python
            pycmd("get_editable_maps");
        }));
        hasItems = true;
    }

    // Only show menu if there are items
    if (hasItems) {
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
}

// Called by Python when editable maps list is received
function onEditableMapsReceived(mapsList) {
    if (!mapsList || mapsList.length === 0) {
        showToast("No other editable mind maps available");
        return;
    }

    showMapSelectionDialog(mapsList);
}

// Show dialog for selecting target map (with toggle for linked maps)
function showMapSelectionDialog(mapsList) {
    // Remove existing dialog
    var existing = document.getElementById('map-select-dialog');
    if (existing) existing.remove();

    var overlay = document.createElement('div');
    overlay.id = 'map-select-dialog';
    overlay.style.cssText = `
        position: fixed;
        top: 0;
        left: 0;
        right: 0;
        bottom: 0;
        background: rgba(0,0,0,0.5);
        z-index: 10001;
        display: flex;
        align-items: center;
        justify-content: center;
    `;

    var dialog = document.createElement('div');
    dialog.style.cssText = `
        background: white;
        border-radius: 8px;
        padding: 20px;
        min-width: 300px;
        max-width: 400px;
        max-height: 80vh;
        box-shadow: 0 4px 20px rgba(0,0,0,0.3);
    `;

    var title = document.createElement('h3');
    title.innerText = "Link to Mind Map";
    title.style.cssText = `
        margin: 0 0 10px 0;
        font-family: sans-serif;
        font-size: 16px;
        color: #333;
    `;
    dialog.appendChild(title);

    var hint = document.createElement('div');
    hint.innerText = "✓ = Linked (click to unlink)";
    hint.style.cssText = `
        margin-bottom: 10px;
        font-family: sans-serif;
        font-size: 12px;
        color: #666;
    `;
    dialog.appendChild(hint);

    var list = document.createElement('div');
    list.style.cssText = `
        max-height: 300px;
        overflow-y: auto;
        border: 1px solid #eee;
        border-radius: 4px;
    `;

    mapsList.forEach(function (map) {
        var item = document.createElement('div');
        var checkmark = map.isLinked ? '✓ ' : '';
        item.innerText = checkmark + map.title;

        var bgColor = map.isLinked ? '#e8f5e9' : 'white';
        var hoverColor = map.isLinked ? '#c8e6c9' : '#e3f2fd';

        item.style.cssText = `
            padding: 12px 15px;
            cursor: pointer;
            font-family: sans-serif;
            font-size: 14px;
            color: ${map.isLinked ? '#2e7d32' : '#333'};
            border-bottom: 1px solid #f0f0f0;
            background: ${bgColor};
            font-weight: ${map.isLinked ? 'bold' : 'normal'};
        `;
        item.onmouseover = function () { this.style.background = hoverColor; };
        item.onmouseout = function () { this.style.background = bgColor; };
        item.onclick = function () {
            overlay.remove();
            if (map.isLinked) {
                // Unlink
                pycmd("unlink_map:" + JSON.stringify({
                    targetMapId: map.id
                }));
            } else {
                // Create link
                pycmd("create_map_link:" + JSON.stringify({
                    targetMapId: map.id
                }));
            }
        };
        list.appendChild(item);
    });

    dialog.appendChild(list);

    var cancelBtn = document.createElement('button');
    cancelBtn.innerText = "Cancel";
    cancelBtn.style.cssText = `
        margin-top: 15px;
        padding: 8px 20px;
        background: #f5f5f5;
        border: 1px solid #ddd;
        border-radius: 4px;
        cursor: pointer;
        font-size: 14px;
    `;
    cancelBtn.onclick = function () { overlay.remove(); };
    dialog.appendChild(cancelBtn);

    overlay.appendChild(dialog);
    document.body.appendChild(overlay);

    // Close on click outside dialog
    overlay.onclick = function (e) {
        if (e.target === overlay) overlay.remove();
    };
}

// Called by Python when map link is successfully created
function onMapLinkCreated(targetMapId, linkedNodeId) {
    console.log("Map link created: " + targetMapId + " -> " + linkedNodeId);
    // Refresh node markers
    setTimeout(markLinkedNodes, 300);
}


// Focus on a specific node and scroll it into view
function focusNode(nodeId) {
    if (!jm || !nodeId) {
        console.log('Cannot focus node: jm not initialized or no nodeId');
        return;
    }

    try {
        console.log('Focusing on node:', nodeId);

        // Select the node
        jm.select_node(nodeId);

        // Get the node element
        var nodeElement = document.querySelector('jmnode[nodeid="' + nodeId + '"]');
        if (!nodeElement) {
            console.log('Node element not found:', nodeId);
            return;
        }

        // Scroll the node into view with smooth animation
        nodeElement.scrollIntoView({
            behavior: 'smooth',
            block: 'center',
            inline: 'center'
        });

        console.log('Node focused and scrolled into view');
    } catch (e) {
        console.error('Error focusing node:', e);
    }
}

document.addEventListener('paste', function (e) {
    if (isEditing) return;
    if (jm && !jm.get_editable()) return;

    var selected = jm.get_selected_node();
    if (selected) {
        e.preventDefault();

        var text = (e.clipboardData || window.clipboardData).getData('text');

        if (text && text.trim() !== "") {

            var newId = 'node_' + Date.now();

            jm.add_node(selected, newId, text);

            jm.select_node(newId);

            if (typeof window.saveHistory === 'function') {
                window.saveHistory();
                scheduleAutoSave();
            }

            if (typeof renderMath === 'function') {
                setTimeout(renderMath, 100);
            }
        }
    }
});

document.addEventListener('copy', function (e) {
    if (isEditing) return;

    var selected = jm.get_selected_node();
    if (selected) {
        var text = selected.topic;

        if (text) {
            e.preventDefault();

            var plainText = text.replace(/<br\s*\/?>/gi, '\n').replace(/<[^>]+>/g, '');

            if (e.clipboardData) {
                e.clipboardData.setData('text/plain', plainText);
            } else if (window.clipboardData) {
                window.clipboardData.setData('Text', plainText);
            }
        }
    }
});

function toggleReadOnly() {
    if (!jm) return;
    var checkbox = document.getElementById('readonly_toggle');
    if (checkbox.checked) {
        jm.disable_edit();
    } else {
        jm.enable_edit();
    }
}
