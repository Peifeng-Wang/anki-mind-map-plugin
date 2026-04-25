/**
 * @license BSD
 * @copyright 2014-2023 hizzgdev@163.com
 *
 * Project Home:
 *   https://github.com/hizzgdev/jsmind/
 */

; (function ($w) {
    'use strict';
    var __name__ = 'jsMind';
    var __version__ = '0.5.7';
    var __author__ = 'hizzgdev@163.com';

    var _noop = function () { };
    var logger = (typeof console === 'undefined') ? {
        log: _noop, debug: _noop, error: _noop, warn: _noop, info: _noop
    } : console;

    var module_names = [
        'core',
        'model',
        'format',
        'util',
        'data-provider',
        'layout-provider',
        'view-provider',
        'shortcut-plugin'
    ];

    function already_loaded() {
        if (typeof module === 'undefined' || !module.exports) {
            if (typeof $w[__name__] != 'undefined') {
                logger.log(__name__ + ' has been already exist.');
                return true;
            }
        }
        return false;
    }

    var $d = $w.document;
    var $g = function (id) { return $d.getElementById(id); };
    var $c = function (tag) { return $d.createElement(tag); };
    var $t = function (n, t) { if (n.hasChildNodes()) { n.firstChild.nodeValue = t; } else { n.appendChild($d.createTextNode(t)); } };

    var $h = function (n, t) {
        if (t instanceof HTMLElement) {
            n.innerHTML = '';
            n.appendChild(t);
        } else {
            n.innerHTML = t;
        }
    };
    var $i = function (el) { return !!el && (typeof el === 'object') && (el.nodeType === 1) && (typeof el.style === 'object') && (typeof el.ownerDocument === 'object'); };
    if (typeof String.prototype.startsWith != 'function') { String.prototype.startsWith = function (p) { return this.slice(0, p.length) === p; }; }
    var VIEW_DRAG_INITIAL_BUFFER = 2000;
    var VIEW_DRAG_EXPAND_THRESHOLD = 200;
    var VIEW_DRAG_EXPAND_SIZE = 2000;

    function create_context() {
        return {
            $w: $w,
            $d: $d,
            $g: $g,
            $c: $c,
            $t: $t,
            $h: $h,
            $i: $i,
            logger: logger,
            __name__: __name__,
            __version__: __version__,
            __author__: __author__,
            VIEW_DRAG_INITIAL_BUFFER: VIEW_DRAG_INITIAL_BUFFER,
            VIEW_DRAG_EXPAND_THRESHOLD: VIEW_DRAG_EXPAND_THRESHOLD,
            VIEW_DRAG_EXPAND_SIZE: VIEW_DRAG_EXPAND_SIZE,
            jm: null
        };
    }

    function install_modules(installers) {
        var ctx = create_context();
        for (var i = 0; i < module_names.length; i++) {
            var installer = installers[module_names[i]];
            if (typeof installer !== 'function') {
                throw new Error('jsMind module missing: ' + module_names[i]);
            }
            installer(ctx);
        }
        return ctx.jm;
    }

    function export_jsmind(jm) {
        if (typeof module !== 'undefined' && typeof exports === 'object') {
            module.exports = jm;
        } else if (typeof define === 'function' && (define.amd || define.cmd)) {
            define(function () { return jm; });
        } else {
            $w[__name__] = jm;
        }
    }

    function bootstrap(installers) {
        if (already_loaded()) { return null; }
        var jm = install_modules(installers);
        export_jsmind(jm);
        return jm;
    }

    if (typeof module !== 'undefined' && module.exports) {
        var installers = {};
        for (var i = 0; i < module_names.length; i++) {
            installers[module_names[i]] = require('./jsmind.' + module_names[i] + '.js');
        }
        bootstrap(installers);
    } else {
        var browser_installers = $w.__jsMindModuleInstallers || {};
        var missing = [];
        for (var j = 0; j < module_names.length; j++) {
            if (typeof browser_installers[module_names[j]] !== 'function') {
                missing.push(module_names[j]);
            }
        }
        if (missing.length === 0) {
            bootstrap(browser_installers);
        } else if ($d && $d.write) {
            var scripts = $d.getElementsByTagName('script');
            var current = $d.currentScript || scripts[scripts.length - 1];
            var base = current && current.src ? current.src.replace(/[^\/]*$/, '') : '';
            var callback = '__jsMindBootstrap' + String(new Date().getTime()) + String(Math.random()).replace(/\D/g, '');
            $w[callback] = function () {
                bootstrap($w.__jsMindModuleInstallers || {});
                try { delete $w[callback]; } catch (e) { $w[callback] = undefined; }
            };
            for (var k = 0; k < missing.length; k++) {
                $d.write('<script src="' + base + 'jsmind.' + missing[k] + '.js"><\/script>');
            }
            $d.write('<script>' + callback + '();<\/script>');
        } else {
            throw new Error('jsMind modules must be loaded before web/jsmind.js');
        }
    }
})(typeof window !== 'undefined' ? window : (typeof global !== 'undefined' ? global : this));
