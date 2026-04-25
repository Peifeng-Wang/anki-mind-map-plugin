;(function (root, factory) {
    if (typeof module !== 'undefined' && module.exports) {
        module.exports = factory();
    } else {
        var installers = root.__jsMindModuleInstallers = root.__jsMindModuleInstallers || {};
        installers['data-provider'] = factory();
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

    jm.data_provider = function (jm) {
        this.jm = jm;
    };

    jm.data_provider.prototype = {
        init: function () {
            logger.debug('data.init');
        },

        reset: function () {
            logger.debug('data.reset');
        },

        load: function (mind_data) {
            var df = null;
            var mind = null;
            if (typeof mind_data === 'object') {
                if (!!mind_data.format) {
                    df = mind_data.format;
                } else {
                    df = 'node_tree';
                }
            } else {
                df = 'freemind';
            }

            if (df == 'node_array') {
                mind = jm.format.node_array.get_mind(mind_data);
            } else if (df == 'node_tree') {
                mind = jm.format.node_tree.get_mind(mind_data);
            } else if (df == 'freemind') {
                mind = jm.format.freemind.get_mind(mind_data);
            } else {
                logger.warn('unsupported format');
            }
            return mind;
        },

        get_data: function (data_format) {
            var data = null;
            if (data_format == 'node_array') {
                data = jm.format.node_array.get_data(this.jm.mind);
            } else if (data_format == 'node_tree') {
                data = jm.format.node_tree.get_data(this.jm.mind);
            } else if (data_format == 'freemind') {
                data = jm.format.freemind.get_data(this.jm.mind);
            } else {
                logger.error('unsupported ' + data_format + ' format');
            }
            return data;
        },
    };

    // ============= layout provider ===========================================

        ctx.jm = jm;
    };
});
