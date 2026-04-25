/**
 * jsMind draggable plugin options.
 */
(function ($w) {
    'use strict';
    var parts = $w.jsMindDraggableParts = $w.jsMindDraggableParts || {};

    parts.options = {
        line_width: 5,
        line_color: 'rgba(99, 102, 241, 0.6)',
        lookup_delay: 100,
        lookup_interval: 30,
        scrolling_trigger_width: 20,
        scrolling_step_length: 10,
        detection_radius_multiplier: 2.5,
        highlight_color: 'rgba(99, 102, 241, 0.15)',
        highlight_border: '3px solid #6366f1'
    };

    if (parts.tryInstall) {
        parts.tryInstall();
    }
})(window);
