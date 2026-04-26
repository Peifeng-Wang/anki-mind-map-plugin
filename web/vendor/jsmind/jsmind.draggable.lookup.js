/**
 * jsMind draggable plugin target lookup.
 */
(function ($w) {
    'use strict';
    var parts = $w.jsMindDraggableParts = $w.jsMindDraggableParts || {};

    parts.lookup = {
        apply: function (proto, env) {
            var jsMind = env.jsMind;
            var options = env.options;

            proto._lookup_close_node = function () {
                var root = this.jm.get_root();
                var root_location = root.get_location();
                var root_size = root.get_size();
                var root_x = root_location.x + root_size.w / 2;

                var sw = this.shadow_w;
                var sh = this.shadow_h;
                var sx = this.shadow.offsetLeft;
                var sy = this.shadow.offsetTop;
                var shadow_center_x = sx + sw / 2;
                var shadow_center_y = sy + sh / 2;

                var direct = shadow_center_x >= root_x ?
                    jsMind.direction.right : jsMind.direction.left;
                var nodes = this.jm.mind.nodes;
                var node = null;
                var layout = this.jm.layout;
                var min_distance = Number.MAX_VALUE;
                var closest_node = null;
                var closest_p = null;
                var shadow_p = null;

                for (var nodeid in nodes) {
                    var np, sp;
                    node = nodes[nodeid];
                    if (node.isroot || node.direction == direct) {
                        if (node.id == this.active_node.id) {
                            continue;
                        }
                        if (!layout.is_visible(node)) {
                            continue;
                        }
                        var ns = node.get_size();
                        var nl = node.get_location();
                        var node_center_y = nl.y + ns.h / 2;

                        var dx, dy;

                        if (direct == jsMind.direction.right) {
                            dx = shadow_center_x - (nl.x + ns.w);
                            dy = shadow_center_y - node_center_y;
                            np = { x: nl.x + ns.w - options.line_width, y: node_center_y };
                            sp = { x: sx + options.line_width, y: shadow_center_y };
                        } else {
                            dx = nl.x - shadow_center_x;
                            dy = shadow_center_y - node_center_y;
                            np = { x: nl.x + options.line_width, y: node_center_y };
                            sp = { x: sx + sw - options.line_width, y: shadow_center_y };
                        }

                        var distance = Math.sqrt(dx * dx + dy * dy);

                        var effective_radius = (ns.w + ns.h) / 2 * options.detection_radius_multiplier;
                        var weight_factor = 1.0;
                        if (distance < effective_radius) {
                            weight_factor = 0.5;
                        }
                        distance = distance * weight_factor;

                        if (distance < min_distance) {
                            closest_node = node;
                            closest_p = np;
                            shadow_p = sp;
                            min_distance = distance;
                        }
                    }
                }

                var result_node = null;
                if (!!closest_node) {
                    var target_node = closest_node;

                    if (!closest_node.isroot) {
                        var n_loc = closest_node.get_location();
                        var n_size = closest_node.get_size();
                        var is_sibling_intent = false;
                        var indent_threshold = 20;

                        if (direct == jsMind.direction.right) {
                            if (shadow_center_x < n_loc.x + n_size.w + indent_threshold) {
                                is_sibling_intent = true;
                            }
                        } else {
                            if (shadow_center_x > n_loc.x - indent_threshold) {
                                is_sibling_intent = true;
                            }
                        }

                        if (is_sibling_intent) {
                            target_node = closest_node.parent;
                            var p_loc = target_node.get_location();
                            var p_size = target_node.get_size();
                            if (direct == jsMind.direction.right) {
                                closest_p = { x: p_loc.x + p_size.w - options.line_width, y: p_loc.y + p_size.h / 2 };
                            } else {
                                closest_p = { x: p_loc.x + options.line_width, y: p_loc.y + p_size.h / 2 };
                            }
                        }
                    }

                    result_node = {
                        node: target_node,
                        direction: direct,
                        sp: shadow_p,
                        np: closest_p
                    };
                }
                return result_node;
            };

            proto.lookup_close_node = function () {
                var node_data = this._lookup_close_node();
                if (!!node_data) {
                    this._magnet_shadow(node_data);
                    this.target_node = node_data.node;
                    this.target_direct = node_data.direction;
                }
            };
        }
    };

    if (parts.tryInstall) {
        parts.tryInstall();
    }
})(window);
