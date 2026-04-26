/**
 * jsMind draggable plugin core registration.
 */
(function ($w) {
    'use strict';
    var $d = $w.document;
    var __name__ = 'jsMind';
    var parts = $w.jsMindDraggableParts = $w.jsMindDraggableParts || {};
    var required = [
        'options',
        'canvas',
        'shadow',
        'highlight',
        'timer',
        'lookup',
        'events',
        'autoscroll',
        'move'
    ];

    function modulesReady() {
        for (var i = 0; i < required.length; i++) {
            if (!parts[required[i]]) {
                return false;
            }
        }
        return true;
    }

    parts.install = function (jsMind) {
        if (!jsMind) { return false; }
        if (typeof jsMind.draggable != 'undefined') { return true; }
        if (!modulesReady()) { return false; }

        var jdom = jsMind.util.dom;
        var clear_selection = 'getSelection' in $w ? function () {
            $w.getSelection().removeAllRanges();
        } : function () {
            $d.selection.empty();
        };
        var env = {
            window: $w,
            document: $d,
            jsMind: jsMind,
            jdom: jdom,
            options: parts.options,
            clearSelection: clear_selection
        };

        jsMind.draggable = function (jm) {
            this.jm = jm;
            this.e_canvas = null;
            this.canvas_ctx = null;
            this.shadow = null;
            this.shadow_w = 0;
            this.shadow_h = 0;
            this.active_node = null;
            this.target_node = null;
            this.target_direct = null;
            this.client_w = 0;
            this.client_h = 0;
            this.offset_x = 0;
            this.offset_y = 0;
            this.hlookup_delay = 0;
            this.hlookup_timer = 0;
            this.capture = false;
            this.moved = false;
            this.view_panel = jm.view.e_panel;
            this.view_panel_rect = null;
        };

        jsMind.draggable.prototype = {
            init: function () {
                this._create_canvas();
                this._create_shadow();
                this._event_bind();
            },

            jm_event_handle: function (type, data) {
                if (type === jsMind.event_type.resize) {
                    this.resize();
                }
            }
        };

        parts.canvas.apply(jsMind.draggable.prototype, env);
        parts.shadow.apply(jsMind.draggable.prototype, env);
        parts.highlight.apply(jsMind.draggable.prototype, env);
        parts.timer.apply(jsMind.draggable.prototype, env);
        parts.lookup.apply(jsMind.draggable.prototype, env);
        parts.autoscroll.apply(jsMind.draggable.prototype, env);
        parts.move.apply(jsMind.draggable.prototype, env);
        parts.events.apply(jsMind.draggable.prototype, env);

        var draggable_plugin = new jsMind.plugin('draggable', function (jm) {
            var jd = new jsMind.draggable(jm);
            jd.init();
            jm.add_event_listener(function (type, data) {
                jd.jm_event_handle.call(jd, type, data);
            });
        });

        jsMind.register_plugin(draggable_plugin);
        return true;
    };

    parts.tryInstall = function () {
        return parts.install($w[__name__]);
    };

    parts.tryInstall();
})(window);
