window.MM = window.MM || {};

function swallowEvent(e) {
    e.preventDefault();
    e.stopPropagation();
    e.stopImmediatePropagation();
}

MM.state = {
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

    // Floating nodes (nodes without parent)
    floatingNodes: [],
    floatingNodeIdPrefix: 'floating_',
    selectedFloatingNode: null,

    // Summary braces data
    summaryBraces: [],
    summaryBraceIdPrefix: 'summary_',
    braceColor: '#3b82f6',

    // Boundary data
    boundaries: [],
    boundaryIdPrefix: 'boundary_',
    boundaryColor: '#ef4444',
    selectedBoundary: null,

    // Track changed node IDs (for syncing to cards)
    changedNodes: new Set(),
    overlayRenderTimer: null,
    overlayRenderRaf: null,
    overlayRenderTimer2: null,
    overlayRenderRaf2: null,
    scrollToNodeAnimToken: 0,
    scrollToNodeAnimRaf: null,

    // Hotkey configuration (defaults; merged with values from Python after main_js loads)
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

    // Pending callback for map selection
    pendingMapLinkCallback: null
};
