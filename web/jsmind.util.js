;(function (root, factory) {
    if (typeof module !== 'undefined' && module.exports) {
        module.exports = factory();
    } else {
        var installers = root.__jsMindModuleInstallers = root.__jsMindModuleInstallers || {};
        installers['util'] = factory();
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

    jm.util = {
        is_node: function (node) {
            return !!node && node instanceof jm.node;
        },
        ajax: {
            request: function (url, param, method, callback, fail_callback) {
                var a = jm.util.ajax;
                var p = null;
                var tmp_param = [];
                for (var k in param) {
                    tmp_param.push(encodeURIComponent(k) + '=' + encodeURIComponent(param[k]));
                }
                if (tmp_param.length > 0) {
                    p = tmp_param.join('&');
                }
                var xhr = new XMLHttpRequest();
                if (!xhr) { return; }
                xhr.onreadystatechange = function () {
                    if (xhr.readyState == 4) {
                        if (xhr.status == 200 || xhr.status == 0) {
                            if (typeof callback === 'function') {
                                var data = jm.util.json.string2json(xhr.responseText);
                                if (data != null) {
                                    callback(data);
                                } else {
                                    callback(xhr.responseText);
                                }
                            }
                        } else {
                            if (typeof fail_callback === 'function') {
                                fail_callback(xhr);
                            } else {
                                logger.error('xhr request failed.', xhr);
                            }
                        }
                    }
                }
                method = method || 'GET';
                xhr.open(method, url, true);
                xhr.setRequestHeader('If-Modified-Since', '0');
                if (method == 'POST') {
                    xhr.setRequestHeader('Content-Type', 'application/x-www-form-urlencoded;charset=utf-8');
                    xhr.send(p);
                } else {
                    xhr.send();
                }
            },
            get: function (url, callback) {
                return jm.util.ajax.request(url, {}, 'GET', callback);
            },
            post: function (url, param, callback) {
                return jm.util.ajax.request(url, param, 'POST', callback);
            }
        },

        dom: {
            //target,eventType,handler
            add_event: function (t, e, h) {
                if (!!t.addEventListener) {
                    t.addEventListener(e, h, false);
                } else {
                    t.attachEvent('on' + e, h);
                }
            }
        },

        file: {
            read: function (file_data, fn_callback) {
                var reader = new FileReader();
                reader.onload = function () {
                    if (typeof fn_callback === 'function') {
                        fn_callback(this.result, file_data.name);
                    }
                };
                reader.readAsText(file_data);
            },

            save: function (file_data, type, name) {
                var blob;
                if (typeof $w.Blob === 'function') {
                    blob = new Blob([file_data], { type: type });
                } else {
                    var BlobBuilder = $w.BlobBuilder || $w.MozBlobBuilder || $w.WebKitBlobBuilder || $w.MSBlobBuilder;
                    var bb = new BlobBuilder();
                    bb.append(file_data);
                    blob = bb.getBlob(type);
                }
                if (navigator.msSaveBlob) {
                    navigator.msSaveBlob(blob, name);
                } else {
                    var URL = $w.URL || $w.webkitURL;
                    var bloburl = URL.createObjectURL(blob);
                    var anchor = $c('a');
                    if ('download' in anchor) {
                        anchor.style.visibility = 'hidden';
                        anchor.href = bloburl;
                        anchor.download = name;
                        $d.body.appendChild(anchor);
                        var evt = $d.createEvent('MouseEvents');
                        evt.initEvent('click', true, true);
                        anchor.dispatchEvent(evt);
                        $d.body.removeChild(anchor);
                    } else {
                        location.href = bloburl;
                    }
                }
            }
        },

        json: {
            json2string: function (json) {
                return JSON.stringify(json);
            },
            string2json: function (json_str) {
                return JSON.parse(json_str);
            },
            merge: function (b, a) {
                for (var o in a) {
                    if (o in b) {
                        if (typeof b[o] === 'object' &&
                            Object.prototype.toString.call(b[o]).toLowerCase() == '[object object]' &&
                            !b[o].length) {
                            jm.util.json.merge(b[o], a[o]);
                        } else {
                            b[o] = a[o];
                        }
                    } else {
                        b[o] = a[o];
                    }
                }
                return b;
            }
        },

        uuid: {
            newid: function () {
                return (new Date().getTime().toString(16) + Math.random().toString(16).substring(2)).substring(2, 18);
            }
        },

        text: {
            is_empty: function (s) {
                if (!s) { return true; }
                return s.replace(/\s*/, '').length == 0;
            }
        }
    };

        ctx.jm = jm;
    };
});
