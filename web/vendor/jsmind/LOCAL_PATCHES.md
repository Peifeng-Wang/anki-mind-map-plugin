# Local Patches against upstream jsMind

This add-on ships a forked copy of [jsMind](https://github.com/hizzgdev/jsmind/)
v0.5.7 (BSD licensed). The fork has been restructured to load cleanly inside
Anki's `AnkiWebView` (no relative script URLs at runtime; all assets inlined
by `mindmap_editor/assets.py`) and to expose internal helpers that the
add-on's own JS depends on.

Use this document as the source of truth when bumping upstream — every
section below is a divergence that must be re-applied.

> Detection methodology: greps for plugin-specific identifiers
> (`__jsMindModuleInstallers`, `VIEW_DRAG_*`, `_resolve_node`,
> `_require_editable`, iterative parent walks), structural cross-checks
> (single-file upstream vs. split modules), and the assertions in
> `tests/refactor_regression.test.js`.

## jsmind.js

- Replaced upstream's monolithic implementation with a thin **loader / bootstrap
  shim** that pulls in the split modules listed in `module_names`
  (`core`, `model`, `format`, `util`, `data-provider`, `layout-provider`,
  `view-provider`, `shortcut-plugin`).
- Introduces a shared **context object** (`create_context`) carrying
  `$w`/`$d`/`$g`/`$c`/`$t`/`$h`/`$i`/`logger`/`__name__`/`__version__`/
  `__author__` plus the `VIEW_DRAG_*` constants. Each split module receives
  this context instead of relying on closure scope inside one IIFE.
- Adds `VIEW_DRAG_INITIAL_BUFFER`, `VIEW_DRAG_EXPAND_THRESHOLD`,
  `VIEW_DRAG_EXPAND_SIZE` constants (lines ~56-58) used by
  `view-provider.js` for canvas auto-expansion while dragging — Anki users
  often drag past the initial canvas, and these knobs grow it.
- Browser bootstrap path (`else` branch around lines 115-141) injects
  `<script>` tags via `document.write` if any module installer is missing.
  This lets standalone usage of `jsmind.js` work without our Python loader,
  while Anki itself inlines every module via `assets.py` and never hits
  this path.
- CommonJS branch (lines 109-114) `require()`s the split modules so
  `tests/refactor_regression.test.js` can `require('jsmind.js')` under
  Node and exercise public API (used by the `jsMind split modules
  preserve compatibility entry and public API` test).

## jsmind.core.js

- Wrapped in a **UMD-style installer** (lines 1-26) that registers a factory
  on `__jsMindModuleInstallers['core']` instead of executing immediately.
  Same pattern in every `jsmind.<module>.js` file below.
