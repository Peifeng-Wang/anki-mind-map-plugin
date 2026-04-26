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
    'web/main.js',
    'web/standalone_viewer/viewer.js',
    ...draggableModuleFiles,
    ...editorModulePaths()
  ].forEach((relPath) => {
    execFileSync(process.execPath, ['--check', file(relPath)], { stdio: 'pipe' });
  });
});

test('main.js remains a compatibility loader for split editor modules', () => {
  const loader = read('web/main.js');
  const modulePaths = editorModulePaths();

  assert.ok(loader.includes('document.write'), 'main.js should synchronously load split modules');
  assert.strictEqual(modulePaths.length, 23, 'expected focused editor modules');
  modulePaths.forEach((relPath) => {
    assert.ok(loader.includes(relPath.replace('web/', '')), `${relPath} missing from loader`);
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

console.log('All refactor regression tests passed.');
