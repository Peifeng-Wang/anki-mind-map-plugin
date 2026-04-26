/**
 * jsMind draggable plugin auto-scroll behavior.
 */
(function ($w) {
    'use strict';
    var parts = $w.jsMindDraggableParts = $w.jsMindDraggableParts || {};

    parts.autoscroll = {
        apply: function (proto, env) {
            var options = env.options;

            proto._scroll_view_panel = function (e, jview) {
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
            };
        }
    };

    if (parts.tryInstall) {
        parts.tryInstall();
    }
})(window);
