// Match hotkey event against config string
function matchHotkey(e, hotkeyString) {
    if (!hotkeyString) return false;

    var parts = hotkeyString.split('+');
    var key = parts[parts.length - 1];
    var needsCtrl = parts.includes('Ctrl');
    var needsMeta = parts.includes('Meta') || parts.includes('Cmd');
    var needsShift = parts.includes('Shift');
    var needsAlt = parts.includes('Alt');

    var eventKey = e.key;

    // For non-F-keys, do case-insensitive comparison
    if (!key.match(/^F\d+$/)) {
        key = key.toLowerCase();
        eventKey = eventKey.toLowerCase();
    }

    // Some keys produce a different character when Shift is held (e.g. ` -> ~).
    // Allow matching config strings that use the unshifted character.
    var shiftedToUnshifted = {
        '~': '`',
        '!': '1',
        '@': '2',
        '#': '3',
        '$': '4',
        '%': '5',
        '^': '6',
        '&': '7',
        '*': '8',
        '(': '9',
        ')': '0',
        '_': '-',
        '+': '=',
        '{': '[',
        '}': ']',
        '|': '\\',
        ':': ';',
        '"': '\'',
        '<': ',',
        '>': '.',
        '?': '/'
    };

    var keyMatches = (eventKey === key) ||
        (needsShift && shiftedToUnshifted[eventKey] && shiftedToUnshifted[eventKey] === key);

    return keyMatches &&
        (e.ctrlKey || e.metaKey) === (needsCtrl || needsMeta) &&
        e.shiftKey === needsShift &&
        e.altKey === needsAlt;
}
