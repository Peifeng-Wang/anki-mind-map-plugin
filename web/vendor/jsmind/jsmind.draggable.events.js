/**
 * jsMind draggable plugin event binding and drag flow.
 */
(function ($w) {
    'use strict';
    var parts = $w.jsMindDraggableParts = $w.jsMindDraggableParts || {};

    parts.events = {
        apply: function (proto, env) {
            var jdom = env.jdom;
            var clear_selection = env.clearSelection;
            var options = env.options;

            proto._get_event_client_point = function (e) {
                return {
                    x: e.clientX || e.touches[0].clientX,
                    y: e.clientY || e.touches[0].clientY
                };
            };

            proto._event_bind = function () {
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
            };

            proto.dragstart = function (e) {
                if (!this.jm.get_editable()) { return; }
                if (this.capture) { return; }
                this.active_node = null;

                var jview = this.jm.view;
                var el = e.target || event.srcElement;
                if (el.tagName.toLowerCase() != 'jmnode') { return; }
                if (jview.get_draggable_canvas()) { jview.disable_draggable_canvas(); }
                var nodeid = jview.get_binded_nodeid(el);
                if (!!nodeid) {
                    var node = this.jm.get_node(nodeid);
                    if (!node.isroot) {
                        this.reset_shadow(el);
                        this.view_panel_rect = this.view_panel.getBoundingClientRect();
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
            };

            proto.drag = function (e) {
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
                    this._scroll_view_panel(e, jview);
                    this.shadow.style.left = px + 'px';
                    this.shadow.style.top = py + 'px';
                }
            };

            proto.dragend = function (e) {
                if (!this.jm.get_editable()) { return; }
                if (this.jm.view.get_draggable_canvas()) { this.jm.view.enable_draggable_canvas(); }
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
            };
        }
    };

    if (parts.tryInstall) {
        parts.tryInstall();
    }
})(window);
