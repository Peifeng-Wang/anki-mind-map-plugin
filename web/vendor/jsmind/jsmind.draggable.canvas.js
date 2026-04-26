/**
 * jsMind draggable plugin canvas helpers.
 */
(function ($w) {
    'use strict';
    var parts = $w.jsMindDraggableParts = $w.jsMindDraggableParts || {};

    parts.canvas = {
        apply: function (proto, env) {
            var $d = env.document;
            var options = env.options;

            proto.resize = function () {
                this.jm.view.e_nodes.appendChild(this.shadow);
                this.e_canvas.width = this.jm.view.size.w;
                this.e_canvas.height = this.jm.view.size.h;
                this._set_canvas_line_style();
            };

            proto._create_canvas = function () {
                var c = $d.createElement('canvas');
                this.jm.view.e_panel.appendChild(c);
                var ctx = c.getContext('2d');
                this.e_canvas = c;
                this.canvas_ctx = ctx;
                this._set_canvas_line_style();
            };

            proto._clear_lines = function () {
                this.canvas_ctx.clearRect(0, 0, this.jm.view.size.w, this.jm.view.size.h);
            };

            proto._canvas_lineto = function (x1, y1, x2, y2) {
                this.canvas_ctx.beginPath();
                this.canvas_ctx.moveTo(x1, y1);
                this.canvas_ctx.lineTo(x2, y2);
                this.canvas_ctx.stroke();
            };

            proto._set_canvas_line_style = function () {
                this.canvas_ctx.lineWidth = options.line_width;
                this.canvas_ctx.strokeStyle = options.line_color;
                this.canvas_ctx.lineCap = 'round';
            };
        }
    };

    if (parts.tryInstall) {
        parts.tryInstall();
    }
})(window);
