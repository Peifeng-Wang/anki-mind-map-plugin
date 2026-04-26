function toggleReadOnly() {
    if (!MM.state.jm) return;
    var checkbox = document.getElementById('readonly_toggle');
    if (checkbox.checked) {
        MM.state.jm.disable_edit();
    } else {
        MM.state.jm.enable_edit();
    }
}
