// Edit-mode lifecycle for jsMind nodes: turning a node into a textarea
// and committing/canceling the edit. The document-level event listeners
// that drive these (keyboard, mouse, contextmenu) live in node_editor_events.js.

// Tag/attribute allowlist for topic rich text. Topics carry user-authored
// formatting from the bold/italic/code hotkeys (see text_formatting.js):
// <b>, <i>, <em>, <strong>, <code>, <pre>, <br>, plus <span>/<u>/<sub>/<sup>
// for completeness. MathJax rewrites math expressions on its own pass after
// the DOM is updated, so we don't need to allow <math>/<svg> here.
var MM_TOPIC_ALLOWED_TAGS = ['b', 'i', 'em', 'strong', 'code', 'pre', 'br', 'span', 'u', 'sub', 'sup'];
var MM_TOPIC_ALLOWED_ATTR = ['class', 'style'];

function sanitizeTopicHtml(html) {
    if (typeof DOMPurify !== 'undefined' && DOMPurify && typeof DOMPurify.sanitize === 'function') {
        return DOMPurify.sanitize(html, {
            ALLOWED_TAGS: MM_TOPIC_ALLOWED_TAGS,
            ALLOWED_ATTR: MM_TOPIC_ALLOWED_ATTR
        });
    }
    // DOMPurify is bundled in editor HTML; if it's missing, we'd rather
    // render text safely than ship raw HTML. Strip every tag as fallback.
    console.warn('DOMPurify unavailable; falling back to tag-stripped topic render.');
    return String(html).replace(/<[^>]*>/g, '');
}

// Enter edit mode for a node
function enterEditMode(node) {
    if (!node || MM.state.isEditing) return;

    MM.state.isEditing = true;
    MM.state.editingNodeId = node.id;
    removeCustomContextMenu();

    // Get the node element directly
    var nodeElement = document.querySelector('jmnode[nodeid="' + node.id + '"]');
    if (!nodeElement) {
        MM.state.isEditing = false;
        MM.state.editingNodeId = null;
        return;
    }

    // Get current content and convert <br> to newlines
    var currentContent = node.topic;
    var plainText = currentContent.replace(/<br\s*\/?>/gi, '\n');

    // Store original HTML
    var originalHTML = nodeElement.innerHTML;

    // Clear node and prepare for editing
    nodeElement.innerHTML = '';
    nodeElement.style.padding = '0';
    nodeElement.style.display = 'inline-block';

    // Create textarea
    var textarea = document.createElement('textarea');
    textarea.id = 'input-box';
    textarea.value = plainText;
    textarea.className = 'mm-node-input';

    // Get computed styles from node
    var computedStyle = window.getComputedStyle(nodeElement);

    // Apply dynamic font styles; the rest lives in CSS.
    textarea.style.fontFamily = computedStyle.fontFamily;
    textarea.style.fontSize = computedStyle.fontSize;
    textarea.style.fontWeight = computedStyle.fontWeight;

    // Add textarea to node
    nodeElement.appendChild(textarea);

    // Auto-resize function - REAL-TIME
    function autoResize() {
        if (!textarea || !textarea.parentNode) return;

        // Create hidden div for measurement
        var measureDiv = document.createElement('div');
        measureDiv.style.cssText = `
            position: absolute;
            visibility: hidden;
            white-space: pre-wrap;
            word-wrap: break-word;
            font-family: ${textarea.style.fontFamily};
            font-size: ${textarea.style.fontSize};
            font-weight: ${textarea.style.fontWeight};
            line-height: ${textarea.style.lineHeight};
            padding: ${textarea.style.padding};
            border: ${textarea.style.border};
            box-sizing: border-box;
            max-width: 500px;
        `;
        measureDiv.textContent = textarea.value || 'W';
        document.body.appendChild(measureDiv);

        var width = Math.max(120, Math.min(500, measureDiv.offsetWidth));
        var height = Math.max(30, measureDiv.offsetHeight);
        document.body.removeChild(measureDiv);

        // Apply to both textarea and node
        textarea.style.width = width + 'px';
        textarea.style.height = height + 'px';
        nodeElement.style.width = width + 'px';
        nodeElement.style.height = height + 'px';

        console.log('Resized:', width, 'x', height);
    }

    textarea.focus();
    textarea.select();
    setTimeout(autoResize, 10);

    // Keydown handler
    textarea.addEventListener('keydown', function (e) {
        e.stopPropagation();
        e.stopImmediatePropagation();

        if (matchHotkey(e, MM.state.hotkeyConfig.bold)) {
            e.preventDefault();
            toggleWrapSelection(textarea, '<b>', '</b>');
            setTimeout(autoResize, 0);
            return false;
        }

        if (matchHotkey(e, MM.state.hotkeyConfig.italic)) {
            e.preventDefault();
            toggleWrapSelection(textarea, '<i>', '</i>');
            setTimeout(autoResize, 0);
            return false;
        }

        if (matchHotkey(e, MM.state.hotkeyConfig.inline_code)) {
            e.preventDefault();
            wrapSelectionAsEscapedHtml(textarea, '<code>', '</code>');
            setTimeout(autoResize, 0);
            return false;
        }

        if (matchHotkey(e, MM.state.hotkeyConfig.code_block)) {
            e.preventDefault();
            wrapSelectionAsEscapedHtml(textarea, '<pre><code>', '</code></pre>');
            setTimeout(autoResize, 0);
            return false;
        }

        // Shift+Enter: insert newline manually
        if (e.key === 'Enter' && e.shiftKey) {
            e.preventDefault();
            var start = textarea.selectionStart;
            var end = textarea.selectionEnd;
            textarea.value = textarea.value.substring(0, start) + '\n' + textarea.value.substring(end);
            textarea.selectionStart = textarea.selectionEnd = start + 1;
            setTimeout(autoResize, 0);
            console.log('Newline inserted');
            return false;
        }

        // Enter: exit
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            exitEditMode();
            return false;
        }

        // Escape: cancel
        if (e.key === 'Escape') {
            e.preventDefault();
            removeCustomContextMenu();
            nodeElement.innerHTML = originalHTML;
            nodeElement.style.width = '';
            nodeElement.style.height = '';
            nodeElement.style.padding = '';
            MM.state.isEditing = false;
            MM.state.editingNodeId = null;
            document.getElementById('jsmind_container').focus();
            return false;
        }

        setTimeout(autoResize, 0);
    }, true);

    // Input handler - resize on every input
    textarea.addEventListener('input', function (e) {
        e.stopPropagation();
        autoResize();
    }, true);

    textarea.addEventListener('paste', function () {
        setTimeout(autoResize, 10);
    }, true);

    textarea.addEventListener('mousedown', function (e) {
        e.stopPropagation();
        e.stopImmediatePropagation();
    }, true);

    textarea.addEventListener('click', function (e) {
        e.stopPropagation();
        e.stopImmediatePropagation();
    }, true);

    textarea.addEventListener('contextmenu', function (e) {
        swallowEvent(e);
        showEditFormattingContextMenu(e.clientX, e.clientY, textarea, function () {
            setTimeout(autoResize, 0);
        });
    }, true);
}

