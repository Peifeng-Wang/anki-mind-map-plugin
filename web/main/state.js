var jm = null;
var autoSaveTimeout = null;
var autoSaveDelay = 2000;

var mindMapHistory = [];
var mindMapHistoryIndex = -1;
var maxHistory = 50;
var mindMapHistoryStateStrings = [];

var selectedNodes = [];
var isEditing = false;
var editingNodeId = null;
var selectionBox = null;
var isSelecting = false;
var selectionStart = { x: 0, y: 0 };

var arrows = [];
var arrowMode = false;
var arrowStart = null;

// Floating nodes (nodes without parent)
var floatingNodes = [];
var floatingNodeIdPrefix = 'floating_';

// Summary braces data
var summaryBraces = [];
var summaryBraceIdPrefix = 'summary_';
var braceColor = '#3b82f6';

// Boundary data
var boundaries = [];
var boundaryIdPrefix = 'boundary_';
var boundaryColor = '#ef4444';
var selectedBoundary = null;

// Track changed node IDs (for syncing to cards)
var changedNodes = new Set();
var overlayRenderTimer = null;
var overlayRenderRaf = null;
var overlayRenderTimer2 = null;
var overlayRenderRaf2 = null;
var scrollToNodeAnimToken = 0;
var scrollToNodeAnimRaf = null;
