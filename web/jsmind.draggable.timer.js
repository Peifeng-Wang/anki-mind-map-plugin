/**
 * jsMind draggable plugin timer and state helpers.
 */
(function ($w) {
    'use strict';
    var parts = $w.jsMindDraggableParts = $w.jsMindDraggableParts || {};

    parts.timer = {
        apply: function (proto) {
            proto._clear_lookup_timer = function (clear_lines, reset_handle) {
                if (this.hlookup_delay != 0) {
                    $w.clearTimeout(this.hlookup_delay);
                    if (reset_handle) {
                        this.hlookup_delay = 0;
                    }
                    if (clear_lines) {
                        this._clear_lines();
                    }
                }
                if (this.hlookup_timer != 0) {
                    $w.clearInterval(this.hlookup_timer);
                    if (reset_handle) {
                        this.hlookup_timer = 0;
                    }
                    if (clear_lines) {
                        this._clear_lines();
                    }
                }
            };

            proto._reset_drag_state = function () {
                this.view_panel_rect = null;
                this.moved = false;
                this.capture = false;
            };

            proto._reset_node_state = function () {
                this.active_node = null;
                this.target_node = null;
                this.target_direct = null;
            };
        }
    };

    if (parts.tryInstall) {
        parts.tryInstall();
    }
})(window);
