const assert = require('node:assert');
const { execFileSync } = require('node:child_process');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');

const root = path.resolve(__dirname, '..');
const draggableModuleFiles = [
  'web/vendor/jsmind/jsmind.draggable.options.js',
  'web/vendor/jsmind/jsmind.draggable.canvas.js',
  'web/vendor/jsmind/jsmind.draggable.highlight.js',
  'web/vendor/jsmind/jsmind.draggable.shadow.js',
  'web/vendor/jsmind/jsmind.draggable.timer.js',
  'web/vendor/jsmind/jsmind.draggable.lookup.js',
  'web/vendor/jsmind/jsmind.draggable.autoscroll.js',
  'web/vendor/jsmind/jsmind.draggable.move.js',
  'web/vendor/jsmind/jsmind.draggable.events.js',
  'web/vendor/jsmind/jsmind.draggable.core.js'
];

function file(relPath) {
  return path.join(root, relPath);
}

function read(relPath) {
  return fs.readFileSync(file(relPath), 'utf8');
}

function readJsmindCssCascade() {
  const entry = read('web/vendor/jsmind/jsmind.css');
  const imports = [...entry.matchAll(/@import\s+url\("\.\/(jsmind-[^"]+\.css)"\);/g)]
    .map((match) => match[1]);
  return imports.map((name) => read(`web/vendor/jsmind/${name}`)).join('\n');
}

function readStyleCssCascade() {
  const entry = read('web/style.css');
  const imports = [...entry.matchAll(/@import\s+url\("styles\/(style-[^"]+\.css)"\);/g)]
    .map((match) => match[1]);
  return imports.map((name) => read(`web/styles/${name}`)).join('\n');
}

function editorModulePaths() {
  return fs.readdirSync(file('web/main'))
    .filter((name) => name.endsWith('.js'))
    .sort()
    .map((name) => `web/main/${name}`);
}

function editorMainSource() {
  return editorModulePaths().map(read).join('\n');
}

function draggableSource() {
  return draggableModuleFiles.map(read).join('\n');
}

function test(name, fn) {
  try {
    fn();
    console.log(`ok - ${name}`);
  } catch (error) {
    console.error(`not ok - ${name}`);
    throw error;
  }
}

function countMatches(text, pattern) {
  return (text.match(pattern) || []).length;
}

function decodeDataAsset(html, type) {
  const attr = `data-standalone-viewer-fallback="${type}"`;
  const tag = html.match(new RegExp(`<(?:script|link)[^>]*${attr}[^>]*>`));
  assert.ok(tag, `${type} fallback asset missing`);
  const urlAttr = type === 'js' ? 'src' : 'href';
  const mime = type === 'js' ? 'javascript' : 'css';
  const url = tag[0].match(new RegExp(`${urlAttr}="data:text\\/${mime};base64,([^"]+)"`));
  assert.ok(url, `${type} fallback data URL missing`);
  return Buffer.from(url[1], 'base64').toString('utf8');
}

function makeElement(id) {
  const classes = new Set(id === 'btnEn' ? ['active'] : []);
  return {
    id,
    children: [],
    listeners: {},
    style: {},
    innerHTML: '',
    textContent: '',
    value: '',
    files: [],
    classList: {
      toggle(name, enabled) {
        if (enabled) {
          classes.add(name);
        } else {
          classes.delete(name);
        }
      },
      contains(name) {
        return classes.has(name);
      }
    },
    addEventListener(type, handler) {
      this.listeners[type] = handler;
    },
    appendChild(child) {
      this.children.push(child);
      return child;
    },
    querySelector() {
      return null;
    },
    getBoundingClientRect() {
      return { left: 0, top: 0, width: 100, height: 100 };
    }
  };
}

test('JavaScript files parse successfully', () => {
  [
    'web/vendor/jsmind/jsmind.js',
    'web/vendor/jsmind/jsmind.draggable.js',
    'web/standalone_viewer/viewer.js',
    ...draggableModuleFiles,
    ...editorModulePaths()
  ].forEach((relPath) => {
    execFileSync(process.execPath, ['--check', file(relPath)], { stdio: 'pipe' });
  });
});

test('jsmind.draggable.js remains a compatibility loader for split draggable modules', () => {
  const loader = read('web/vendor/jsmind/jsmind.draggable.js');

  assert.ok(loader.includes('document.write'), 'jsmind.draggable.js should synchronously load split modules');
  draggableModuleFiles.forEach((relPath) => {
    assert.ok(loader.includes(relPath.replace('web/vendor/jsmind/', '')), `${relPath} missing from loader`);
  });
});

test('standalone viewer assets parse and bind controls', () => {
  const html = read('web/standalone_viewer.html');
  assert.strictEqual(countMatches(html, /\sonclick=/g), 0, 'inline onclick handlers should stay removed');
  assert.strictEqual(countMatches(html, /<style(?:\s[^>]*)?>/g), 0, 'viewer CSS should not stay inline');
  assert.strictEqual(countMatches(html, /<script>([\s\S]*?)<\/script>/g), 0, 'viewer JS should not stay inline');
  assert.ok(html.includes('href="./standalone_viewer/viewer.css"'), 'external viewer CSS entry missing');
  assert.ok(html.includes('src="./standalone_viewer/viewer.js"'), 'external viewer JS entry missing');
  assert.strictEqual(decodeDataAsset(html, 'css'), read('web/standalone_viewer/viewer.css'),
    'export fallback CSS must match the split viewer CSS');
  assert.strictEqual(decodeDataAsset(html, 'js'), read('web/standalone_viewer/viewer.js'),
    'export fallback JS must match the split viewer JS');

  const script = read('web/standalone_viewer/viewer.js');
  assert.ok(script.includes('const elements = {};'), 'fixed DOM reference cache should exist');
  assert.ok(script.includes('function cacheElements()'), 'cacheElements helper missing');
  assert.ok(script.includes('document.createDocumentFragment()'), 'mindmap selector should batch option appends');
  assert.ok(script.includes('global.AnkiMindMapViewer'), 'viewer fallback guard missing');
  new Function(script);

  const elements = Object.create(null);
  const document = {
    getElementById(id) {
      if (!elements[id]) {
        elements[id] = makeElement(id);
      }
      return elements[id];
    },
    querySelectorAll() {
      return [];
    },
    createElement(tag) {
      return makeElement(tag);
    },
    createDocumentFragment() {
      return makeElement('fragment');
    }
  };
  const storage = {
    values: Object.create(null),
    getItem(key) {
      return this.values[key] || null;
    },
    setItem(key, value) {
      this.values[key] = value;
    }
  };
  const context = {
    document,
    localStorage: storage,
    FileReader: function FileReader() {},
    jsMind: function jsMind() {},
    console,
    alert(message) {
      throw new Error(message);
    },
    window: {
      getComputedStyle() {
        return { fontSize: '16px' };
      }
    }
  };

  Function(...Object.keys(context), script)(...Object.values(context));
  assert.strictEqual(typeof context.window.AnkiMindMapViewer.switchLanguage, 'function');

  ['btnEn', 'btnCn', 'btnCenter', 'btnZoomIn', 'btnZoomOut'].forEach((id) => {
    assert.strictEqual(typeof elements[id].listeners.click, 'function', `${id} click handler missing`);
  });
  assert.strictEqual(typeof elements.fileInput.listeners.change, 'function', 'file input change handler missing');

  elements.btnCn.listeners.click();
  assert.strictEqual(storage.values.mindmap_viewer_lang, 'cn');
  assert.ok(elements.btnCn.classList.contains('active'));
  assert.ok(!elements.btnEn.classList.contains('active'));

  elements.btnEn.listeners.click();
  assert.strictEqual(storage.values.mindmap_viewer_lang, 'en');
  assert.ok(elements.btnEn.classList.contains('active'));
  assert.ok(!elements.btnCn.classList.contains('active'));
});

test('draggable helper methods preserve expected state transitions', () => {
  const script = draggableSource();
  const clearedTimeouts = [];
  const clearedIntervals = [];
  const windowMock = {
    document: {
      createElement(tag) {
        return {
          tagName: tag,
          style: {},
          appendChild() {},
          getContext() {
            return {};
          }
        };
      }
    },
    jsMind: {
      event_type: {
        resize: 1
      },
      plugin: function plugin(name, init) {
        this.name = name;
        this.init = init;
      },
      register_plugin() {},
      util: {
        dom: {
          add_event() {}
        }
      }
    },
    getSelection() {
      return { removeAllRanges() {} };
    },
    clearTimeout(id) {
      clearedTimeouts.push(id);
    },
    clearInterval(id) {
      clearedIntervals.push(id);
    },
    setTimeout() {
      return 1;
    },
    setInterval() {
      return 2;
    }
  };

  vm.runInNewContext(script, { window: windowMock });
  const draggable = new windowMock.jsMind.draggable({
    view: {
      e_panel: {},
      e_nodes: {},
      size: { w: 0, h: 0 }
    }
  });

  const mousePoint = draggable._get_event_client_point({ clientX: 10, clientY: 20 });
  assert.strictEqual(mousePoint.x, 10);
  assert.strictEqual(mousePoint.y, 20);
  const touchPoint = draggable._get_event_client_point({ touches: [{ clientX: 30, clientY: 40 }] });
  assert.strictEqual(touchPoint.x, 30);
  assert.strictEqual(touchPoint.y, 40);
  const zeroFallbackPoint = draggable._get_event_client_point({
    clientX: 0,
    clientY: 0,
    touches: [{ clientX: 5, clientY: 6 }]
  });
  assert.strictEqual(zeroFallbackPoint.x, 5, '0 x coordinate fallback must keep the previous || semantics');
  assert.strictEqual(zeroFallbackPoint.y, 6, '0 y coordinate fallback must keep the previous || semantics');

  let clearLinesCount = 0;
  draggable._clear_lines = function () {
    clearLinesCount += 1;
  };
  draggable.hlookup_delay = 11;
  draggable.hlookup_timer = 22;
  draggable._clear_lookup_timer(true, true);
  assert.deepStrictEqual(clearedTimeouts, [11]);
  assert.deepStrictEqual(clearedIntervals, [22]);
  assert.strictEqual(clearLinesCount, 2);
  assert.strictEqual(draggable.hlookup_delay, 0);
  assert.strictEqual(draggable.hlookup_timer, 0);

  draggable.view_panel_rect = {};
  draggable.moved = true;
  draggable.capture = true;
  draggable._reset_drag_state();
  assert.strictEqual(draggable.view_panel_rect, null);
  assert.strictEqual(draggable.moved, false);
  assert.strictEqual(draggable.capture, false);

  draggable.active_node = {};
  draggable.target_node = {};
  draggable.target_direct = 1;
  draggable._reset_node_state();
  assert.strictEqual(draggable.active_node, null);
  assert.strictEqual(draggable.target_node, null);
  assert.strictEqual(draggable.target_direct, null);

  draggable.canvas_ctx = {};
  draggable._set_canvas_line_style();
  assert.strictEqual(draggable.canvas_ctx.lineWidth, 5);
  assert.strictEqual(draggable.canvas_ctx.strokeStyle, 'rgba(99, 102, 241, 0.6)');
  assert.strictEqual(draggable.canvas_ctx.lineCap, 'round');

  let clearHighlightCount = 0;
  draggable._clear_highlight = function () {
    clearHighlightCount += 1;
  };
  const element = { style: {} };
  const node = { _data: { view: { element } } };
  draggable._highlight_target_node(node);
  assert.strictEqual(draggable.highlighted_element, element);
  assert.strictEqual(clearHighlightCount, 1);
  draggable._highlight_target_node(node);
  assert.strictEqual(clearHighlightCount, 1, 'same highlighted element should not be cleared and rewritten');
});

test('jsMind internal helpers keep node resolution and editable semantics', () => {
  const jsMind = require(file('web/vendor/jsmind/jsmind.js'));
  const instance = Object.create(jsMind.prototype);
  const resolved = { id: 'found' };
  instance.get_node = function (id) {
    return id === 'found' ? resolved : null;
  };

  assert.strictEqual(instance._resolve_node('found'), resolved);
  const directNode = new jsMind.node('direct', 0, 'direct topic', {}, false, null, jsMind.direction.right);
  assert.strictEqual(instance._resolve_node(directNode), directNode);
  const originalError = console.error;
  console.error = function () {};
  try {
    assert.strictEqual(instance._resolve_node('missing'), null);

    instance.get_editable = function () {
      return true;
    };
    assert.strictEqual(instance._require_editable(), true);

    instance.get_editable = function () {
      return false;
    };
    assert.strictEqual(instance._require_editable(), false);
  } finally {
    console.error = originalError;
  }
});

test('jsMind performance helpers keep equivalent lookup and clear behavior', () => {
  const jsMindSource = read('web/vendor/jsmind/jsmind.view-provider.js');
  assert.ok(jsMindSource.includes('this.e_svg.textContent = \'\';'), 'SVG clear should use batch textContent clearing');
  assert.ok(/get_binded_nodeid:\s*function \(element\) \{\s*while \(element != null\)/.test(jsMindSource),
    'get_binded_nodeid should use iterative parent lookup');
  assert.ok(/is_node:\s*function \(element\) \{\s*while \(element != null\)/.test(jsMindSource),
    'is_node should use iterative parent lookup');
});

test('jsMind split modules preserve compatibility entry and public API', () => {
  const entry = read('web/vendor/jsmind/jsmind.js');
  [
    'core',
    'model',
    'format',
    'util',
    'data-provider',
    'layout-provider',
    'view-provider',
    'shortcut-plugin'
  ].forEach((name) => {
    assert.ok(fs.existsSync(file(`web/vendor/jsmind/jsmind.${name}.js`)), `missing split module ${name}`);
    assert.ok(entry.includes(`'${name}'`), `entry should load ${name}`);
    execFileSync(process.execPath, ['--check', file(`web/vendor/jsmind/jsmind.${name}.js`)], { stdio: 'pipe' });
  });

  const jsMind = require(file('web/vendor/jsmind/jsmind.js'));
  assert.strictEqual(typeof jsMind, 'function');
  assert.strictEqual(typeof jsMind.format.node_tree.get_mind, 'function');
  assert.strictEqual(typeof jsMind.util.json.merge, 'function');
  assert.strictEqual(typeof jsMind.register_plugin, 'function');
  assert.strictEqual(jsMind.direction.right, 1);
});

test('main.js save refactor keeps expected structure', () => {
  const main = editorMainSource();
  assert.strictEqual(countMatches(main, /function focusNode\s*\(/g), 1, 'focusNode should only be defined once');
  ['collectFloatingNodesData', 'collectChangedNodesData', 'buildSavePayload'].forEach((name) => {
    assert.ok(main.includes(`function ${name}(`), `${name} helper missing`);
  });
  ['data', 'image_html', 'arrows', 'floatingNodes', 'summaryBraces', 'boundaries', 'changedNodes'].forEach((field) => {
    assert.ok(main.includes(`${field}:`), `save payload field ${field} missing`);
  });
  assert.strictEqual(countMatches(main, /pycmd\("save:" \+ JSON\.stringify\(payload\)\);/g), 2);
  assert.strictEqual(countMatches(main, /MM\.state\.changedNodes\.clear\(\);/g), 2);
  assert.ok(main.includes('function installUpdateNodeTracking('), 'update_node tracking installer missing');
  assert.ok(main.includes('_ankiMindMapTracksChanges'), 'update_node tracking guard missing');
  assert.strictEqual(countMatches(main, /installUpdateNodeTracking\(/g), 3,
    'installer should be defined and called from init and reload');
  assert.ok(main.includes('mindMapHistoryStateStrings: [],'), 'history string cache missing from MM.state');
  assert.ok(main.includes('MM.state.mindMapHistoryStateStrings[MM.state.mindMapHistoryIndex]'), 'history cache should be used for duplicate detection');
  assert.ok(main.includes('MM.state.mindMapHistoryStateStrings.push(currentStateStr);'), 'history cache should be updated when pushing history');
  assert.ok(main.includes('MM.state.mindMapHistoryStateStrings.shift();'), 'history cache should stay aligned when trimming history');
});

test('CSS refactors keep non-empty rules and selected override ordering', () => {
  const jsmindEntry = read('web/vendor/jsmind/jsmind.css');
  const jsmindImports = [...jsmindEntry.matchAll(/@import\s+url\("\.\/(jsmind-[^"]+\.css)"\);/g)]
    .map((match) => match[1]);
  assert.deepStrictEqual(jsmindImports, [
    'jsmind-base.css',
    'jsmind-overflow.css',
    'jsmind-default.css',
    'jsmind-responsive.css',
    'jsmind-modern-premium.css',
    'jsmind-classic-themes.css'
  ], 'jsmind.css import order should preserve the original cascade');
  assert.strictEqual(countMatches(jsmindEntry, /(?:^|\n)\s*(?!@import|\/|\*|\s*$)[^{@]+\{/g), 0,
    'jsmind.css should remain a compatibility import entry');

  const jsmindCss = readJsmindCssCascade();
  assert.strictEqual(countMatches(jsmindCss, /\{\s*\}/g), 0, 'empty CSS rules should be removed');
  const selectedIndex = jsmindCss.indexOf('jmnodes.theme-warning jmnode.selected,');
  const lastHoverIndex = jsmindCss.indexOf('jmnodes.theme-asbestos jmnode:hover');
  assert.ok(selectedIndex > lastHoverIndex, 'merged selected block must stay after theme hover rules');
  ['primary jmnode.selected', 'modern-premium jmnode.selected'].forEach((selectorPart) => {
    assert.ok(jsmindCss.includes(selectorPart), `${selectorPart} must not be merged away`);
  });
  assert.ok(!jsmindCss.includes('moz-user-select: -moz-none;'), 'invalid moz-user-select declaration should stay removed');
  assert.strictEqual(countMatches(jsmindCss, /transition:\s*all/g), 0, 'jsmind.css should not use transition: all');

  const styleEntry = read('web/style.css');
  const styleImports = [...styleEntry.matchAll(/@import\s+url\("styles\/(style-[^"]+\.css)"\);/g)]
    .map((match) => match[1]);
  assert.deepStrictEqual(styleImports, [
    'style-base.css',
    'style-interactions.css',
    'style-link-indicators.css',
    'style-structure.css',
    'style-node-content.css'
  ], 'style.css import order should preserve the original cascade');
  assert.strictEqual(countMatches(styleEntry, /(?:^|\n)\s*(?!@import|\/|\*|\s*$)[^{@]+\{/g), 0,
    'style.css should remain a compatibility import entry');

  const styleCss = readStyleCssCascade();
  assert.ok(styleCss.includes('jmnode[data-has-card="true"]::after,\n' +
    'jmnode[data-is-map-link="true"]::before,\n' +
    'jmnode[data-has-linked-maps="true"]::before'), 'badge common selector group missing');
  ['position: absolute;', 'top: -10px;', 'width: 24px;', 'height: 24px;',
    'animation: link-bounce 3s ease-in-out infinite;'].forEach((declaration) => {
    assert.ok(styleCss.includes(declaration), `badge common declaration ${declaration} missing`);
  });
  const cardContent = styleCss.match(/jmnode\[data-has-card="true"\]::after \{[\s\S]*?content: "([^"]+)";/);
  assert.ok(cardContent, 'card link indicator content missing');
  assert.strictEqual(cardContent[1].codePointAt(0), 0x1F517, 'card link indicator must still render the link icon');
  assert.ok(styleCss.includes('font-size: 26px !important;'), 'modern-premium font-size override missing');
  assert.ok(styleCss.includes('font-weight: 700 !important;'), 'base map-link font weight missing');
  assert.ok(styleCss.includes('padding: 18px 32px !important;'), 'base map-link padding missing');
  assert.strictEqual(countMatches(styleCss, /transition:\s*all/g), 0, 'style.css should not use transition: all');
});

test('DOMPurify is vendored and wired into the rich-text topic render path', () => {
  const dompurifyPath = 'web/vendor/dompurify/dompurify.min.js';
  assert.ok(fs.existsSync(file(dompurifyPath)), 'DOMPurify vendor file missing');

  const dompurify = read(dompurifyPath);
  const sizeKb = Buffer.byteLength(dompurify, 'utf8') / 1024;
  assert.ok(sizeKb > 10 && sizeKb < 80,
    `DOMPurify size out of expected range (~25 KB minified), got ${sizeKb.toFixed(1)} KB`);
  assert.ok(dompurify.startsWith('/*! @license DOMPurify'),
    'DOMPurify file should start with the upstream license header');
  assert.ok(/\bsanitize\b/.test(dompurify), 'DOMPurify should expose a sanitize identifier');

  // Sanity check: the syntax should parse so we don't ship a broken minified file.
  execFileSync(process.execPath, ['--check', file(dompurifyPath)], { stdio: 'pipe' });

  const nodeEditor = read('web/main/node_editor.js');
  assert.ok(nodeEditor.includes('DOMPurify.sanitize'),
    'node_editor.js should call DOMPurify.sanitize on the rich-text topic path');
  assert.ok(nodeEditor.includes('sanitizeTopicHtml('),
    'node_editor.js should route innerHTML writes through sanitizeTopicHtml');
  assert.ok(!/TODO:?\s*topic may contain rich-text/i.test(nodeEditor),
    'P0 sanitize TODO should be resolved in node_editor.js');

  // floating_nodes.js still owns the plain-text path; it must keep using escapeHtml,
  // not switch to the rich-text DOMPurify pipeline.
  const floatingNodes = read('web/main/floating_nodes.js');
  assert.ok(floatingNodes.includes('escapeHtml'),
    'floating_nodes.js should keep escapeHtml for plain-text topics');
});

test('MathJax is vendored locally and assets.py references the local path', () => {
  const mathjaxPath = 'web/vendor/mathjax/es5/tex-svg.js';
  assert.ok(fs.existsSync(file(mathjaxPath)), 'MathJax vendor file missing');

  const mathjax = read(mathjaxPath);
  const sizeKb = Buffer.byteLength(mathjax, 'utf8') / 1024;
  assert.ok(sizeKb > 1500 && sizeKb < 2500,
    `MathJax bundle size out of expected range, got ${sizeKb.toFixed(1)} KB`);
  assert.ok(mathjax.includes('MathJax'), 'MathJax file should contain the MathJax identifier');

  // Syntax sanity: make sure it parses so we don't ship a broken file.
  execFileSync(process.execPath, ['--check', file(mathjaxPath)], { stdio: 'pipe' });

  const assets = read('mindmap_editor/assets.py');
  assert.ok(assets.includes('vendor/mathjax/es5/tex-svg.js'),
    'assets.py should reference the local MathJax path');
  assert.ok(!assets.includes('cdn.jsdelivr.net/npm/mathjax'),
    'assets.py should no longer use the CDN MathJax URL');
});

// ---------- Sandbox helper for web/main/*.js unit tests ----------
function runMainJsInSandbox(files) {
  const documentMock = {
    getElementById() { return null; },
    querySelector() { return null; },
    querySelectorAll() { return []; },
    createElement(tag) {
      return {
        tagName: tag,
        style: {},
        classList: { add() {}, remove() {}, toggle() {}, contains() { return false; } },
        appendChild() {},
        addEventListener() {},
        removeEventListener() {},
        setAttribute() {},
        getAttribute() { return null; },
        getBoundingClientRect() { return { width: 0, height: 0, left: 0, top: 0, right: 0, bottom: 0 }; },
        closest() { return null; },
        contains() { return false; },
        isConnected: true,
        children: [],
        childNodes: [],
        parentElement: null,
        parentNode: null,
        querySelector() { return null; },
        querySelectorAll() { return []; },
        scrollIntoView() {},
        innerHTML: '',
        textContent: '',
        value: '',
        id: '',
        files: [],
        focus() {},
        select() {},
      };
    },
    createElementNS(ns, tag) { return this.createElement(tag); },
    createDocumentFragment() { return { appendChild() {}, children: [] }; },
    addEventListener() {},
    removeEventListener() {},
    body: { appendChild() {}, removeChild() {}, children: [] },
  };

  const sandbox = {
    getComputedStyle() { return { fontSize: '16px', fontFamily: 'sans-serif', fontWeight: '400' }; },
    getSelection() { return { removeAllRanges() {} }; },
    addEventListener() {},
    removeEventListener() {},
    requestAnimationFrame() { return 0; },
    cancelAnimationFrame() {},
    scrollTo() {},
    clipboardData: undefined,
    document: documentMock,
    navigator: { clipboard: undefined },
    console,
    setTimeout: (fn, ms) => { if (fn) fn(); return 0; },
    clearTimeout() {},
    setInterval: (fn, ms) => { if (fn) fn(); return 0; },
    clearInterval() {},
    Date,
    JSON,
    Math,
    parseInt,
    parseFloat,
    isNaN,
    isFinite,
    Number,
    String,
    Array,
    Object,
    RegExp,
    Error,
    TypeError,
    RangeError,
    Uint8Array,
    Buffer,
    ArrayBuffer,
    Map,
    Set,
    WeakMap,
    WeakSet,
    Symbol,
    Promise,
    Reflect,
    Proxy,
    Intl,
    require,
    module: {},
    exports: {},
    alert: console.warn,
  };

  // window === globalThis === sandbox (just like a real browser)
  sandbox.window = sandbox;
  sandbox.global = sandbox;
  sandbox.document = documentMock;

  sandbox.DOMPurify = {
    sanitize(html, opts) {
      if (opts && opts.ALLOWED_TAGS) {
        return String(html).replace(/<[^>]*>/g, '');
      }
      return html;
    }
  };
  sandbox.MathJax = { typesetPromise() { return Promise.resolve(); } };
  sandbox.pycmd = function(cmd) {};

  function MockNode(id, index, topic, data, isroot, parent, direction) {
    this.id = id;
    this.index = index;
    this.topic = topic;
    this.data = data || {};
    this.isroot = isroot || false;
    this.parent = parent;
    this.direction = direction;
    this.children = [];
    this.expanded = true;
    this._data = { view: { element: null, abs_x: 0, abs_y: 0, width: 100, height: 40 } };
  }

  sandbox.jsMind = function(options) { this.options = options; };
  sandbox.jsMind.prototype = {
    get_node(id) { return this._nodes && this._nodes[id] || null; },
    get_root() { return this._root || null; },
    get_selected_node() { return this._selected || null; },
    select_node() {},
    select_clear() {},
    show() {},
    get_data() { return { data: this._root }; },
    get_editable() { return true; },
    update_node() {},
    remove_node() {},
    expand_node() {},
    collapse_node() {},
    toggle_node() {},
    is_node_visible() { return true; },
    add_node(parent, id, topic) {
      const node = new MockNode(id, 0, topic, {}, false, parent ? parent.id : null);
      if (!this._nodes) this._nodes = {};
      this._nodes[id] = node;
      return node;
    },
    disable_edit() {},
    enable_edit() {},
    view: { e_panel: { scrollLeft: 0, scrollTop: 0 }, e_nodes: {}, actualZoom: 1 },
    direction: { right: 1, left: 2 },
  };
  sandbox.jsMind.event_type = { resize: 1, mousedown: 2, click: 3, dblclick: 4 };
  sandbox.jsMind.util = { dom: { add_event() {} }, json: { merge() {} }, uuid: {} };
  sandbox.jsMind.register_plugin = function() {};
  sandbox.jsMind.format = { node_tree: { get_mind() {} } };

  sandbox.MM = { state: {
    jm: null,
    autoSaveTimeout: null,
    autoSaveDelay: 2000,
    mindMapHistory: [],
    mindMapHistoryIndex: -1,
    maxHistory: 50,
    mindMapHistoryStateStrings: [],
    selectedNodes: [],
    isEditing: false,
    editingNodeId: null,
    selectionBox: null,
    isSelecting: false,
    selectionStart: { x: 0, y: 0 },
    arrows: [],
    arrowMode: false,
    arrowStart: null,
    floatingNodes: [],
    floatingNodeIdPrefix: 'floating_',
    selectedFloatingNode: null,
    summaryBraces: [],
    summaryBraceIdPrefix: 'summary_',
    braceColor: '#3b82f6',
    boundaries: [],
    boundaryIdPrefix: 'boundary_',
    boundaryColor: '#ef4444',
    selectedBoundary: null,
    changedNodes: new Set(),
    overlayRenderTimer: null,
    overlayRenderRaf: null,
    overlayRenderTimer2: null,
    overlayRenderRaf2: null,
    scrollToNodeAnimToken: 0,
    scrollToNodeAnimRaf: null,
    hotkeyConfig: {
      save: 'Ctrl+S',
      refresh: 'F5',
      focus_root: 'Ctrl+R',
      create_summary: 'Ctrl+Shift+S',
      create_boundary: 'Ctrl+Shift+B',
      bold: 'Ctrl+B',
      italic: 'Ctrl+I',
      inline_code: 'Ctrl+`',
      code_block: 'Ctrl+Shift+`',
      toggle_collapse: '`'
    },
    pendingMapLinkCallback: null
  }};

  const source = (files || [
    'web/main/state.js',
    'web/main/jsmind_dom.js',
    'web/main/hotkeys.js',
    'web/main/ui_feedback.js',
    'web/main/text_formatting.js',
    'web/main/mathjax.js',
    'web/main/node_editor.js',
    'web/main/persistence.js',
    'web/main/summary_braces_dom.js',
    'web/main/boundaries.js',
  ]).map(read).join('\n');

  vm.runInNewContext(source, sandbox);
  return sandbox;
}

// ---------- Structural regression tests ----------

test('CSS refactor classes used in JS are defined in style-interactions.css', () => {
  const css = readStyleCssCascade();
  const main = editorMainSource();
  const cssClasses = [...css.matchAll(/\.(mm-[a-z0-9-]+)/g)].map((m) => m[1]);
  assert.ok(cssClasses.length > 0, 'should find mm- classes in CSS');
  cssClasses.forEach((cls) => {
    assert.ok(main.includes(`'${cls}'`) || main.includes(`"${cls}"`),
      `CSS class .${cls} should be referenced in main JS`);
  });
});

test('swallowEvent exists and prevents propagation', () => {
  const sandbox = runMainJsInSandbox(['web/main/state.js']);
  assert.strictEqual(typeof sandbox.swallowEvent, 'function', 'swallowEvent should be defined');
  let prevented = false;
  let stopped = false;
  let stoppedImmediate = false;
  const e = {
    preventDefault() { prevented = true; },
    stopPropagation() { stopped = true; },
    stopImmediatePropagation() { stoppedImmediate = true; }
  };
  sandbox.swallowEvent(e);
  assert.ok(prevented, 'should call preventDefault');
  assert.ok(stopped, 'should call stopPropagation');
  assert.ok(stoppedImmediate, 'should call stopImmediatePropagation');
});

// ---------- Pure logic unit tests ----------

test('countNodes recursively counts nodes', () => {
  const sandbox = runMainJsInSandbox(['web/main/mathjax.js']);
  assert.strictEqual(sandbox.countNodes({ id: 'root', children: [] }), 1);
  assert.strictEqual(sandbox.countNodes({ id: 'root', children: [{ id: 'a' }, { id: 'b' }] }), 3);
  assert.strictEqual(sandbox.countNodes({ id: 'root', children: [{ id: 'a', children: [{ id: 'aa' }] }] }), 3);
});

test('matchHotkey correctly matches hotkey strings', () => {
  const sandbox = runMainJsInSandbox(['web/main/state.js', 'web/main/hotkeys.js']);
  const mk = sandbox.matchHotkey;
  assert.ok(mk({ key: 's', ctrlKey: true, metaKey: false, shiftKey: false, altKey: false }, 'Ctrl+S'));
  assert.ok(mk({ key: 'S', ctrlKey: true, metaKey: false, shiftKey: true, altKey: false }, 'Ctrl+Shift+S'));
  assert.ok(!mk({ key: 's', ctrlKey: false, metaKey: false, shiftKey: false, altKey: false }, 'Ctrl+S'));
  assert.ok(mk({ key: '~', ctrlKey: false, metaKey: false, shiftKey: true, altKey: false }, 'Shift+`'));
  assert.ok(mk({ key: 'F5', ctrlKey: false, metaKey: false, shiftKey: false, altKey: false }, 'F5'));
  assert.ok(!mk({ key: 'f5', ctrlKey: false, metaKey: false, shiftKey: false, altKey: false }, 'F5'));
});

test('escapeHtml escapes HTML entities', () => {
  const sandbox = runMainJsInSandbox(['web/main/ui_feedback.js']);
  assert.strictEqual(sandbox.escapeHtml('<script>'), '&lt;script&gt;');
  assert.strictEqual(sandbox.escapeHtml('"test"'), '&quot;test&quot;');
  assert.strictEqual(sandbox.escapeHtml("it's"), 'it&#039;s');
  assert.strictEqual(sandbox.escapeHtml('&'), '&amp;');
});

test('escapeCodeTagsForDisplay escapes inside code tags', () => {
  const sandbox = runMainJsInSandbox(['web/main/ui_feedback.js', 'web/main/text_formatting.js']);
  const out = sandbox.escapeCodeTagsForDisplay('<code><script>alert(1)</script></code>');
  assert.ok(!out.includes('<script>'), 'script tag inside code should be escaped');
  assert.ok(out.includes('<code>'), 'outer code tag should remain');
  assert.ok(out.includes('alert(1)'), 'content should survive');
});

test('sanitizeTopicHtml falls back to tag stripping without DOMPurify', () => {
  const sandbox = runMainJsInSandbox(['web/main/node_editor.js']);
  delete sandbox.DOMPurify;
  const out = sandbox.sanitizeTopicHtml('<b>bold</b><script>evil</script>');
  assert.ok(!out.includes('<script>'), 'script tag should be stripped');
  assert.ok(!out.includes('<b>'), 'all tags should be stripped in fallback');
  assert.ok(out.includes('bold'), 'text content should survive');
});

test('toggleWrapSelection wraps and unwraps textarea content', () => {
  const sandbox = runMainJsInSandbox(['web/main/text_formatting.js']);
  function makeTextarea(value, start, end) {
    return { value, selectionStart: start, selectionEnd: end };
  }
  const ta = makeTextarea('hello world', 0, 11);
  sandbox.toggleWrapSelection(ta, '<b>', '</b>');
  assert.strictEqual(ta.value, '<b>hello world</b>');
  assert.strictEqual(ta.selectionStart, 3);
  assert.strictEqual(ta.selectionEnd, 14);
  // unwrap
  sandbox.toggleWrapSelection(ta, '<b>', '</b>');
  assert.strictEqual(ta.value, 'hello world');
});

test('validateSummarySelection validates node selection', () => {
  const sandbox = runMainJsInSandbox(['web/main/state.js', 'web/main/summary_braces_dom.js']);
  sandbox.MM.state.selectedNodes = [];
  let result = sandbox.validateSummarySelection();
  assert.strictEqual(result.valid, false);
  assert.ok(result.reason.includes('2'));

  const el1 = { getAttribute: () => 'n1' };
  const el2 = { getAttribute: () => 'n2' };
  sandbox.MM.state.selectedNodes = [el1, el2];

  sandbox.MM.state.jm = {
    get_node(id) {
      if (id === 'n1') return { id: 'n1', isroot: false, parent: 'p1', data: {} };
      if (id === 'n2') return { id: 'n2', isroot: false, parent: 'p1', data: {} };
      if (id === 'p1') return { id: 'p1', isroot: false, parent: 'root', data: {} };
      return null;
    }
  };
  result = sandbox.validateSummarySelection();
  assert.strictEqual(result.valid, true);
  assert.strictEqual(result.nodes.length, 2);
});

test('validateBoundarySelection validates boundary selection', () => {
  const sandbox = runMainJsInSandbox(['web/main/state.js', 'web/main/boundaries.js']);
  sandbox.MM.state.selectedNodes = [];
  let result = sandbox.validateBoundarySelection();
  assert.strictEqual(result.valid, false);
  assert.ok(result.reason.includes('1'));

  const el1 = { getAttribute: () => 'n1' };
  sandbox.MM.state.selectedNodes = [el1];
  sandbox.MM.state.jm = {
    get_node(id) {
      if (id === 'n1') return { id: 'n1', isroot: false, parent: 'p1', data: {} };
      return null;
    }
  };
  result = sandbox.validateBoundarySelection();
  assert.strictEqual(result.valid, true);
  assert.strictEqual(result.nodes.length, 1);
});

test('hasSpecialBoundary detects special boundaries', () => {
  const sandbox = runMainJsInSandbox(['web/main/state.js', 'web/main/boundaries.js']);
  sandbox.MM.state.boundaries = [];
  assert.strictEqual(sandbox.hasSpecialBoundary(), false);
  sandbox.MM.state.boundaries = [{ id: 'b1', isSpecial: false }];
  assert.strictEqual(sandbox.hasSpecialBoundary(), false);
  sandbox.MM.state.boundaries = [{ id: 'b1', isSpecial: true }];
  assert.strictEqual(sandbox.hasSpecialBoundary(), true);
});

test('collectFloatingNodesData maps floating nodes', () => {
  const sandbox = runMainJsInSandbox(['web/main/state.js', 'web/main/persistence.js']);
  sandbox.MM.state.floatingNodes = [
    { id: 'f1', topic: 'A', x: 10, y: 20 },
    { id: 'f2', topic: 'B', x: 30, y: 40, extra: 'ignored' }
  ];
  const result = sandbox.collectFloatingNodesData();
  assert.strictEqual(result.length, 2);
  assert.strictEqual(JSON.stringify(result[0]), JSON.stringify({ id: 'f1', topic: 'A', x: 10, y: 20 }));
  assert.strictEqual(JSON.stringify(result[1]), JSON.stringify({ id: 'f2', topic: 'B', x: 30, y: 40 }));
  assert.strictEqual(result[1].extra, undefined);
});

console.log('All refactor regression tests passed.');
