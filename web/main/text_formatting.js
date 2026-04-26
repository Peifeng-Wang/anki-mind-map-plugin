function toggleWrapSelection(textarea, openTag, closeTag) {
    var value = textarea.value;
    var start = textarea.selectionStart;
    var end = textarea.selectionEnd;

    if (start === end) {
        textarea.value = value.substring(0, start) + openTag + closeTag + value.substring(end);
        textarea.selectionStart = textarea.selectionEnd = start + openTag.length;
        return;
    }

    var before = value.substring(0, start);
    var selected = value.substring(start, end);
    var after = value.substring(end);

    var hasWrap =
        start >= openTag.length &&
        value.substring(start - openTag.length, start) === openTag &&
        value.substring(end, end + closeTag.length) === closeTag;

    if (hasWrap) {
        textarea.value =
            value.substring(0, start - openTag.length) +
            selected +
            value.substring(end + closeTag.length);
        textarea.selectionStart = start - openTag.length;
        textarea.selectionEnd = end - openTag.length;
        return;
    }

    textarea.value = before + openTag + selected + closeTag + after;
    textarea.selectionStart = start + openTag.length;
    textarea.selectionEnd = end + openTag.length;
}

function wrapSelectionAsEscapedHtml(textarea, openTag, closeTag) {
    var value = textarea.value;
    var start = textarea.selectionStart;
    var end = textarea.selectionEnd;

    if (start === end) {
        textarea.value = value.substring(0, start) + openTag + closeTag + value.substring(end);
        textarea.selectionStart = textarea.selectionEnd = start + openTag.length;
        return;
    }

    var before = value.substring(0, start);
    var selected = value.substring(start, end);
    var after = value.substring(end);

    textarea.value = before + openTag + selected + closeTag + after;
    // Keep the original selection (inside the tags).
    textarea.selectionStart = start + openTag.length;
    textarea.selectionEnd = end + openTag.length;
}

function escapeCodeTagsForDisplay(text) {
    // Escape any content inside <code>...</code> and <pre><code>...</code></pre>.
    // This lets users type raw code in the textarea without manually HTML-escaping it.
    var blocks = [];
    var token = '__CODE_ESC_' + Date.now() + '_' + Math.random().toString(16).slice(2) + '__';

    function stash(html) {
        blocks.push(html);
        return token + (blocks.length - 1) + token;
    }

    var out = String(text);

    // Process code blocks first so the inline <code> regex won't touch them.
    out = out.replace(/<pre><code>([\s\S]*?)<\/code><\/pre>/gi, function (_m, inner) {
        return stash('<pre><code>' + escapeHtml(inner) + '</code></pre>');
    });

    out = out.replace(/<code>([\s\S]*?)<\/code>/gi, function (_m, inner) {
        return stash('<code>' + escapeHtml(inner) + '</code>');
    });

    out = out.replace(new RegExp(token + '(\\d+)' + token, 'g'), function (_m, idx) {
        return blocks[Number(idx)] || '';
    });

    return out;
}