// Exit edit mode
function exitEditMode() {
    if (!MM.state.isEditing) return;

    removeCustomContextMenu();

    var inputBox = document.getElementById('input-box');
    if (!inputBox || !MM.state.editingNodeId) {
        MM.state.isEditing = false;
        MM.state.editingNodeId = null;
        return;
    }

    var newText = escapeCodeTagsForDisplay(inputBox.value);
    var node = MM.state.jm.get_node(MM.state.editingNodeId);

    if (node) {
        var nodeElement = document.querySelector('jmnode[nodeid="' + MM.state.editingNodeId + '"]');

        if (nodeElement) {
            nodeElement.innerHTML = '';
            nodeElement.style.width = '';
            nodeElement.style.height = '';
            nodeElement.style.padding = '';
            nodeElement.style.whiteSpace = 'normal';
            nodeElement.style.wordWrap = 'break-word';
            nodeElement.style.display = 'inline-block';
            nodeElement.style.maxWidth = '500px';

            if (newText && newText.trim() !== '') {
                // Convert newlines to <br> for display
                var htmlText = newText.replace(/\r?\n/g, '<br>');
                MM.state.jm.update_node(MM.state.editingNodeId, htmlText);

                if (MM.state.jm.view.opts.support_html) {
                    // Topic carries rich text (Bold/Italic/Code) — sanitize via DOMPurify.
                    nodeElement.innerHTML = sanitizeTopicHtml(htmlText);
                } else {
                    nodeElement.textContent = htmlText;
                }
            } else {
                if (MM.state.jm.view.opts.support_html) {
                    // Topic carries rich text (Bold/Italic/Code) — sanitize via DOMPurify.
                    nodeElement.innerHTML = sanitizeTopicHtml(node.topic);
                } else {
                    nodeElement.textContent = node.topic;
                }
            }
        }
    }

    MM.state.isEditing = false;
    MM.state.editingNodeId = null;

    var container = document.getElementById('jsmind_container');
    if (container) container.focus();

    saveHistory();

    // Auto-save immediately and refresh to fix position
    console.log('Auto-saving after edit...');
    autoSave();

    // Trigger refresh after a brief delay to allow save to complete
    setTimeout(function () {
        console.log('Auto-refreshing to fix node position...');
        refreshMap();
    }, 100);

    setTimeout(renderMath, 300);
}
