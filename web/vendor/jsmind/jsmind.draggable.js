/**
 * Compatibility loader for the split jsMind draggable plugin modules.
 * Keep this file as the public browser entry; Anki inlines the modules
 * directly from mindmap_editor.py to avoid relying on relative script URLs.
 */
(function () {
    var scripts = [
        'jsmind.draggable.options.js',
        'jsmind.draggable.canvas.js',
        'jsmind.draggable.highlight.js',
        'jsmind.draggable.shadow.js',
        'jsmind.draggable.timer.js',
        'jsmind.draggable.lookup.js',
        'jsmind.draggable.autoscroll.js',
        'jsmind.draggable.move.js',
        'jsmind.draggable.events.js',
        'jsmind.draggable.core.js'
    ];

    if (typeof document === 'undefined' || typeof document.write !== 'function') {
        return;
    }

    scripts.forEach(function (src) {
        document.write('<scr' + 'ipt src="' + src + '"></scr' + 'ipt>');
    });
}());
