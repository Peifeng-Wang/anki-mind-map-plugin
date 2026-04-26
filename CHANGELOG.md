## [2.0.0] - 2026-01-25

### Added
- **Inter-Map Linking**: Implemented bi-directional linking between mind maps. Users can now right-click the root node to establish links to other mind map files.
- **New Node Relocation Strategy**: Added the ability to designate a Boundary as a "Target Zone." New nodes generated from card links will automatically be placed within this specific boundary.
- **Node Boundaries**: Introduced rectangular boundaries for visual grouping.
    - Select multiple nodes (Shift + Click) and use the context menu or shortcuts to create a boundary.
    - Right-click the boundary border to remove it.
- **Summary (Brace) Mode**: Added support for creating summary braces for multiple selected nodes.
    - *Note: Summary nodes are terminal and cannot support subsequent child nodes.*
- **Rich Text Formatting**: Enabled markdown-style formatting within nodes, including **Bold**, *Italic*, `Inline Code`, and Code Blocks.
- **Preview Window Pinning**: Added a "Pin" toggle to the preview window to prevent auto-closing.
- **Navigation Shortcuts**: Added keyboard shortcuts for quickly expanding and collapsing child nodes.

### Changed
- **Keyboard Navigation**: Refined the algorithm for keyboard-based node traversal to improve focus accuracy and user experience.
- **Visuals**: Optimized visual experience for navigating between nodes using arrow keys.

### Fixed
- Resolved inconsistencies and bugs related to the Zoom functionality.

## [1.1.0] - 2025-12-07

### Added
- Feature to **Enable/Disable Floating Nodes** in the configuration (`enable_floating_nodes`).
- New configuration settings for **Card Jump Mode**:
    - `jump_mode`: Determines action when clicking the card link badge (Options: `"preview"` or `"browser"`).
    - `preview_mode`: Controls content displayed in the preview window (Options: `"all"` content or just the `"front"` side).
- Added **Read-Only Mode** toggle in the Mind Map Editor menu for distraction-free viewing.

### Changed
- Optimized **Node Movement Logic** for smoother interaction and dragging.
- Optimized **Node Zoom Logic** (e.g., handling zoom in the view provider).
- Refined **Scrollbar Styles** for a modern, custom appearance.
- Updated various **Icons/Visual Indicators** within the Mind Map editor interface.

## [1.2.0] - 2026-4-26

### Added
- Added `quick_open_action` configuration. Users can now set `Ctrl + M` to either open the last active mind map (`last_mindmap`) or the mind map selection interface (`manager`).

### Changed
- Refactoring: Completed a large-scale architectural refactoring of the project.
- Optimization: Significantly improved overall system performance.