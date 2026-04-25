/**
 * jsMind draggable plugin target highlighting.
 */
(function ($w) {
    'use strict';
    var parts = $w.jsMindDraggableParts = $w.jsMindDraggableParts || {};

    parts.highlight = {
        apply: function (proto, env) {
            var options = env.options;

            proto._highlight_target_node = function (node) {
                if (node && node._data && node._data.view && node._data.view.element) {
                    var el = node._data.view.element;
                    if (el === this.highlighted_element) {
                        return;
                    }
                    this._clear_highlight();
                    el.style.backgroundColor = options.highlight_color;
                    el.style.border = options.highlight_border;
                    el.style.transform = 'scale(1.05)';
                    el.style.transition = 'all 0.2s cubic-bezier(0.4, 0, 0.2, 1)';
                    this.highlighted_element = el;
                } else {
                    this._clear_highlight();
                }
            };

            proto._clear_highlight = function () {
                if (this.highlighted_element) {
                    this.highlighted_element.style.backgroundColor = '';
                    this.highlighted_element.style.border = '';
                    this.highlighted_element.style.transform = '';
                    this.highlighted_element.style.transition = '';
                    this.highlighted_element = null;
                }
            };
        }
    };

    if (parts.tryInstall) {
        parts.tryInstall();
    }
})(window);
