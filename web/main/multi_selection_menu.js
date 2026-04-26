// Context menu shown after multi-selecting nodes (Shift+Click).
// Cross-cuts summary and boundary commands; depends on validators in
// summary_braces_dom.js / boundaries.js and command entry points in
// summary_braces_commands.js / boundaries.js.

function showMultiSelectionContextMenu(x, y) {
    var existing = document.getElementById('custom-context-menu');
    if (existing) existing.remove();

    var menu = document.createElement('div');
    menu.id = 'custom-context-menu';
    menu.className = 'mm-context-menu';
    menu.style.left = x + 'px';
    menu.style.top = y + 'px';

    function createMenuItem(text, onClick, disabled) {
        var item = document.createElement('div');
        item.innerText = text;
        item.className = 'mm-context-menu-item' + (disabled ? ' disabled' : '');
        if (!disabled) {
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
    sep.className = 'mm-context-menu-sep';
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
    sep2.className = 'mm-context-menu-sep';
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
