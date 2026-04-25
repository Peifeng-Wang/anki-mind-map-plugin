/**
 * jsMind draggable plugin node move handling.
 */
(function ($w) {
    'use strict';
    var parts = $w.jsMindDraggableParts = $w.jsMindDraggableParts || {};

    parts.move = {
        apply: function (proto, env) {
            var jsMind = env.jsMind;

            proto.move_node = function (src_node, target_node, target_direct) {
                var shadow_h = this.shadow.offsetTop;
                if (!!target_node && !!src_node && !jsMind.node.inherited(src_node, target_node)) {
                    var sibling_nodes = target_node.children;
                    var sc = sibling_nodes.length;
                    var node = null;
                    var delta_y = Number.MAX_VALUE;
                    var node_before = null;
                    var beforeid = '_last_';
                    while (sc--) {
                        node = sibling_nodes[sc];
                        if (node.direction == target_direct && node.id != src_node.id) {
                            var dy = node.get_location().y - shadow_h;
                            if (dy > 0 && dy < delta_y) {
                                delta_y = dy;
                                node_before = node;
                                beforeid = '_first_';
                            }
                        }
                    }
                    if (!!node_before) { beforeid = node_before.id; }
                    this.jm.move_node(src_node.id, beforeid, target_node.id, target_direct);
                }
                this._reset_node_state();
            };
        }
    };

    if (parts.tryInstall) {
        parts.tryInstall();
    }
})(window);
