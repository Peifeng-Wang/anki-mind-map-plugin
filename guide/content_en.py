def get_english_sidebar():
    return """
    <h2>Contents</h2>
    <a href="#quick-start" class="nav-link">&#9889; Quick Start</a>
    <a href="#setup-sync" class="nav-link">&#9729; Sync Setup</a>
    <a href="#operations" class="nav-link">&#9733; Operations</a>
    <a href="#card-linking" class="nav-link">&#8644; Card Linking</a>
    <a href="#config" class="nav-link">&#9881; Configuration</a>
    <a href="#advanced" class="nav-link">&#9632; Advanced</a>
    <a href="#backup" class="nav-link">&#9851; Backup</a>
    """


def get_english_body():
    return """
    <h1>&#9733; Mind Map Plugin Guide</h1>
    <div id="quick-start" class="feature">
        <h2 style="margin-top:0;">&#9889; Quick Start Workflow</h2>
        <ol>
            <li><strong>Create Map:</strong> Go to <code>Tools &rarr; Mind Map &rarr; Mind Map Manager</code>, then click <strong>New</strong>.</li>
            <li><strong>Link Card:</strong> Open the Add window or Browser, click the <strong>MM</strong> toolbar button, and choose a map.</li>
            <li><strong>Edit Content:</strong> Edit the first line of the card Front field; it becomes the linked node text.</li>
            <li><strong>Refresh:</strong> Return to the mind map editor and press <strong>F5</strong>.</li>
            <li><strong>Navigate:</strong> Right-click a node to jump to the card, or click the review badge to return to the map node.</li>
        </ol>
        <div class="tip"><strong>Tip:</strong> Unlinked nodes can still be used for structure, titles, or brainstorming.</div>
    </div>

    <h2 id="setup-sync">&#9729; Important: First Time Sync</h2>
    <div class="warning">
        <strong>CRITICAL STEP FOR NEW USERS</strong>
        <p>After installing this add-on or using Active/Inactive for the first time, choose <strong>Upload to AnkiWeb</strong> when Anki asks how to sync.</p>
        <ul>
            <li>This is a one-time requirement for the custom <code>MindMap Master</code> note type.</li>
            <li>Future changes will sync normally.</li>
        </ul>
    </div>

    <h2 id="operations">&#9733; Basic Operations</h2>
    <table>
        <tr><th>Action</th><th>Shortcut</th><th>Description</th></tr>
        <tr><td>Add Child</td><td><span class="shortcut">Tab</span></td><td>Create a child node.</td></tr>
        <tr><td>Add Sibling</td><td><span class="shortcut">Enter</span></td><td>Create a sibling node.</td></tr>
        <tr><td>Edit</td><td><span class="shortcut">Space</span> / double-click</td><td>Edit text; use <span class="shortcut">Shift+Enter</span> for a new line.</td></tr>
        <tr><td>Delete</td><td><span class="shortcut">Delete</span></td><td>Remove the node and its children.</td></tr>
        <tr><td>Move</td><td>Drag &amp; Drop</td><td>Move a node to a new parent.</td></tr>
    </table>
    <h3>Copy, Paste &amp; Undo</h3>
    <ul>
        <li>Select a node and use <span class="shortcut">Ctrl+C</span> / <span class="shortcut">Ctrl+V</span> to copy it under another node.</li>
        <li>Pasting external text creates a new child node with that text.</li>
        <li>Undo with <span class="shortcut">Ctrl+Z</span>; redo with <span class="shortcut">Ctrl+Y</span> or <span class="shortcut">Ctrl+Shift+Z</span>.</li>
    </ul>

    <h2 id="card-linking">&#8644; Card Linking System</h2>
    <div class="feature">
        <p>Links are initiated from Anki cards to keep the workflow simple and compatible with different card types.</p>
        <ul>
            <li><strong>Mind Map &rarr; Card:</strong> editing a linked node updates the first line of the card Front field.</li>
            <li><strong>Card &rarr; Mind Map:</strong> editing the first line of the card Front field updates the linked node.</li>
        </ul>
    </div>
    <div class="warning"><strong>Auto-save warning:</strong> Wait for the "Auto-saved" notice before closing an editor after editing linked nodes.</div>

    <h2 id="config">&#9881; Configuration</h2>
    <p>Open <strong>Tools &rarr; Add-ons &rarr; Mind Map &rarr; Config</strong>.</p>
    <ul>
        <li><strong>Line Color:</strong> accepts names, Hex, or RGBA values.</li>
        <li><strong>Background:</strong> place images in <code>backgrounds</code> and set the filename in config.</li>
        <li><strong>Hotkeys:</strong> customize save, refresh, focus root, and quick open shortcuts.</li>
    </ul>

    <h2 id="advanced">&#9632; Advanced Features</h2>
    <ul>
        <li><strong>Floating Nodes:</strong> double-click empty space to create independent nodes.</li>
        <li><strong>MathJax:</strong> use standard inline and block math syntax.</li>
        <li><strong>Active/Inactive:</strong> hide completed maps from the card linking menu.</li>
        <li><strong>Fullscreen:</strong> use the toolbar fullscreen button.</li>
    </ul>

    <h2 id="backup">&#9851; Backup &amp; Recovery</h2>
    <p>Use <strong>Tools &rarr; Mind Map &rarr; Backup &amp; Recovery</strong> to export maps to JSON, optionally with an offline HTML viewer, or import them back later.</p>

    <hr style="margin: 30px 0; border: none; border-top: 2px solid #3498db;">
    <p style="text-align: center; color: #95a5a6;"><small>Anki Mind Map Plugin | Enhance Learning Through Visualization</small></p>
    """
