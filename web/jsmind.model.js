;(function (root, factory) {
    if (typeof module !== 'undefined' && module.exports) {
        module.exports = factory();
    } else {
        var installers = root.__jsMindModuleInstallers = root.__jsMindModuleInstallers || {};
        installers['model'] = factory();
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

    jm.direction = {
        left: -1, center: 0, right: 1, of: function (dir) {
            if (!dir || dir === -1 || dir === 0 || dir === 1) {
                return dir;
            }
            if (dir === '-1' || dir === '0' || dir === '1') {
                return parseInt(dir);
            }
            if (dir.toLowerCase() === 'left') {
                return this.left;
            }
            if (dir.toLowerCase() === 'right') {
                return this.right;
            }
            if (dir.toLowerCase() === 'center') {
                return this.center;
            }
        }
    };
    jm.event_type = { show: 1, resize: 2, edit: 3, select: 4 };
    jm.key = { meta: 1 << 13, ctrl: 1 << 12, alt: 1 << 11, shift: 1 << 10 };

    jm.node = function (sId, iIndex, sTopic, oData, bIsRoot, oParent, eDirection, bExpanded) {
        if (!sId) { logger.error('invalid node id'); return; }
        if (typeof iIndex != 'number') { logger.error('invalid node index'); return; }
        if (typeof bExpanded === 'undefined') { bExpanded = true; }
        this.id = sId;
        this.index = iIndex;
        this.topic = sTopic;
        this.data = oData || {};
        this.isroot = bIsRoot;
        this.parent = oParent;
        this.direction = eDirection;
        this.expanded = !!bExpanded;
        this.children = [];
        this._data = {};
    };

    jm.node.compare = function (node1, node2) {
        // '-1' is alwary the last
        var r = 0;
        var i1 = node1.index;
        var i2 = node2.index;
        if (i1 >= 0 && i2 >= 0) {
            r = i1 - i2;
        } else if (i1 == -1 && i2 == -1) {
            r = 0;
        } else if (i1 == -1) {
            r = 1;
        } else if (i2 == -1) {
            r = -1;
        } else {
            r = 0;
        }
        //logger.debug(i1+' <> '+i2+'  =  '+r);
        return r;
    };

    jm.node.inherited = function (pnode, node) {
        if (!!pnode && !!node) {
            if (pnode.id === node.id) {
                return true;
            }
            if (pnode.isroot) {
                return true;
            }
            var pid = pnode.id;
            var p = node;
            while (!p.isroot) {
                p = p.parent;
                if (p.id === pid) {
                    return true;
                }
            }
        }
        return false;
    };

    jm.node.is_node = function (n) {
        return !!n && n instanceof jm.node;
    };

    jm.node.prototype = {
        get_location: function () {
            var vd = this._data.view;
            return {
                x: vd.abs_x,
                y: vd.abs_y
            };
        },
        get_size: function () {
            var vd = this._data.view;
            return {
                w: vd.width,
                h: vd.height
            }
        }
    };


    jm.mind = function () {
        this.name = null;
        this.author = null;
        this.version = null;
        this.root = null;
        this.selected = null;
        this.nodes = {};
    };

    jm.mind.prototype = {
        get_node: function (nodeid) {
            if (nodeid in this.nodes) {
                return this.nodes[nodeid];
            } else {
                logger.warn('the node[id=' + nodeid + '] can not be found');
                return null;
            }
        },

        set_root: function (nodeid, topic, data) {
            if (this.root == null) {
                this.root = new jm.node(nodeid, 0, topic, data, true);
                this._put_node(this.root);
                return this.root;
            } else {
                logger.error('root node is already exist');
                return null;
            }
        },

        add_node: function (parent_node, nodeid, topic, data, direction, expanded, idx) {
            if (!jm.util.is_node(parent_node)) {
                logger.error('the parent_node ' + parent_node + ' is not a node.');
                return null;
            }
            var node_index = idx || -1;
            var node = new jm.node(nodeid, node_index, topic, data, false, parent_node, parent_node.direction, expanded);
            if (parent_node.isroot) {
                node.direction = direction || jm.direction.right;
            }
            if (this._put_node(node)) {
                parent_node.children.push(node);
                this._reindex(parent_node);
            } else {
                logger.error('fail, the nodeid \'' + node.id + '\' has been already exist.');
                node = null;
            }
            return node;
        },

        insert_node_before: function (node_before, nodeid, topic, data, direction) {
            if (!jm.util.is_node(node_before)) {
                logger.error('the node_before ' + node_before + ' is not a node.');
                return null;
            }
            var node_index = node_before.index - 0.5;
            return this.add_node(node_before.parent, nodeid, topic, data, direction, true, node_index);
        },

        get_node_before: function (node) {
            if (!jm.util.is_node(node)) {
                var the_node = this.get_node(node);
                if (!the_node) {
                    logger.error('the node[id=' + node + '] can not be found.');
                    return null;
                } else {
                    return this.get_node_before(the_node);
                }
            }
            if (node.isroot) { return null; }
            var idx = node.index - 2;
            if (idx >= 0) {
                return node.parent.children[idx];
            } else {
                return null;
            }
        },

        insert_node_after: function (node_after, nodeid, topic, data, direction) {
            if (!jm.util.is_node(node_after)) {
                logger.error('the node_after ' + node_after + ' is not a node.');
                return null;
            }
            var node_index = node_after.index + 0.5;
            return this.add_node(node_after.parent, nodeid, topic, data, direction, true, node_index);
        },

        get_node_after: function (node) {
            if (!jm.util.is_node(node)) {
                var the_node = this.get_node(node);
                if (!the_node) {
                    logger.error('the node[id=' + node + '] can not be found.');
                    return null;
                } else {
                    return this.get_node_after(the_node);
                }
            }
            if (node.isroot) { return null; }
            var idx = node.index;
            var brothers = node.parent.children;
            if (brothers.length > idx) {
                return node.parent.children[idx];
            } else {
                return null;
            }
        },

        move_node: function (node, before_id, parent_id, direction) {
            if (!jm.util.is_node(node)) {
                logger.error('the parameter node ' + node + ' is not a node.');
                return null;
            }
            if (!parent_id) {
                parent_id = node.parent.id;
            }
            return this._move_node(node, before_id, parent_id, direction);
        },

        _flow_node_direction: function (node, direction) {
            if (typeof direction === 'undefined') {
                direction = node.direction;
            } else {
                node.direction = direction;
            }
            var len = node.children.length;
            while (len--) {
                this._flow_node_direction(node.children[len], direction);
            }
        },

        _move_node_internal: function (node, beforeid) {
            if (!!node && !!beforeid) {
                if (beforeid == '_last_') {
                    node.index = -1;
                    this._reindex(node.parent);
                } else if (beforeid == '_first_') {
                    node.index = 0;
                    this._reindex(node.parent);
                } else {
                    var node_before = (!!beforeid) ? this.get_node(beforeid) : null;
                    if (node_before != null && node_before.parent != null && node_before.parent.id == node.parent.id) {
                        node.index = node_before.index - 0.5;
                        this._reindex(node.parent);
                    }
                }
            }
            return node;
        },

        _move_node: function (node, beforeid, parentid, direction) {
            if (!!node && !!parentid) {
                var parent_node = this.get_node(parentid)
                if (jm.node.inherited(node, parent_node)) {
                    logger.error('can not move a node to its children');
                    return null;
                }
                if (node.parent.id != parentid) {
                    // remove from parent's children
                    var sibling = node.parent.children;
                    var si = sibling.length;
                    while (si--) {
                        if (sibling[si].id == node.id) {
                            sibling.splice(si, 1);
                            break;
                        }
                    }
                    node.parent = parent_node;
                    parent_node.children.push(node);
                }

                if (node.parent.isroot) {
                    if (direction == jm.direction.left) {
                        node.direction = direction;
                    } else {
                        node.direction = jm.direction.right;
                    }
                } else {
                    node.direction = node.parent.direction;
                }
                this._move_node_internal(node, beforeid);
                this._flow_node_direction(node);
            }
            return node;
        },

        remove_node: function (node) {
            if (!jm.util.is_node(node)) {
                logger.error('the parameter node ' + node + ' is not a node.');
                return false;
            }
            if (node.isroot) {
                logger.error('fail, can not remove root node');
                return false;
            }
            if (this.selected != null && this.selected.id == node.id) {
                this.selected = null;
            }
            // clean all subordinate nodes
            var children = node.children;
            var ci = children.length;
            while (ci--) {
                this.remove_node(children[ci]);
            }
            // clean all children
            children.length = 0;
            // remove from parent's children
            var sibling = node.parent.children;
            var si = sibling.length;
            while (si--) {
                if (sibling[si].id == node.id) {
                    sibling.splice(si, 1);
                    break;
                }
            }
            // remove from global nodes
            delete this.nodes[node.id];
            // clean all properties
            for (var k in node) {
                delete node[k];
            }
            // remove it's self
            node = null;
            //delete node;
            return true;
        },

        _put_node: function (node) {
            if (node.id in this.nodes) {
                logger.warn('the nodeid \'' + node.id + '\' has been already exist.');
                return false;
            } else {
                this.nodes[node.id] = node;
                return true;
            }
        },

        _reindex: function (node) {
            if (node instanceof jm.node) {
                node.children.sort(jm.node.compare);
                for (var i = 0; i < node.children.length; i++) {
                    node.children[i].index = i + 1;
                }
            }
        },
    };

        ctx.jm = jm;
    };
});
