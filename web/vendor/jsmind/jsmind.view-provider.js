;(function (root, factory) {
    if (typeof module !== 'undefined' && module.exports) {
        module.exports = factory();
    } else {
        var installers = root.__jsMindModuleInstallers = root.__jsMindModuleInstallers || {};
        installers['view-provider'] = factory();
    }
})(typeof window !== 'undefined' ? window : (typeof global !== 'undefined' ? global : this), function () {
    'use strict';

    return function (ctx) {
        var $w = ctx.$w;
        var $d = ctx.$d;
        var $g = ctx.$g;
        var $c = ctx.$c;
        var $t = ctx.$t;
        var $h = ctx.$h;
        var $i = ctx.$i;
        var logger = ctx.logger;
        var __name__ = ctx.__name__;
        var __version__ = ctx.__version__;
        var __author__ = ctx.__author__;
        var VIEW_DRAG_INITIAL_BUFFER = ctx.VIEW_DRAG_INITIAL_BUFFER;
        var VIEW_DRAG_EXPAND_THRESHOLD = ctx.VIEW_DRAG_EXPAND_THRESHOLD;
        var VIEW_DRAG_EXPAND_SIZE = ctx.VIEW_DRAG_EXPAND_SIZE;
        var jm = ctx.jm;

    jm.graph_canvas = function (view) {
        this.opts = view.opts;
        this.e_canvas = $c('canvas');
        this.e_canvas.className = 'jsmind';
        this.canvas_ctx = this.e_canvas.getContext('2d');
        this.size = { w: 0, h: 0 };
    };

    jm.graph_canvas.prototype = {
        element: function () {
            return this.e_canvas;
        },

        set_size: function (w, h) {
            this.size.w = w;
            this.size.h = h;
            this.e_canvas.width = w;
            this.e_canvas.height = h;
        },

        clear: function () {
            this.canvas_ctx.clearRect(0, 0, this.size.w, this.size.h);
        },

        draw_line: function (pout, pin, offset) {
            var ctx = this.canvas_ctx;
            ctx.strokeStyle = this.opts.line_color;
            ctx.lineWidth = this.opts.line_width;
            ctx.lineCap = 'round';

            this._bezier_to(ctx,
                pin.x + offset.x,
                pin.y + offset.y,
                pout.x + offset.x,
                pout.y + offset.y);
        },

        copy_to: function (dest_canvas_ctx, callback) {
            dest_canvas_ctx.drawImage(this.e_canvas, 0, 0);
            !!callback && callback();
        },

        _bezier_to: function (ctx, x1, y1, x2, y2) {
            ctx.beginPath();
            ctx.moveTo(x1, y1);
            ctx.bezierCurveTo(x1 + (x2 - x1) * 2 / 3, y1, x1, y2, x2, y2);
            ctx.stroke();
        },

        _line_to: function (ctx, x1, y1, x2, y2) {
            ctx.beginPath();
            ctx.moveTo(x1, y1);
            ctx.lineTo(x2, y2);
            ctx.stroke();
        }
    };

    jm.graph_svg = function (view) {
        this.view = view;
        this.opts = view.opts;
        this.e_svg = jm.graph_svg.c('svg');
        this.e_svg.setAttribute('class', 'jsmind');
        this.size = { w: 0, h: 0 };
        this.lines = [];
    };

    jm.graph_svg.c = function (tag) {
        return $d.createElementNS('http://www.w3.org/2000/svg', tag);
    };

    jm.graph_svg.prototype = {
        element: function () {
            return this.e_svg;
        },

        set_size: function (w, h) {
            this.size.w = w;
            this.size.h = h;
            this.e_svg.setAttribute('width', w);
            this.e_svg.setAttribute('height', h);
        },

        clear: function () {
            this.e_svg.textContent = '';
            this.lines.length = 0;
        },

        draw_line: function (pout, pin, offset) {
            var line = jm.graph_svg.c('path');
            line.setAttribute('stroke', this.opts.line_color);
            line.setAttribute('stroke-width', this.opts.line_width);
            line.setAttribute('fill', 'transparent');
            this.lines.push(line);
            this.e_svg.appendChild(line);
            this._bezier_to(line, pin.x + offset.x, pin.y + offset.y, pout.x + offset.x, pout.y + offset.y);
        },

        copy_to: function (dest_canvas_ctx, callback) {
            var img = new Image();
            img.onload = function () {
                dest_canvas_ctx.drawImage(img, 0, 0);
                !!callback && callback();
            }
            img.src = 'data:image/svg+xml;base64,' + btoa(new XMLSerializer().serializeToString(this.e_svg));
        },

        _bezier_to: function (path, x1, y1, x2, y2) {
            path.setAttribute('d', 'M' + x1 + ' ' + y1 + ' C ' + (x1 + (x2 - x1) * 2 / 3) + ' ' + y1 + ', ' + x1 + ' ' + y2 + ', ' + x2 + ' ' + y2);
        },

        _line_to: function (path, x1, y1, x2, y2) {
            path.setAttribute('d', 'M ' + x1 + ' ' + y1 + ' L ' + x2 + ' ' + y2);
        }
    };

    // view provider
    jm.view_provider = function (jm, options) {
        this.opts = options;
        this.jm = jm;
        this.layout = jm.layout;

        this.container = null;
        this.e_panel = null;
        this.e_nodes = null;

        this.size = { w: 0, h: 0 };

        this.selected_node = null;
        this.editing_node = null;

        this.graph = null;
    };

    jm.view_provider.prototype = {
        init: function () {
            logger.debug('view.init');

            this.container = $i(this.opts.container) ? this.opts.container : $g(this.opts.container);
            if (!this.container) {
                logger.error('the options.view.container was not be found in dom');
                return;
            }
            this.e_panel = $c('div');
            this.e_nodes = $c('jmnodes');
            this.e_editor = $c('input');

            this.graph = this.opts.engine.toLowerCase() === 'svg' ? new jm.graph_svg(this) : new jm.graph_canvas(this);
            this.e_panel.className = 'jsmind-inner jmnode-overflow-' + this.opts.node_overflow;
            this.e_panel.tabIndex = 1;
            this.e_panel.appendChild(this.graph.element());
            this.e_panel.appendChild(this.e_nodes);

            this.e_editor.className = 'jsmind-editor';
            this.e_editor.type = 'text';

            this.actualZoom = 1;
            this.zoomStep = 0.1;
            this.minZoom = 0.5;
            this.maxZoom = 2;

            var v = this;
            jm.util.dom.add_event(this.e_editor, 'keydown', function (e) {
                var evt = e || event;
                if (evt.keyCode == 13) { v.edit_node_end(); evt.stopPropagation(); }
            });
            jm.util.dom.add_event(this.e_editor, 'blur', function (e) {
                v.edit_node_end();
            });

            this.container.appendChild(this.e_panel);

            // Used to avoid dragging, while editing node.
            this.dragging_enabled = true

            this.draggable_canvas()
        },

        add_event: function (obj, event_name, event_handle) {
            jm.util.dom.add_event(this.e_nodes, event_name, function (e) {
                var evt = e || event;
                event_handle.call(obj, evt);
            });
        },

        get_binded_nodeid: function (element) {
            while (element != null) {
                var tagName = element.tagName.toLowerCase();
                if (tagName == 'jmnode' || tagName == 'jmexpander') {
                    return element.getAttribute('nodeid');
                } else if (tagName == 'jmnodes' || tagName == 'body' || tagName == 'html') {
                    return null;
                }
                element = element.parentElement;
            }
            return null;
        },

        is_node: function (element) {
            while (element != null) {
                var tagName = element.tagName.toLowerCase();
                if (tagName == 'jmnode') {
                    return true;
                } else if (tagName == 'jmnodes' || tagName == 'body' || tagName == 'html') {
                    return false;
                }
                element = element.parentElement;
            }
            return false;
        },

        is_expander: function (element) {
            return (element.tagName.toLowerCase() == 'jmexpander');
        },

        reset: function () {
            logger.debug('view.reset');
            this.selected_node = null;
            this.clear_lines();
            this.clear_nodes();
            this.reset_theme();
        },

        reset_theme: function () {
            var theme_name = this.jm.options.theme;
            if (!!theme_name) {
                this.e_nodes.className = 'theme-' + theme_name;
            } else {
                this.e_nodes.className = '';
            }
        },

        reset_custom_style: function () {
            var nodes = this.jm.mind.nodes;
            for (var nodeid in nodes) {
                this.reset_node_custom_style(nodes[nodeid]);
            }
        },

        load: function () {
            logger.debug('view.load');
            this.init_nodes();
        },

        expand_size: function () {
            var min_size = this.layout.get_min_size();
            var min_width = min_size.w + this.opts.hmargin * 2;
            var min_height = min_size.h + this.opts.vmargin * 2;
            var client_w = this.e_panel.clientWidth;
            var client_h = this.e_panel.clientHeight;
            if (client_w < min_width) { client_w = min_width; }
            if (client_h < min_height) { client_h = min_height; }

            // Add extra buffer space to prevent content disappearing on first drag
            this.size.w = client_w + VIEW_DRAG_INITIAL_BUFFER;
            this.size.h = client_h + VIEW_DRAG_INITIAL_BUFFER;
        },

        init_nodes_size: function (node) {
            var view_data = node._data.view;
            view_data.width = view_data.element.clientWidth;
            view_data.height = view_data.element.clientHeight;
        },

        init_nodes: function () {
            var nodes = this.jm.mind.nodes;
            var doc_frag = $d.createDocumentFragment();
            for (var nodeid in nodes) {
                this.create_node_element(nodes[nodeid], doc_frag);
            }
            this.e_nodes.appendChild(doc_frag);
            for (var nodeid in nodes) {
                this.init_nodes_size(nodes[nodeid]);
            }
        },

        add_node: function (node) {
            this.create_node_element(node, this.e_nodes);
            this.init_nodes_size(node);
        },

        create_node_element: function (node, parent_node) {
            var view_data = null;
            if ('view' in node._data) {
                view_data = node._data.view;
            } else {
                view_data = {};
                node._data.view = view_data;
            }

            var d = $c('jmnode');
            if (node.isroot) {
                d.className = 'root';
            } else {
                var d_e = $c('jmexpander');
                $t(d_e, '-');
                d_e.setAttribute('nodeid', node.id);
                d_e.style.visibility = 'hidden';
                parent_node.appendChild(d_e);
                view_data.expander = d_e;
            }
            if (!!node.topic) {
                if (this.opts.support_html) {
                    $h(d, node.topic);
                } else {
                    $t(d, node.topic);
                }
            }
            d.setAttribute('nodeid', node.id);
            d.style.visibility = 'hidden';
            this._reset_node_custom_style(d, node.data);

            parent_node.appendChild(d);
            view_data.element = d;
        },

        remove_node: function (node) {
            if (this.selected_node != null && this.selected_node.id == node.id) {
                this.selected_node = null;
            }
            if (this.editing_node != null && this.editing_node.id == node.id) {
                node._data.view.element.removeChild(this.e_editor);
                this.editing_node = null;
            }
            var children = node.children;
            var i = children.length;
            while (i--) {
                this.remove_node(children[i]);
            }
            if (node._data.view) {
                var element = node._data.view.element;
                var expander = node._data.view.expander;
                this.e_nodes.removeChild(element);
                this.e_nodes.removeChild(expander);
                node._data.view.element = null;
                node._data.view.expander = null;
            }
        },

        update_node: function (node) {
            var view_data = node._data.view;
            var element = view_data.element;
            if (!!node.topic) {
                if (this.opts.support_html) {
                    $h(element, node.topic);
                } else {
                    $t(element, node.topic);
                }
            }
            if (this.layout.is_visible(node)) {
                view_data.width = element.clientWidth;
                view_data.height = element.clientHeight;
            } else {
                let origin_style = element.getAttribute('style');
                element.style = 'visibility: visible; left:0; top:0;';
                view_data.width = element.clientWidth;
                view_data.height = element.clientHeight;
                element.style = origin_style;
            }
        },

        select_node: function (node) {
            if (!!this.selected_node) {
                this.selected_node._data.view.element.className =
                    this.selected_node._data.view.element.className.replace(/\s*selected\b/i, '');
                this.reset_node_custom_style(this.selected_node);
            }
            if (!!node) {
                this.selected_node = node;
                node._data.view.element.className += ' selected';
                this.clear_node_custom_style(node);
            }
        },

        select_clear: function () {
            this.select_node(null);
        },

        get_editing_node: function () {
            return this.editing_node;
        },

        is_editing: function () {
            return (!!this.editing_node);
        },

        edit_node_begin: function (node) {
            if (!node.topic) {
                logger.warn("don't edit image nodes");
                return;
            }
            if (this.editing_node != null) {
                this.edit_node_end();
            }
            this.editing_node = node;
            var view_data = node._data.view;
            var element = view_data.element;
            var topic = node.topic;
            var ncs = getComputedStyle(element);
            this.e_editor.value = topic;
            this.e_editor.style.width = (element.clientWidth - parseInt(ncs.getPropertyValue('padding-left')) - parseInt(ncs.getPropertyValue('padding-right'))) + 'px';
            element.innerHTML = '';
            element.appendChild(this.e_editor);
            element.style.zIndex = 5;
            this.e_editor.focus();
            this.e_editor.select();
        },

        edit_node_end: function () {
            if (this.editing_node != null) {
                var node = this.editing_node;
                this.editing_node = null;
                var view_data = node._data.view;
                var element = view_data.element;
                var topic = this.e_editor.value;
                element.style.zIndex = 'auto';
                element.removeChild(this.e_editor);
                if (jm.util.text.is_empty(topic) || node.topic === topic) {
                    if (this.opts.support_html) {
                        $h(element, node.topic);
                    } else {
                        $t(element, node.topic);
                    }
                } else {
                    this.jm.update_node(node.id, topic);
                }
            }
            this.e_panel.focus();
        },

        get_view_offset: function () {
            var bounds = this.layout.bounds;
            var _x = (this.size.w - bounds.e - bounds.w) / 2;
            var _y = this.size.h / 2;
            return { x: _x, y: _y };
        },

        resize: function () {
            this.graph.set_size(1, 1);
            this.e_nodes.style.width = '1px';
            this.e_nodes.style.height = '1px';

            this.expand_size();
            this._show();
        },

        _show: function () {
            this.graph.set_size(this.size.w, this.size.h);
            this.e_nodes.style.width = this.size.w + 'px';
            this.e_nodes.style.height = this.size.h + 'px';
            this.show_nodes();
            this.show_lines();
            //this.layout.cache_valid = true;
            this.jm.invoke_event_handle(jm.event_type.resize, { data: [] });
        },

        zoomIn: function () {
            return this.setZoom(this.actualZoom + this.zoomStep);
        },

        zoomOut: function () {
            return this.setZoom(this.actualZoom - this.zoomStep);
        },

        setZoom: function (zoom) {
            if ((zoom < this.minZoom) || (zoom > this.maxZoom)) {
                return false;
            }
            this.actualZoom = zoom;
            for (var i = 0; i < this.e_panel.children.length; i++) {
                this.e_panel.children[i].style.zoom = zoom;
            };

            this.show(false);

            var selected_node = this.jm.get_selected_node();
            if (!!selected_node) {
                var view_data = selected_node._data.view;
                var node_center_x = view_data.abs_x + view_data.width / 2;
                var node_center_y = view_data.abs_y + view_data.height / 2;

                var client_w = this.e_panel.clientWidth;
                var client_h = this.e_panel.clientHeight;

                this.e_panel.scrollLeft = node_center_x * this.actualZoom - client_w / 2;
                this.e_panel.scrollTop = node_center_y * this.actualZoom - client_h / 2;
            }
            return true;
        },

        _center_root: function () {
            // center root node
            var outer_w = this.e_panel.clientWidth;
            var outer_h = this.e_panel.clientHeight;
            if (this.size.w > outer_w) {
                var _offset = this.get_view_offset();
                this.e_panel.scrollLeft = _offset.x * this.actualZoom - outer_w / 2;
            }
            if (this.size.h > outer_h) {
                this.e_panel.scrollTop = (this.size.h * this.actualZoom - outer_h) / 2;
            }
        },

        show: function (keep_center) {
            logger.debug('view.show');
            this.expand_size();
            this._show();
            if (!!keep_center) {
                this._center_root();
            }
        },

        relayout: function () {
            this.expand_size();
            this._show();
        },

        save_location: function (node) {
            var vd = node._data.view;
            vd._saved_location = {
                x: parseInt(vd.element.style.left) - this.e_panel.scrollLeft,
                y: parseInt(vd.element.style.top) - this.e_panel.scrollTop,
            };
        },

        restore_location: function (node) {
            var vd = node._data.view;
            this.e_panel.scrollLeft = parseInt(vd.element.style.left) - vd._saved_location.x;
            this.e_panel.scrollTop = parseInt(vd.element.style.top) - vd._saved_location.y;
        },

        clear_nodes: function () {
            var mind = this.jm.mind;
            if (mind == null) {
                return;
            }
            var nodes = mind.nodes;
            var node = null;
            for (var nodeid in nodes) {
                node = nodes[nodeid];
                node._data.view.element = null;
                node._data.view.expander = null;
            }
            this.e_nodes.innerHTML = '';
        },

        show_nodes: function () {
            var nodes = this.jm.mind.nodes;
            var node = null;
            var node_element = null;
            var expander = null;
            var p = null;
            var p_expander = null;
            var expander_text = '-';
            var view_data = null;
            var _offset = this.get_view_offset();
            for (var nodeid in nodes) {
                node = nodes[nodeid];
                view_data = node._data.view;
                node_element = view_data.element;
                expander = view_data.expander;
                if (!this.layout.is_visible(node)) {
                    node_element.style.display = 'none';
                    expander.style.display = 'none';
                    continue;
                }
                this.reset_node_custom_style(node);
                p = this.layout.get_node_point(node);
                view_data.abs_x = _offset.x + p.x;
                view_data.abs_y = _offset.y + p.y;
                node_element.style.left = (_offset.x + p.x) + 'px';
                node_element.style.top = (_offset.y + p.y) + 'px';
                node_element.style.display = '';
                node_element.style.visibility = 'visible';
                if (!node.isroot && node.children.length > 0) {
                    expander_text = node.expanded ? '-' : '+';
                    p_expander = this.layout.get_expander_point(node);
                    expander.style.left = (_offset.x + p_expander.x) + 'px';
                    expander.style.top = (_offset.y + p_expander.y) + 'px';
                    expander.style.display = '';
                    expander.style.visibility = 'visible';
                    $t(expander, expander_text);
                }
                // hide expander while all children have been removed
                if (!node.isroot && node.children.length == 0) {
                    expander.style.display = 'none';
                    expander.style.visibility = 'hidden';
                }
            }
        },

        reset_node_custom_style: function (node) {
            this._reset_node_custom_style(node._data.view.element, node.data);
        },

        _reset_node_custom_style: function (node_element, node_data) {
            if ('background-color' in node_data) {
                node_element.style.backgroundColor = node_data['background-color'];
            }
            if ('foreground-color' in node_data) {
                node_element.style.color = node_data['foreground-color'];
            }
            if ('width' in node_data) {
                node_element.style.width = node_data['width'] + 'px';
            }
            if ('height' in node_data) {
                node_element.style.height = node_data['height'] + 'px';
            }
            if ('font-size' in node_data) {
                node_element.style.fontSize = node_data['font-size'] + 'px';
            }
            if ('font-weight' in node_data) {
                node_element.style.fontWeight = node_data['font-weight'];
            }
            if ('font-style' in node_data) {
                node_element.style.fontStyle = node_data['font-style'];
            }
            if ('background-image' in node_data) {
                var backgroundImage = node_data['background-image'];
                if (backgroundImage.startsWith('data') && node_data['width'] && node_data['height']) {
                    var img = new Image();

                    img.onload = function () {
                        var c = $c('canvas');
                        c.width = node_element.clientWidth;
                        c.height = node_element.clientHeight;
                        var img = this;
                        if (c.getContext) {
                            var ctx = c.getContext('2d');
                            ctx.drawImage(img, 2, 2, node_element.clientWidth, node_element.clientHeight);
                            var scaledImageData = c.toDataURL();
                            node_element.style.backgroundImage = 'url(' + scaledImageData + ')';
                        }
                    };
                    img.src = backgroundImage;

                } else {
                    node_element.style.backgroundImage = 'url(' + backgroundImage + ')';
                }
                node_element.style.backgroundSize = '99%';

                if ('background-rotation' in node_data) {
                    node_element.style.transform = 'rotate(' + node_data['background-rotation'] + 'deg)';
                }
            }
        },

        clear_node_custom_style: function (node) {
            var node_element = node._data.view.element;
            node_element.style.backgroundColor = "";
            node_element.style.color = "";
        },

        clear_lines: function () {
            this.graph.clear();
        },

        show_lines: function () {
            this.clear_lines();
            var nodes = this.jm.mind.nodes;
            var node = null;
            var pin = null;
            var pout = null;
            var _offset = this.get_view_offset();
            for (var nodeid in nodes) {
                node = nodes[nodeid];
                if (!!node.isroot) { continue; }
                if (('visible' in node._data.layout) && !node._data.layout.visible) { continue; }
                pin = this.layout.get_node_point_in(node);
                pout = this.layout.get_node_point_out(node.parent);
                this.graph.draw_line(pout, pin, _offset);
            }
        },

        // Drag the whole mind map with your mouse (usefull when it's larger that the container).
        draggable_canvas: function () {
            // If draggable option is true.
            if (this.opts.draggable) {
                // Dragging disabled by default.
                let dragging = false
                let x, y
                if (this.opts.hide_scrollbars_when_draggable) {
                    // Avoid scrollbars when mind map is larger than the container (e_panel = id jsmind-inner)
                    this.e_panel.style = 'overflow: hidden'
                }
                // Move the whole mind map with mouse moves, while button is down.
                jm.util.dom.add_event(this.container, 'mousedown', (eventDown) => {
                    dragging = true
                    // Record current mouse position.
                    x = eventDown.clientX
                    y = eventDown.clientY
                })
                // Stop moving mind map once mouse button is released.
                jm.util.dom.add_event(this.container, 'mouseup', () => {
                    dragging = false
                })
                // Follow current mouse position and move mind map accordingly.
                jm.util.dom.add_event(this.container, 'mousemove', (eventMove) => {
                    if (this.dragging_enabled && dragging) {
                        // Dynamically expand container if nearing edges (for infinite canvas)
                        const dx = x - eventMove.clientX;
                        const dy = y - eventMove.clientY;
                        // Only expand when there is actually scrollable overflow in that direction.
                        // Otherwise (e.g. at min zoom where content fits) expansion triggers every mousemove and shifts the layout.
                        const canScrollX = this.e_panel.scrollWidth > this.e_panel.clientWidth + 1;
                        const canScrollY = this.e_panel.scrollHeight > this.e_panel.clientHeight + 1;

                        // Expand right if scrolling near right edge
                        if (dx > 0 && canScrollX &&
                            this.e_panel.scrollLeft + this.e_panel.clientWidth > this.e_panel.scrollWidth - VIEW_DRAG_EXPAND_THRESHOLD) {
                            this.size.w += VIEW_DRAG_EXPAND_SIZE;
                            this.e_nodes.style.width = this.size.w + 'px';
                            this.graph.set_size(this.size.w, this.size.h);
                            this.show_nodes(); // Redraw nodes after canvas resize
                            this.show_lines(); // Redraw lines after canvas resize
                        }

                        // Expand bottom if scrolling near bottom edge
                        if (dy > 0 && canScrollY &&
                            this.e_panel.scrollTop + this.e_panel.clientHeight > this.e_panel.scrollHeight - VIEW_DRAG_EXPAND_THRESHOLD) {
                            this.size.h += VIEW_DRAG_EXPAND_SIZE;
                            this.e_nodes.style.height = this.size.h + 'px';
                            this.graph.set_size(this.size.w, this.size.h);
                            this.show_nodes(); // Redraw nodes after canvas resize
                            this.show_lines(); // Redraw lines after canvas resize
                        }

                        this.e_panel.scrollBy(dx, dy)
                        // Record new current position.
                        x = eventMove.clientX
                        y = eventMove.clientY
                    }
                })
            }
        },

        get_draggable_canvas: function () {
            return this.opts.draggable
        },

        enable_draggable_canvas: function () {
            this.dragging_enabled = true
        },

        disable_draggable_canvas: function () {
            this.dragging_enabled = false
        },

    };


        ctx.jm = jm;
    };
});