function showEditFormattingContextMenu(x, y, textarea, onResize) {

    var selectionSnapshot = {
        start: textarea.selectionStart,
        end: textarea.selectionEnd
    };

    function runWithSelection(action) {
        textarea.focus();
        textarea.selectionStart = selectionSnapshot.start;
        textarea.selectionEnd = selectionSnapshot.end;
        action();
        selectionSnapshot.start = textarea.selectionStart;
        selectionSnapshot.end = textarea.selectionEnd;
        if (typeof onResize === 'function') onResize();
    }

    var menu = document.createElement('div');
    menu.id = 'custom-context-menu';
    menu.style.cssText = `
        position: fixed;
        left: ${x}px;
        top: ${y}px;
        background: white;
        border: 1px solid #ccc;
        box-shadow: 2px 2px 5px rgba(0,0,0,0.2);
        z-index: 10000;
        padding: 5px 0;
        border-radius: 4px;
        min-width: 160px;
    `;

    function createMenuItem(text, onClick) {
        var item = document.createElement('div');
        item.innerText = text;
        item.style.cssText = `
            padding: 8px 15px;
            cursor: pointer;
            font-family: sans-serif;
            font-size: 14px;
            color: #333;
        `;
        item.onmouseover = function () { this.style.background = '#f0f0f0'; };
        item.onmouseout = function () { this.style.background = 'white'; };
        // Keep focus in the textarea while interacting with the menu.
        item.addEventListener('mousedown', function (ev) {
            ev.preventDefault();
            ev.stopPropagation();
            ev.stopImmediatePropagation();
        }, true);
        item.onclick = function () {
            onClick();
            menu.remove();
        };
        return item;
    }

    menu.appendChild(createMenuItem('Bold', function () {
        runWithSelection(function () { toggleWrapSelection(textarea, '<b>', '</b>'); });
    }));
    menu.appendChild(createMenuItem('Italic', function () {
        runWithSelection(function () { toggleWrapSelection(textarea, '<i>', '</i>'); });
    }));
    menu.appendChild(createMenuItem('Inline Code', function () {
        runWithSelection(function () { wrapSelectionAsEscapedHtml(textarea, '<code>', '</code>'); });
    }));
    menu.appendChild(createMenuItem('Code Block', function () {
        runWithSelection(function () { wrapSelectionAsEscapedHtml(textarea, '<pre><code>', '</code></pre>'); });
    }));

    document.body.appendChild(menu);

    // Close on click elsewhere.
    var closeHandler = function (e) {
        if (!menu.contains(e.target)) {
            menu.remove();
            document.removeEventListener('click', closeHandler, true);
        }
    };
    setTimeout(function () { document.addEventListener('click', closeHandler, true); }, 0);
}

// Called from Python (Qt shortcuts) and can also be used by other JS code.
window.applyTextFormatting = function (action) {
    if (!action) return;
    if (!MM.state.isEditing || !MM.state.editingNodeId) return;

    var textarea = document.getElementById('input-box');
    if (!textarea) return;

    textarea.focus();

    if (action === 'bold') {
        toggleWrapSelection(textarea, '<b>', '</b>');
    } else if (action === 'italic') {
        toggleWrapSelection(textarea, '<i>', '</i>');
    } else if (action === 'inline_code') {
        wrapSelectionAsEscapedHtml(textarea, '<code>', '</code>');
    } else if (action === 'code_block') {
        wrapSelectionAsEscapedHtml(textarea, '<pre><code>', '</code></pre>');
    }

    // Trigger the existing input listener to re-measure the textarea.
    textarea.dispatchEvent(new Event('input'));
};

// Fallback: capture hotkeys at document level during edit mode (some environments don't deliver them to textarea).
document.addEventListener('keydown', function (e) {
    if (!MM.state.isEditing || !MM.state.editingNodeId) return;

    if (matchHotkey(e, MM.state.hotkeyConfig.bold)) {
        e.preventDefault();
        e.stopPropagation();
        e.stopImmediatePropagation();
        window.applyTextFormatting('bold');
        return;
    }
    if (matchHotkey(e, MM.state.hotkeyConfig.italic)) {
        e.preventDefault();
        e.stopPropagation();
        e.stopImmediatePropagation();
        window.applyTextFormatting('italic');
        return;
    }
    if (matchHotkey(e, MM.state.hotkeyConfig.inline_code)) {
        e.preventDefault();
        e.stopPropagation();
        e.stopImmediatePropagation();
        window.applyTextFormatting('inline_code');
        return;
    }
    if (matchHotkey(e, MM.state.hotkeyConfig.code_block)) {
        e.preventDefault();
        e.stopPropagation();
        e.stopImmediatePropagation();
        window.applyTextFormatting('code_block');
        return;
    }
}, true);

