/**
 * @license BSD
 * @copyright 2014-2023 hizzgdev@163.com
 * 
 * Project Home:
 *   https://github.com/hizzgdev/jsmind/
 */

(function ($w) {
    'use strict';
    var $d = $w.document;
    var __name__ = 'jsMind';
    var jsMind = $w[__name__];
    if (!jsMind) { return; }
    if (typeof jsMind.draggable != 'undefined') { return; }

    var jdom = jsMind.util.dom;
    var clear_selection = 'getSelection' in $w ? function () {
        $w.getSelection().removeAllRanges();
    } : function () {
        $d.selection.empty();
    };

    var options = {
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
        this.view_panel_rect = null
    };

    jsMind.draggable.prototype = {
        init: function () {
            this._create_canvas();
            this._create_shadow();
            this._event_bind();
        },

        resize: function () {
            this.jm.view.e_nodes.appendChild(this.shadow);
            this.e_canvas.width = this.jm.view.size.w;
            this.e_canvas.height = this.jm.view.size.h;
            this._set_canvas_line_style();
        },

        _create_canvas: function () {
            var c = $d.createElement('canvas');
            this.jm.view.e_panel.appendChild(c);
            var ctx = c.getContext('2d');
            this.e_canvas = c;
            this.canvas_ctx = ctx;
            this._set_canvas_line_style();
        },

        _create_shadow: function () {
            var s = $d.createElement('jmnode');
            s.style.visibility = 'hidden';
            s.style.zIndex = '3';
            s.style.cursor = 'move';
            s.style.opacity = '0.8';
            s.style.transition = 'opacity 0.15s ease';
            s.style.boxShadow = '0 8px 32px rgba(0, 0, 0, 0.3)';
            this.shadow = s;
            this.highlighted_element = null;
        },

        reset_shadow: function (el) {
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

        },

        show_shadow: function () {
            if (!this.moved) {
                this.shadow.style.visibility = 'visible';
            }
        },

        hide_shadow: function () {
            this.shadow.style.visibility = 'hidden';
        },

        _magnet_shadow: function (node) {
            if (!!node) {
                this._clear_lines();
                this._canvas_lineto(node.sp.x, node.sp.y, node.np.x, node.np.y);
                this._highlight_target_node(node.node);
            } else {
                this._clear_highlight();
            }
        },

        _highlight_target_node: function (node) {
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
        },

        _clear_highlight: function () {
            if (this.highlighted_element) {
                this.highlighted_element.style.backgroundColor = '';
                this.highlighted_element.style.border = '';
                this.highlighted_element.style.transform = '';
                this.highlighted_element.style.transition = '';
                this.highlighted_element = null;
            }
        },

        _clear_lines: function () {
            this.canvas_ctx.clearRect(0, 0, this.jm.view.size.w, this.jm.view.size.h);
        },

        _canvas_lineto: function (x1, y1, x2, y2) {
            this.canvas_ctx.beginPath();
            this.canvas_ctx.moveTo(x1, y1);
            this.canvas_ctx.lineTo(x2, y2);
            this.canvas_ctx.stroke();
        },

        _set_canvas_line_style: function () {
            this.canvas_ctx.lineWidth = options.line_width;
            this.canvas_ctx.strokeStyle = options.line_color;
            this.canvas_ctx.lineCap = 'round';
        },

        _get_event_client_point: function (e) {
            return {
                x: e.clientX || e.touches[0].clientX,
                y: e.clientY || e.touches[0].clientY
            };
        },

        _clear_lookup_timer: function (clear_lines, reset_handle) {
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
        },

        _reset_drag_state: function () {
            this.view_panel_rect = null
            this.moved = false;
            this.capture = false;
        },

        _reset_node_state: function () {
            this.active_node = null;
            this.target_node = null;
            this.target_direct = null;
        },

        _lookup_close_node: function () {
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
        },
        
        lookup_close_node: function () {
            var node_data = this._lookup_close_node();
            if (!!node_data) {
                this._magnet_shadow(node_data);
                this.target_node = node_data.node;
                this.target_direct = node_data.direction;
            }
        },

        _event_bind: function () {
            var jd = this;
            var container = this.jm.view.container;
            jdom.add_event(container, 'mousedown', function (e) {
                var evt = e || event;
                jd.dragstart.call(jd, evt);
            });
            jdom.add_event(container, 'mousemove', function (e) {
                var evt = e || event;
                jd.drag.call(jd, evt);
            });
            jdom.add_event(container, 'mouseup', function (e) {
                var evt = e || event;
                jd.dragend.call(jd, evt);
            });
            jdom.add_event(container, 'touchstart', function (e) {
                var evt = e || event;
                jd.dragstart.call(jd, evt);
            });
            jdom.add_event(container, 'touchmove', function (e) {
                var evt = e || event;
                jd.drag.call(jd, evt);
            });
            jdom.add_event(container, 'touchend', function (e) {
                var evt = e || event;
                jd.dragend.call(jd, evt);
            });
        },

        dragstart: function (e) {
            if (!this.jm.get_editable()) { return; }
            if (this.capture) { return; }
            this.active_node = null;

            var jview = this.jm.view;
            var el = e.target || event.srcElement;
            if (el.tagName.toLowerCase() != 'jmnode') { return; }
            if (jview.get_draggable_canvas()) { jview.disable_draggable_canvas() }
            var nodeid = jview.get_binded_nodeid(el);
            if (!!nodeid) {
                var node = this.jm.get_node(nodeid);
                if (!node.isroot) {
                    this.reset_shadow(el);
                    this.view_panel_rect = this.view_panel.getBoundingClientRect()
                    this.active_node = node;
                    var point = this._get_event_client_point(e);
                    this.offset_x = point.x / jview.actualZoom - el.offsetLeft;
                    this.offset_y = point.y / jview.actualZoom - el.offsetTop;
                    this.client_hw = Math.floor(el.clientWidth / 2);
                    this.client_hh = Math.floor(el.clientHeight / 2);
                    this._clear_lookup_timer(false, false);
                    var jd = this;
                    this.hlookup_delay = $w.setTimeout(function () {
                        jd.hlookup_delay = 0;
                        jd.hlookup_timer = $w.setInterval(function () {
                            jd.lookup_close_node.call(jd);
                        }, options.lookup_interval);
                    }, options.lookup_delay);
                    this.capture = true;
                }
            }
        },

        drag: function (e) {
            if (!this.jm.get_editable()) { return; }
            if (this.capture) {
                e.preventDefault();
                this.show_shadow();
                this.moved = true;
                clear_selection();
                var jview = this.jm.view;
                var point = this._get_event_client_point(e);
                var px = point.x / jview.actualZoom - this.offset_x;
                var py = point.y / jview.actualZoom - this.offset_y;
                // scrolling container axisY if drag nodes exceeding container
                if (
                    e.clientY - this.view_panel_rect.top < options.scrolling_trigger_width &&
                    this.view_panel.scrollTop > options.scrolling_step_length
                ) {
                    this.view_panel.scrollBy(0, -options.scrolling_step_length);
                    this.offset_y += options.scrolling_step_length / jview.actualZoom;
                } else if (
                    this.view_panel_rect.bottom - e.clientY < options.scrolling_trigger_width &&
                    this.view_panel.scrollTop <
                    this.view_panel.scrollHeight - this.view_panel_rect.height - options.scrolling_step_length
                ) {
                    this.view_panel.scrollBy(0, options.scrolling_step_length);
                    this.offset_y -= options.scrolling_step_length / jview.actualZoom;
                }
                // scrolling container axisX if drag nodes exceeding container
                if (e.clientX - this.view_panel_rect.left < options.scrolling_trigger_width && this.view_panel.scrollLeft > options.scrolling_step_length) {
                    this.view_panel.scrollBy(-options.scrolling_step_length, 0);
                    this.offset_x += options.scrolling_step_length / jview.actualZoom;
                } else if (
                    this.view_panel_rect.right - e.clientX < options.scrolling_trigger_width &&
                    this.view_panel.scrollLeft < this.view_panel.scrollWidth - this.view_panel_rect.width - options.scrolling_step_length
                ) {
                    this.view_panel.scrollBy(options.scrolling_step_length, 0);
                    this.offset_x -= options.scrolling_step_length / jview.actualZoom;
                }
                this.shadow.style.left = px + 'px';
                this.shadow.style.top = py + 'px';
            }
        },

        dragend: function (e) {
            if (!this.jm.get_editable()) { return; }
            if (this.jm.view.get_draggable_canvas()) { this.jm.view.enable_draggable_canvas() }
            if (this.capture) {
                this._clear_lookup_timer(true, true);
                this._clear_highlight();
                if (this.moved) {
                    var src_node = this.active_node;
                    var target_node = this.target_node;
                    var target_direct = this.target_direct;
                    this.move_node(src_node, target_node, target_direct);
                }
                this.hide_shadow();
            }
            this._reset_drag_state();
        },

        move_node: function (src_node, target_node, target_direct) {
            var shadow_h = this.shadow.offsetTop;
            if (!!target_node && !!src_node && !jsMind.node.inherited(src_node, target_node)) {
                // lookup before_node
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
        },

        jm_event_handle: function (type, data) {
            if (type === jsMind.event_type.resize) {
                this.resize();
            }
        }
    };

    var draggable_plugin = new jsMind.plugin('draggable', function (jm) {
        var jd = new jsMind.draggable(jm);
        jd.init();
        jm.add_event_listener(function (type, data) {
            jd.jm_event_handle.call(jd, type, data);
        });
    });

    jsMind.register_plugin(draggable_plugin);

})(window);
