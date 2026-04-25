function toggleReadOnly() {
    if (!jm) return;
    var checkbox = document.getElementById('readonly_toggle');
    if (checkbox.checked) {
        jm.disable_edit();
    } else {
        jm.enable_edit();
    }
}
