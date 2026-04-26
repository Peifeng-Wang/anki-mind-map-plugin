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

        MM.state.jm = new jsMind({
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

        MM.state.jm.add_event_listener(function (type, data) {
            if (type === 3) {
                console.log('Detected change...');
                window.saveHistory();
                scheduleAutoSave();
            }
        });

        MM.state.jm.show(data);
        saveHistory();
        migrateLegacyCustomNodesIntoJsMindNodes();

        if (data.data && data.data.id) {
            MM.state.jm.select_node(data.data.id);
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
            MM.state.braceColor = braceColorFromPython;
        }

        // Load floating nodes if they exist
        if (data.floatingNodes && Array.isArray(data.floatingNodes)) {
            data.floatingNodes.forEach(function (nodeData) {
                loadFloatingNode(nodeData);
            });
        }

        // Load summary braces if they exist
        if (data.summaryBraces && Array.isArray(data.summaryBraces)) {
            MM.state.summaryBraces = data.summaryBraces;
            setTimeout(function () {
                renderSummaryBraces();
                markSummaryNodes();
            }, 200);
        }

        // Load boundaries if they exist
        if (data.boundaries && Array.isArray(data.boundaries)) {
            MM.state.boundaries = data.boundaries;
            // Load boundary color from config if available
            if (typeof boundaryColorFromPython !== 'undefined') {
                MM.state.boundaryColor = boundaryColorFromPython;
            }
            setTimeout(function () {
                renderBoundaries();
            }, 250);
        }

        function scheduleOverlayRerender() {
            if (MM.state.overlayRenderTimer) {
                clearTimeout(MM.state.overlayRenderTimer);
                MM.state.overlayRenderTimer = null;
            }
            if (MM.state.overlayRenderRaf) {
                cancelAnimationFrame(MM.state.overlayRenderRaf);
                MM.state.overlayRenderRaf = null;
            }
            if (MM.state.overlayRenderTimer2) {
                clearTimeout(MM.state.overlayRenderTimer2);
                MM.state.overlayRenderTimer2 = null;
            }
            if (MM.state.overlayRenderRaf2) {
                cancelAnimationFrame(MM.state.overlayRenderRaf2);
                MM.state.overlayRenderRaf2 = null;
            }

            // Defer to the next frame so zoom/style updates have settled.
            MM.state.overlayRenderTimer = setTimeout(function () {
                MM.state.overlayRenderRaf = requestAnimationFrame(function () {
                    renderSummaryBraces();
                    renderBoundaries();
                });
            }, 0);

            // Qt WebEngine can apply style.zoom asynchronously at extreme values; do a second pass after a short delay.
            MM.state.overlayRenderTimer2 = setTimeout(function () {
                MM.state.overlayRenderRaf2 = requestAnimationFrame(function () {
                    renderSummaryBraces();
                    renderBoundaries();
                });
            }, 80);
        }

        // Re-render braces when layout changes
        MM.state.jm.add_event_listener(function (type, data) {
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
