;(function (root, factory) {
    if (typeof module !== 'undefined' && module.exports) {
        module.exports = factory();
    } else {
        var installers = root.__jsMindModuleInstallers = root.__jsMindModuleInstallers || {};
        installers['shortcut-plugin'] = factory();
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

    jm.shortcut_provider = function (jm, options) {
        this.jm = jm;
        this.opts = options;
        this.mapping = options.mapping;
        this.handles = options.handles;
        this._newid = null;
        this._mapping = {};
    };

    jm.shortcut_provider.prototype = {
        init: function () {
            jm.util.dom.add_event(this.jm.view.e_panel, 'keydown', this.handler.bind(this));

            this.handles['addchild'] = this.handle_addchild;
            this.handles['addbrother'] = this.handle_addbrother;
            this.handles['editnode'] = this.handle_editnode;
            this.handles['delnode'] = this.handle_delnode;
            this.handles['toggle'] = this.handle_toggle;
            this.handles['up'] = this.handle_up;
            this.handles['down'] = this.handle_down;
            this.handles['left'] = this.handle_left;
            this.handles['right'] = this.handle_right;

            for (var handle in this.mapping) {
                if (!!this.mapping[handle] && (handle in this.handles)) {
                    var keys = this.mapping[handle];
                    if (!Array.isArray(keys)) {
                        keys = [keys]
                    }
                    for (let key of keys) {
                        this._mapping[key] = this.handles[handle];
                    }
                }
            }

            if (typeof this.opts.id_generator === 'function') {
                this._newid = this.opts.id_generator;
            } else {
                this._newid = jm.util.uuid.newid;
            }
        },

        enable_shortcut: function () {
            this.opts.enable = true;
        },

        disable_shortcut: function () {
            this.opts.enable = false;
        },

        handler: function (e) {
            if (e.which == 9) { e.preventDefault(); } //prevent tab to change focus in browser
            if (this.jm.view.is_editing()) { return; }
            var evt = e || event;
            if (!this.opts.enable) { return true; }
            var kc = evt.keyCode + (evt.metaKey << 13) + (evt.ctrlKey << 12) + (evt.altKey << 11) + (evt.shiftKey << 10);
            if (kc in this._mapping) {
                this._mapping[kc].call(this, this.jm, e);
            }
        },

        handle_addchild: function (_jm, e) {
            var selected_node = _jm.get_selected_node();
            if (!!selected_node) {
                var nodeid = this._newid();
                var node = _jm.add_node(selected_node, nodeid, 'New Node');
                if (!!node) {
                    _jm.select_node(nodeid);
                    _jm.begin_edit(nodeid);
                }
            }
        },
        handle_addbrother: function (_jm, e) {
            var selected_node = _jm.get_selected_node();
            if (!!selected_node && !selected_node.isroot) {
                var nodeid = this._newid();
                var node = _jm.insert_node_after(selected_node, nodeid, 'New Node');
                if (!!node) {
                    _jm.select_node(nodeid);
                    _jm.begin_edit(nodeid);
                }
            }
        },
        handle_editnode: function (_jm, e) {
            var selected_node = _jm.get_selected_node();
            if (!!selected_node) {
                _jm.begin_edit(selected_node);
            }
        },
        handle_delnode: function (_jm, e) {
            var selected_node = _jm.get_selected_node();
            if (!!selected_node && !selected_node.isroot) {
                _jm.select_node(selected_node.parent);
                _jm.remove_node(selected_node);
            }
        },
        handle_toggle: function (_jm, e) {
            var evt = e || event;
            var selected_node = _jm.get_selected_node();
            if (!!selected_node) {
                _jm.toggle_node(selected_node.id);
                evt.stopPropagation();
                evt.preventDefault();
            }
        },
        handle_up: function (_jm, e) {
            var evt = e || event;
            var selected_node = _jm.get_selected_node();
            if (!!selected_node) {
                var up_node = _jm.find_node_before(selected_node);
                if (!up_node) {
                    var np = _jm.find_node_before(selected_node.parent);
                    if (!!np && np.children.length > 0) {
                        up_node = np.children[np.children.length - 1];
                    }
                }
                if (!!up_node) {
                    _jm.select_node(up_node);
                }
                evt.stopPropagation();
                evt.preventDefault();
            }
        },

        handle_down: function (_jm, e) {
            var evt = e || event;
            var selected_node = _jm.get_selected_node();
            if (!!selected_node) {
                var down_node = _jm.find_node_after(selected_node);
                if (!down_node) {
                    var np = _jm.find_node_after(selected_node.parent);
                    if (!!np && np.children.length > 0) {
                        down_node = np.children[0];
                    }
                }
                if (!!down_node) {
                    _jm.select_node(down_node);
                }
                evt.stopPropagation();
                evt.preventDefault();
            }
        },

        handle_left: function (_jm, e) {
            this._handle_direction(_jm, e, jm.direction.left);
        },
        handle_right: function (_jm, e) {
            this._handle_direction(_jm, e, jm.direction.right);
        },
        _handle_direction: function (_jm, e, d) {
            var evt = e || event;
            var selected_node = _jm.get_selected_node();
            var node = null;
            if (!!selected_node) {
                if (selected_node.isroot) {
                    var c = selected_node.children;
                    var children = [];
                    for (var i = 0; i < c.length; i++) {
                        if (c[i].direction === d) {
                            children.push(i);
                        }
                    }
                    node = c[children[Math.floor((children.length - 1) / 2)]];
                }
                else if (selected_node.direction === d) {
                    var children = selected_node.children;
                    var childrencount = children.length;
                    if (childrencount > 0) {
                        node = children[Math.floor((childrencount - 1) / 2)];
                    }
                } else {
                    node = selected_node.parent;
                }
                if (!!node) {
                    _jm.select_node(node);
                }
                evt.stopPropagation();
                evt.preventDefault();
            }
        },
    };


    // plugin
    jm.plugin = function (name, init) {
        this.name = name;
        this.init = init;
    };

    jm.plugins = [];

    jm.register_plugin = function (plugin) {
        if (plugin instanceof jm.plugin) {
            jm.plugins.push(plugin);
        }
    };

    jm.init_plugins = function (sender) {
        $w.setTimeout(function () {
            jm._init_plugins(sender);
        }, 0);
    };

    jm._init_plugins = function (sender) {
        var l = jm.plugins.length;
        var fn_init = null;
        for (var i = 0; i < l; i++) {
            fn_init = jm.plugins[i].init;
            if (typeof fn_init === 'function') {
                fn_init(sender);
            }
        }
    };

        ctx.jm = jm;
    };
});
