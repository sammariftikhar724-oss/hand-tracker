function updateSettings(clearFlag = false) {
    const mode = document.getElementById('modeSelect').value;
    const minDist = document.getElementById('minDist').value;
    const maxDist = document.getElementById('maxDist').value;
    const brushSize = document.getElementById('brushSize').value;
    const color = document.getElementById('toolColor').value;

    document.getElementById('drawingControls').style.display = (mode === 'Air Drawing') ? 'block' : 'none';
    document.getElementById('calibrationControls').style.display = (mode === 'Volume Control' || mode === 'Brightness Control') ? 'block' : 'none';
    document.getElementById('mediaInfo').style.display = (mode === 'Media Gestures') ? 'block' : 'none';

    document.getElementById('currentModeBadge').innerText = `Mode: ${mode}`;

    fetch('/update_settings', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            mode: mode,
            min_dist: minDist,
            max_dist: maxDist,
            brush_thickness: brushSize,
            color: color,
            clear_canvas: clearFlag
        })
    });
}

function clearCanvas() {
    updateSettings(true);
}

window.onload = function() {
    updateSettings();
};