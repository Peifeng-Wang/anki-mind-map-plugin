(function () {
    var scripts = [
        'main/state.js',
        'main/jsmind_dom.js',
        'main/hotkeys.js',
        'main/ui_feedback.js',
        'main/text_formatting.js',
        'main/app_events.js',
        'main/floating_nodes.js',
        'main/persistence.js',
        'main/mathjax.js',
        'main/node_commands.js',
        'main/persistence_reload.js',
        'main/selection.js',
        'main/summary_braces.js',
        'main/boundaries.js',
        'main/navigation.js',
        'main/node_editor.js',
        'main/backend_links.js',
        'main/clipboard.js',
        'main/app_events_tail.js'
    ];

    if (typeof document === 'undefined' || typeof document.write !== 'function') {
        return;
    }

    scripts.forEach(function (src) {
        document.write('<scr' + 'ipt src="' + src + '"></scr' + 'ipt>');
    });
}());