- Added `_resolve_node(node)` helper (lines ~355-364): accepts either a
  node id or a `jsMind.node` instance and returns the resolved node. Logs
  via `logger.error` when an id is missing. Used by `add_node`,
  `update_node`, `remove_node`, and friends so the public API can take
  either form. Relied on by `tests/refactor_regression.test.js`
  ("jsMind internal helpers keep node resolution and editable
  semantics").
- Added `_require_editable(message)` helper (lines ~366-372): centralised
  the previously-duplicated `if (!this.get_editable()) { logger.error(...); return false; }`
  guard. Every editing entry point (`add_node`, `remove_node`,
  `update_node`, etc.) now calls it.

## jsmind.model.js

- Same UMD-style installer wrapper (lines 1-26) as `jsmind.core.js`.
- Otherwise tracks upstream's `Mind` model.

## jsmind.format.js

- Same UMD-style installer wrapper (lines 1-26).
- Hosts `format.node_tree`/`format.node_array`/`format.freemind`
  installers; checked by the regression suite which asserts
  `jsMind.format.node_tree.get_mind` is callable after install.

## jsmind.util.js

- Same UMD-style installer wrapper (lines 1-26).
- Hosts `util.is_node`, `util.uuid`, `util.text`, `util.json` (with
  `merge` referenced by the regression suite).

## jsmind.data-provider.js / jsmind.layout-provider.js / jsmind.shortcut-plugin.js

- Same UMD-style installer wrapper (lines 1-26).
- Otherwise track upstream behaviour.

## jsmind.view-provider.js

- Same UMD-style installer wrapper (lines 1-26).
- `clear()` (line ~110-113) uses `this.e_svg.textContent = '';` for batch
  SVG line clearing instead of upstream's per-child `removeChild` loop —
  measurably faster on large maps. Pinned by the
  `jsMind performance helpers keep equivalent lookup and clear behavior`
  regression test.
- `get_binded_nodeid` (lines ~212-223) and `is_node` (lines ~225-236)
  rewritten as **iterative parent walks** instead of recursive calls.
  Avoids stack-blowups on deeply nested DOM and makes the function
  inlineable; explicitly asserted by the regression suite.
- Canvas auto-expansion in the drag path (lines ~733-748) uses the
  `VIEW_DRAG_EXPAND_THRESHOLD`/`VIEW_DRAG_EXPAND_SIZE` constants from the
  shared context — without this, the editor canvas can't grow past its
  initial bounding box mid-drag.
- Initial canvas size uses `VIEW_DRAG_INITIAL_BUFFER` (lines ~281-282)
  so the editable area is comfortably larger than the visible viewport.

## jsmind.draggable.js

- Replaced upstream's monolithic draggable plugin with a **document.write
  loader** (lines 1-27) that injects script tags for the ten split
  draggable modules listed below. Header comment explicitly notes "Anki
  inlines the modules directly from mindmap_editor.py to avoid relying
  on relative script URLs."
- The split form lets `tests/refactor_regression.test.js` build the
  combined source via `draggableSource()` and exercise individual
  helpers (`_get_event_client_point`, `_clear_lookup_timer`,
  `_reset_drag_state`, `_reset_node_state`, `_set_canvas_line_style`,
  `_highlight_target_node`).

## jsmind.draggable.options.js / .canvas.js / .highlight.js / .shadow.js / .timer.js / .lookup.js / .autoscroll.js / .move.js / .events.js / .core.js

- New files; these are the split modules referenced by `jsmind.draggable.js`
  and `mindmap_editor/assets.py`. Together they reproduce the upstream
  draggable plugin.
- Each begins with the same UMD-style installer wrapper as the core
  modules.
- `.canvas.js::_set_canvas_line_style` pins `lineWidth: 5`, `strokeStyle:
  rgba(99, 102, 241, 0.6)`, `lineCap: round` (asserted by the regression
  suite).
- `.lookup.js::_get_event_client_point` falls back from `clientX`/
  `clientY` to `touches[0].clientX`/`clientY`, with `||` semantics that
  also fall through when the mouse coordinate is exactly `0` — pinned by
  the regression suite (`zeroFallbackPoint`).
- `.highlight.js::_highlight_target_node` short-circuits when the same
  element is re-targeted (regression suite asserts no extra
  `_clear_highlight` call on duplicate).
- `.timer.js::_clear_lookup_timer` accepts boolean flags for
  `clear_timeouts`/`clear_intervals` and resets `hlookup_delay`/
  `hlookup_timer` to `0` afterwards.

## jsmind.css

- Reduced to a **compatibility import entry** (lines 9-14): `@import`
  the six split CSS files (`jsmind-base.css`, `jsmind-overflow.css`,
  `jsmind-default.css`, `jsmind-responsive.css`,
  `jsmind-modern-premium.css`, `jsmind-classic-themes.css`). Order is
  load-bearing — pinned by the `CSS refactors keep non-empty rules and
  selected override ordering` regression test.

## jsmind-base.css / jsmind-overflow.css / jsmind-default.css / jsmind-responsive.css / jsmind-modern-premium.css / jsmind-classic-themes.css

- New files — the upstream `jsmind.css` cascade split into
  layered concerns (base reset, overflow handling, default theme,
  responsive media queries, the new "modern premium" theme, then the
  legacy classic theme palette set).
- The regression suite asserts no empty rule blocks (`{}`) survive the
  split, the merged `selected` override block stays after every
  `theme-* jmnode:hover` rule (so click-state wins), and the invalid
  `moz-user-select: -moz-none;` declaration is removed.
- Includes a custom `theme-modern-premium` and `theme-primary` palette
  not present upstream — hand-authored for the add-on's default look.
- All `transition: all` declarations were rewritten to enumerate the
  animated properties (the regression suite asserts zero remaining
  `transition: all` matches).
