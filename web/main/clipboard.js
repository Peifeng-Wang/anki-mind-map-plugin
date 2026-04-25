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
