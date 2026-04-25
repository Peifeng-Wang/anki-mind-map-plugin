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

