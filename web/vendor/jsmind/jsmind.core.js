;(function (root, factory) {
    if (typeof module !== 'undefined' && module.exports) {
        module.exports = factory();
    } else {
        var installers = root.__jsMindModuleInstallers = root.__jsMindModuleInstallers || {};
        installers['core'] = factory();
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

    var DEFAULT_OPTIONS = {
        container: '',   // id of the container
        editable: false, // you can change it in your options
        theme: null,
        mode: 'full',    // full or side
        support_html: true,

        view: {
            engine: 'canvas',
            hmargin: 100,
            vmargin: 50,
            line_width: 2,
            line_color: '#555',
            draggable: false, // drag the mind map with your mouse, when it's larger that the container
            hide_scrollbars_when_draggable: false, // hide container scrollbars, when mind map is larger than container and draggable option is true.
            node_overflow: 'hidden' // hidden or wrap
        },
        layout: {
            hspace: 30,
            vspace: 20,
            pspace: 13,
            cousin_space: 0
        },
        default_event_handle: {
            enable_mousedown_handle: true,
            enable_click_handle: true,
            enable_dblclick_handle: true,
            enable_mousewheel_handle: true
        },
        shortcut: {
            enable: true,
            handles: {
            },
            mapping: {
                addchild: [45, 4096 + 13], // Insert, Ctrl+Enter
                addbrother: 13, // Enter
                editnode: 113,// F2
                delnode: 46, // Delete
                toggle: 32, // Space
                left: 37, // Left
                up: 38, // Up
                right: 39, // Right
                down: 40, // Down
            }
        },
    };

    // core object
    var jm = function (options) {
        jm.current = this;

        this.version = __version__;
        var opts = {};
        jm.util.json.merge(opts, DEFAULT_OPTIONS);
        jm.util.json.merge(opts, options);

        if (!opts.container) {
            logger.error('the options.container should not be null or empty.');
            return;
        }
        this.options = opts;
        this.initialized = false;
        this.mind = null;
        this.event_handles = [];
        this.init();
    };

    jm.prototype = {
        init: function () {
            if (this.initialized) { return; }
            this.initialized = true;

            var opts = this.options;

            var opts_layout = {
                mode: opts.mode,
                hspace: opts.layout.hspace,
                vspace: opts.layout.vspace,
                pspace: opts.layout.pspace,
                cousin_space: opts.layout.cousin_space
            }
            var opts_view = {
                container: opts.container,
                support_html: opts.support_html,
                engine: opts.view.engine,
                hmargin: opts.view.hmargin,
                vmargin: opts.view.vmargin,
                line_width: opts.view.line_width,
                line_color: opts.view.line_color,
                draggable: opts.view.draggable,
                hide_scrollbars_when_draggable: opts.view.hide_scrollbars_when_draggable,
                node_overflow: opts.view.node_overflow
            };
            // create instance of function provider
            this.data = new jm.data_provider(this);
            this.layout = new jm.layout_provider(this, opts_layout);
            this.view = new jm.view_provider(this, opts_view);
            this.shortcut = new jm.shortcut_provider(this, opts.shortcut);

            this.data.init();
            this.layout.init();
            this.view.init();
            this.shortcut.init();

            this._event_bind();

            jm.init_plugins(this);
        },

        enable_edit: function () {
            this.options.editable = true;
        },

        disable_edit: function () {
            this.options.editable = false;
        },

        // call enable_event_handle('dblclick')
        // options are 'mousedown', 'click', 'dblclick'
        enable_event_handle: function (event_handle) {
            this.options.default_event_handle['enable_' + event_handle + '_handle'] = true;
        },

        // call disable_event_handle('dblclick')
        // options are 'mousedown', 'click', 'dblclick'
        disable_event_handle: function (event_handle) {
            this.options.default_event_handle['enable_' + event_handle + '_handle'] = false;
        },

        get_editable: function () {
            return this.options.editable;
        },

        set_theme: function (theme) {
            var theme_old = this.options.theme;
            this.options.theme = (!!theme) ? theme : null;
            if (theme_old != this.options.theme) {
                this.view.reset_theme();
                this.view.reset_custom_style();
            }
        },
        _event_bind: function () {
            this.view.add_event(this, 'mousedown', this.mousedown_handle);
            this.view.add_event(this, 'click', this.click_handle);
            this.view.add_event(this, 'dblclick', this.dblclick_handle);
            this.view.add_event(this, "mousewheel", this.mousewheel_handle)
        },

        mousedown_handle: function (e) {
            if (!this.options.default_event_handle['enable_mousedown_handle']) {
                return;
            }
            var element = e.target || event.srcElement;
            var nodeid = this.view.get_binded_nodeid(element);
            if (!!nodeid) {
                if (this.view.is_node(element)) {
                    this.select_node(nodeid);
                }
            } else {
                this.select_clear();
            }
        },

        click_handle: function (e) {
            if (!this.options.default_event_handle['enable_click_handle']) {
                return;
            }
            var element = e.target || event.srcElement;
            var is_expander = this.view.is_expander(element);
            if (is_expander) {
                var nodeid = this.view.get_binded_nodeid(element);
                if (!!nodeid) {
                    this.toggle_node(nodeid);
                }
            }
        },

        dblclick_handle: function (e) {
            if (!this.options.default_event_handle['enable_dblclick_handle']) {
                return;
            }
            if (this.get_editable()) {
                var element = e.target || event.srcElement;
                var is_node = this.view.is_node(element);
                if (is_node) {
                    var nodeid = this.view.get_binded_nodeid(element);
                    if (!!nodeid) {
                        this.begin_edit(nodeid);
                    }
                }
            }
        },

        // Use [Ctrl] + Mousewheel, to zoom in/out.
        mousewheel_handle: function (event) {
            // Test if mousewheel option is enabled and Ctrl key is pressed.
            if (!this.options.default_event_handle["enable_mousewheel_handle"] || !window.event.ctrlKey) {
                return
            }
            // Avoid default page scrolling behavior.
            event.preventDefault()

            if (event.deltaY < 0) {
                this.view.zoomIn()
            } else {
                this.view.zoomOut()
            }
        },

        begin_edit: function (node) {
            node = this._resolve_node(node);
            if (!node) {
                return false;
            }
            if (!this._require_editable('fail, this mind map is not editable.')) {
                return;
            }
            this.view.edit_node_begin(node);
        },

        end_edit: function () {
            this.view.edit_node_end();
        },

        toggle_node: function (node) {
            node = this._resolve_node(node);
            if (!node) { return; }
            if (node.isroot) { return; }
            this.view.save_location(node);
            this.layout.toggle_node(node);
            this.view.relayout();
            this.view.restore_location(node);
        },

        expand_node: function (node) {
            node = this._resolve_node(node);
            if (!node) { return; }
            if (node.isroot) { return; }
            this.view.save_location(node);
            this.layout.expand_node(node);
            this.view.relayout();
            this.view.restore_location(node);
        },

        collapse_node: function (node) {
            node = this._resolve_node(node);
            if (!node) { return; }
            if (node.isroot) { return; }
            this.view.save_location(node);
            this.layout.collapse_node(node);
            this.view.relayout();
            this.view.restore_location(node);
        },

        expand_all: function () {
            this.layout.expand_all();
            this.view.relayout();
        },

        collapse_all: function () {
            this.layout.collapse_all();
            this.view.relayout();
        },

        expand_to_depth: function (depth) {
            this.layout.expand_to_depth(depth);
            this.view.relayout();
        },

        _reset: function () {
            this.view.reset();
            this.layout.reset();
            this.data.reset();
        },

        _show: function (mind) {
            var m = mind || jm.format.node_array.example;

            this.mind = this.data.load(m);
            if (!this.mind) {
                logger.error('data.load error');
                return;
            } else {
                logger.debug('data.load ok');
            }

            this.view.load();
            logger.debug('view.load ok');

            this.layout.layout();
            logger.debug('layout.layout ok');

            this.view.show(true);
            logger.debug('view.show ok');

            this.invoke_event_handle(jm.event_type.show, { data: [mind] });
        },

        show: function (mind) {
            this._reset();
            this._show(mind);
        },

        get_meta: function () {
            return {
                name: this.mind.name,
                author: this.mind.author,
                version: this.mind.version
            };
        },

        get_data: function (data_format) {
            var df = data_format || 'node_tree';
            return this.data.get_data(df);
        },

        get_root: function () {
            return this.mind.root;
        },

        get_node: function (node) {
            if (jm.util.is_node(node)) {
                return node;
            }
            return this.mind.get_node(node);
        },

        _resolve_node: function (node) {
            if (jm.util.is_node(node)) {
                return node;
            }
            var the_node = this.get_node(node);
            if (!the_node) {
                logger.error('the node[id=' + node + '] can not be found.');
            }
            return the_node;
        },

        _require_editable: function (message) {
            if (this.get_editable()) {
                return true;
            }
            logger.error(message || 'fail, this mind map is not editable');
            return false;
        },

        add_node: function (parent_node, nodeid, topic, data, direction) {
            if (!this._require_editable()) {
                return null;
            }
            var the_parent_node = this.get_node(parent_node);
            var dir = jm.direction.of(direction)
            if (dir === undefined) {
                dir = this.layout.calculate_next_child_direction(the_parent_node);
            }
            var node = this.mind.add_node(the_parent_node, nodeid, topic, data, dir);
            if (!!node) {
                this.view.add_node(node);
                this.layout.layout();
                this.view.show(false);
                this.view.reset_node_custom_style(node);
                this.expand_node(the_parent_node);
                this.invoke_event_handle(jm.event_type.edit, { evt: 'add_node', data: [the_parent_node.id, nodeid, topic, data, dir], node: nodeid });
            }
            return node;
        },

        insert_node_before: function (node_before, nodeid, topic, data, direction) {
            if (!this._require_editable()) {
                return null;
            }
            var the_node_before = this.get_node(node_before);
            var dir = jm.direction.of(direction)
            if (dir === undefined) {
                dir = this.layout.calculate_next_child_direction(the_node_before.parent);
            }
            var node = this.mind.insert_node_before(the_node_before, nodeid, topic, data, dir);
            if (!!node) {
                this.view.add_node(node);
                this.layout.layout();
                this.view.show(false);
                this.invoke_event_handle(jm.event_type.edit, { evt: 'insert_node_before', data: [the_node_before.id, nodeid, topic, data, dir], node: nodeid });
            }
            return node;
        },

        insert_node_after: function (node_after, nodeid, topic, data, direction) {
            if (!this._require_editable()) {
                return null;
            }
            var the_node_after = this.get_node(node_after);
            var dir = jm.direction.of(direction)
            if (dir === undefined) {
                dir = this.layout.calculate_next_child_direction(the_node_after.parent);
            }
            var node = this.mind.insert_node_after(the_node_after, nodeid, topic, data, dir);
            if (!!node) {
                this.view.add_node(node);
                this.layout.layout();
                this.view.show(false);
                this.invoke_event_handle(jm.event_type.edit, { evt: 'insert_node_after', data: [the_node_after.id, nodeid, topic, data, dir], node: nodeid });
            }
            return node;
        },

        remove_node: function (node) {
            node = this._resolve_node(node);
            if (!node) {
                return false;
            }
            if (!this._require_editable()) {
                return false;
            }
            if (node.isroot) {
                logger.error('fail, can not remove root node');
                return false;
            }
            var nodeid = node.id;
            var parentid = node.parent.id;
            var parent_node = this.get_node(parentid);
            this.view.save_location(parent_node);
            this.view.remove_node(node);
            this.mind.remove_node(node);
            this.layout.layout();
            this.view.show(false);
            this.view.restore_location(parent_node);
            this.invoke_event_handle(jm.event_type.edit, { evt: 'remove_node', data: [nodeid], node: parentid });
            return true;
        },

        update_node: function (nodeid, topic) {
            if (!this._require_editable()) {
                return;
            }
            if (jm.util.text.is_empty(topic)) {
                logger.warn('fail, topic can not be empty');
                return;
            }
            var node = this.get_node(nodeid);
            if (!!node) {
                if (node.topic === topic) {
                    logger.info('nothing changed');
                    this.view.update_node(node);
                    return;
                }
                node.topic = topic;
                this.view.update_node(node);
                this.layout.layout();
                this.view.show(false);
                this.invoke_event_handle(jm.event_type.edit, { evt: 'update_node', data: [nodeid, topic], node: nodeid });
            }
        },

        move_node: function (nodeid, beforeid, parentid, direction) {
            if (!this._require_editable()) {
                return;
            }
            var node = this.get_node(nodeid);
            var updated_node = this.mind.move_node(node, beforeid, parentid, direction);
            if (!!updated_node) {
                this.view.update_node(updated_node);
                this.layout.layout();
                this.view.show(false);
                this.invoke_event_handle(jm.event_type.edit, { evt: 'move_node', data: [nodeid, beforeid, parentid, direction], node: nodeid });
            }
        },

        select_node: function (node) {
            node = this._resolve_node(node);
            if (!node) { return; }
            if (!this.layout.is_visible(node)) {
                return;
            }
            this.mind.selected = node;
            this.view.select_node(node);
            this.invoke_event_handle(jm.event_type.select, { evt: 'select_node', data: [], node: node.id });
        },

        get_selected_node: function () {
            if (!!this.mind) {
                return this.mind.selected;
            } else {
                return null;
            }
        },

        select_clear: function () {
            if (!!this.mind) {
                this.mind.selected = null;
                this.view.select_clear();
            }
        },

        is_node_visible: function (node) {
            return this.layout.is_visible(node);
        },

        find_node_before: function (node) {
            node = this._resolve_node(node);
            if (!node) { return; }
            if (node.isroot) { return null; }
            var n = null;
            if (node.parent.isroot) {
                var c = node.parent.children;
                var prev = null;
                var ni = null;
                for (var i = 0; i < c.length; i++) {
                    ni = c[i];
                    if (node.direction === ni.direction) {
                        if (node.id === ni.id) {
                            n = prev;
                        }
                        prev = ni;
                    }
                }
            } else {
                n = this.mind.get_node_before(node);
            }
            return n;
        },

        find_node_after: function (node) {
            node = this._resolve_node(node);
            if (!node) { return; }
            if (node.isroot) { return null; }
            var n = null;
            if (node.parent.isroot) {
                var c = node.parent.children;
                var getthis = false;
                var ni = null;
                for (var i = 0; i < c.length; i++) {
                    ni = c[i];
                    if (node.direction === ni.direction) {
                        if (getthis) {
                            n = ni;
                            break;
                        }
                        if (node.id === ni.id) {
                            getthis = true;
                        }
                    }
                }
            } else {
                n = this.mind.get_node_after(node);
            }
            return n;
        },

        set_node_color: function (nodeid, bgcolor, fgcolor) {
            if (!this._require_editable()) {
                return null;
            }
            var node = this.mind.get_node(nodeid);
            if (!!node) {
                if (!!bgcolor) {
                    node.data['background-color'] = bgcolor;
                }
                if (!!fgcolor) {
                    node.data['foreground-color'] = fgcolor;
                }
                this.view.reset_node_custom_style(node);
            }
        },

        set_node_font_style: function (nodeid, size, weight, style) {
            if (!this._require_editable()) {
                return null;
            }
            var node = this.mind.get_node(nodeid);
            if (!!node) {
                if (!!size) {
                    node.data['font-size'] = size;
                }
                if (!!weight) {
                    node.data['font-weight'] = weight;
                }
                if (!!style) {
                    node.data['font-style'] = style;
                }
                this.view.reset_node_custom_style(node);
                this.view.update_node(node);
                this.layout.layout();
                this.view.show(false);
            }
        },

        set_node_background_image: function (nodeid, image, width, height, rotation) {
            if (!this._require_editable()) {
                return null;
            }
            var node = this.mind.get_node(nodeid);
            if (!!node) {
                if (!!image) {
                    node.data['background-image'] = image;
                }
                if (!!width) {
                    node.data['width'] = width;
                }
                if (!!height) {
                    node.data['height'] = height;
                }
                if (!!rotation) {
                    node.data['background-rotation'] = rotation;
                }
                this.view.reset_node_custom_style(node);
                this.view.update_node(node);
                this.layout.layout();
                this.view.show(false);
            }
        },

        set_node_background_rotation: function (nodeid, rotation) {
            if (!this._require_editable()) {
                return null;
            }
            var node = this.mind.get_node(nodeid);
            if (!!node) {
                if (!node.data['background-image']) {
                    logger.error('fail, only can change rotation angle of node with background image');
                    return null;
                }
                node.data['background-rotation'] = rotation;
                this.view.reset_node_custom_style(node);
                this.view.update_node(node);
                this.layout.layout();
                this.view.show(false);
            }
        },

        resize: function () {
            this.view.resize();
        },

        // callback(type ,data)
        add_event_listener: function (callback) {
            if (typeof callback === 'function') {
                this.event_handles.push(callback);
            }
        },

        clear_event_listener: function () {
            this.event_handles = [];
        },

        invoke_event_handle: function (type, data) {
            var j = this;
            $w.setTimeout(function () {
                j._invoke_event_handle(type, data);
            }, 0);
        },

        _invoke_event_handle: function (type, data) {
            var l = this.event_handles.length;
            for (var i = 0; i < l; i++) {
                this.event_handles[i](type, data);
            }
        },

    };


    jm.show = function (options, mind) {
        logger.warn('`jsMind.show(options, mind)` is deprecated, please use `jm = new jsMind(options); jm.show(mind);` instead')
        var _jm = new jm(options);
        _jm.show(mind);
        return _jm;
    };

        ctx.jm = jm;
    };
});
