/**
 * jsMind draggable plugin shadow node helpers.
 */
(function ($w) {
    'use strict';
    var parts = $w.jsMindDraggableParts = $w.jsMindDraggableParts || {};

    parts.shadow = {
        apply: function (proto, env) {
            var $d = env.document;

            proto._create_shadow = function () {
                var s = $d.createElement('jmnode');
                s.style.visibility = 'hidden';
                s.style.zIndex = '3';
                s.style.cursor = 'move';
                s.style.opacity = '0.8';
                s.style.transition = 'opacity 0.15s ease';
                s.style.boxShadow = '0 8px 32px rgba(0, 0, 0, 0.3)';
                this.shadow = s;
                this.highlighted_element = null;
            };

            proto.reset_shadow = function (el) {
                var s = this.shadow.style;
                this.shadow.innerHTML = el.innerHTML;
                s.left = el.style.left;
                s.top = el.style.top;
                s.width = el.style.width;
                s.height = el.style.height;
                s.backgroundImage = el.style.backgroundImage;
                s.backgroundSize = el.style.backgroundSize;
                s.transform = el.style.transform;
                this.shadow_w = this.shadow.clientWidth;
                this.shadow_h = this.shadow.clientHeight;
            };

            proto.show_shadow = function () {
                if (!this.moved) {
                    this.shadow.style.visibility = 'visible';
                }
            };

            proto.hide_shadow = function () {
                this.shadow.style.visibility = 'hidden';
            };

            proto._magnet_shadow = function (node) {
                if (!!node) {
                    this._clear_lines();
                    this._canvas_lineto(node.sp.x, node.sp.y, node.np.x, node.np.y);
                    this._highlight_target_node(node.node);
                } else {
                    this._clear_highlight();
                }
            };
        }
    };

    if (parts.tryInstall) {
        parts.tryInstall();
    }
})(window);
