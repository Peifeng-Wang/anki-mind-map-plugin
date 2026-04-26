// Context menu shown after multi-selecting nodes (Shift+Click).
// Cross-cuts summary and boundary commands; depends on validators in
// summary_braces_dom.js / boundaries.js and command entry points in
// summary_braces_commands.js / boundaries.js.

function showMultiSelectionContextMenu(x, y) {
    var existing = document.getElementById('custom-context-menu');
    if (existing) existing.remove();

    var menu = document.createElement('div');
    menu.id = 'custom-context-menu';
    menu.style.cssText = 'position:fixed; left:' + x + 'px; top:' + y + 'px; background:white; border:1px solid #ccc; box-shadow:2px 2px 5px rgba(0,0,0,0.2); z-index:10000; padding:5px 0; border-radius:4px; min-width:180px;';

    function createMenuItem(text, onClick, disabled) {
        var item = document.createElement('div');
        item.innerText = text;
        item.style.cssText = 'padding:8px 15px; cursor:' + (disabled ? 'default' : 'pointer') + '; font-family:sans-serif; font-size:14px; color:' + (disabled ? '#999' : '#333') + ';';
        if (!disabled) {
            item.onmouseover = function () { this.style.background = '#f0f0f0'; };
            item.onmouseout = function () { this.style.background = 'white'; };
            item.onclick = function () {
                onClick();
                menu.remove();
            };
        }
        return item;
    }

    var validation = validateSummarySelection();

    if (validation.valid) {
        menu.appendChild(createMenuItem('Create Summary', function () {
            createSummary();
        }));
    } else {
        menu.appendChild(createMenuItem(validation.reason, null, true));
    }

    // Separator
    var sep = document.createElement('div');
    sep.style.cssText = 'height:1px; background:#eee; margin:4px 0;';
    menu.appendChild(sep);

    // Boundary option
    var boundaryValidation = validateBoundarySelection();
    if (boundaryValidation.valid) {
        menu.appendChild(createMenuItem('Create Boundary', function () {
            createBoundary();
        }));
    } else {
        menu.appendChild(createMenuItem('Boundary: ' + boundaryValidation.reason, null, true));
    }

    // Separator
    var sep2 = document.createElement('div');
    sep2.style.cssText = 'height:1px; background:#eee; margin:4px 0;';
    menu.appendChild(sep2);

    menu.appendChild(createMenuItem('Clear Selection', function () {
        clearSelection();
    }));

    document.body.appendChild(menu);

    // Close on click elsewhere
    var closeHandler = function (e) {
        if (!menu.contains(e.target)) {
            menu.remove();
            document.removeEventListener('click', closeHandler);
        }
    };
    setTimeout(function () { document.addEventListener('click', closeHandler); }, 0);
}
