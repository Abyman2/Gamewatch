import os

# --- 1. UPDATE templates/index.html ---
with open("templates/index.html", "r", encoding="utf-8") as f:
    html = f.read()

# Add Clear All Boxes and Apply All TVs buttons
old_btn_group = """                    <button type="button" class="btn btn-autodetect-pill" id="btn-auto-detect-tvs" onclick="triggerAutoDetectTVs()">
                        <span class="sparkle-icon">✨</span>
                        <span>Auto-Detect TVs</span>
                        <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><polyline points="6 9 12 15 18 9"></polyline></svg>
                    </button>"""

new_btn_group = """                    <button type="button" class="btn btn-autodetect-pill" id="btn-auto-detect-tvs" onclick="triggerAutoDetectTVs()">
                        <span class="sparkle-icon">✨</span>
                        <span>Auto-Detect TVs</span>
                        <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><polyline points="6 9 12 15 18 9"></polyline></svg>
                    </button>
                    <button type="button" class="btn" id="btn-auto-apply-all-tvs" onclick="autoApplyAllDetectedTvs()" title="Automatically configure TV 1, TV 2, ... TV 7 from detected screens" style="padding: 6px 14px; font-size: 12px; border-radius: 9999px; border: 1px solid rgba(16, 185, 129, 0.5); background: rgba(16, 185, 129, 0.15); color: #10b981; cursor: pointer; font-weight: 600;">
                        <span>⚡ Apply All TVs</span>
                    </button>
                    <button type="button" class="btn" id="btn-clear-all-tvs" onclick="clearAllTvCalibrations()" title="Remove all dummy/test boxes for clean setup" style="padding: 6px 14px; font-size: 12px; border-radius: 9999px; border: 1px solid rgba(239, 68, 68, 0.4); background: rgba(239, 68, 68, 0.1); color: #ef4444; cursor: pointer; font-weight: 600;">
                        <span>🧹 Clear All Boxes</span>
                    </button>"""

if old_btn_group in html:
    html = html.replace(old_btn_group, new_btn_group)
    print("index.html: toolbar buttons updated successfully")
else:
    print("index.html: old_btn_group not found")

# Add show-all-tvs toggle
old_toggles = """                                <div class="ck-toggles-row">
                                    <label class="toggle-anti-glare-label" title="Suppresses harsh fluorescent ceiling lamp glare on screen">
                                        <input type="checkbox" id="chk-anti-glare" checked onchange="toggleAntiGlare(this.checked)">
                                        <span class="tag-slider"></span>
                                        <span class="tag-txt">☀ Anti-Glare Filter</span>
                                    </label>
                                    <span class="keystone-angle-badge" id="keystone-angle-badge">📐 Keystone: 0.0°</span>
                                </div>"""

new_toggles = """                                <div class="ck-toggles-row">
                                    <label class="toggle-anti-glare-label" title="Suppresses harsh fluorescent ceiling lamp glare on screen">
                                        <input type="checkbox" id="chk-anti-glare" checked onchange="toggleAntiGlare(this.checked)">
                                        <span class="tag-slider"></span>
                                        <span class="tag-txt">☀ Anti-Glare Filter</span>
                                    </label>
                                    <label class="toggle-anti-glare-label" title="Shows or hides non-active TV boxes to eliminate screen clutter">
                                        <input type="checkbox" id="chk-show-all-tvs" onchange="drawCanvasOverlay()">
                                        <span class="tag-slider"></span>
                                        <span class="tag-txt">👁 Show Other TV Outlines</span>
                                    </label>
                                    <span class="keystone-angle-badge" id="keystone-angle-badge">📐 Keystone: 0.0°</span>
                                </div>"""

if old_toggles in html:
    html = html.replace(old_toggles, new_toggles)
    print("index.html: toggles row updated successfully")
else:
    print("index.html: old_toggles not found")

# Add Delete Station button
old_save_btn = """                    <button type="button" class="btn btn-primary btn-save-config" id="btn-studio-save-station">
                        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M19 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11l5 5v11a2 2 0 0 1-2 2z"></path><polyline points="17 21 17 13 7 13 7 21"></polyline><polyline points="7 3 7 8 15 8"></polyline></svg>
                        <span>Save Configuration</span>
                        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><polyline points="9 18 15 12 9 6"></polyline></svg>
                    </button>"""

new_save_btn = """                    <button type="button" class="btn btn-primary btn-save-config" id="btn-studio-save-station">
                        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M19 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11l5 5v11a2 2 0 0 1-2 2z"></path><polyline points="17 21 17 13 7 13 7 21"></polyline><polyline points="7 3 7 8 15 8"></polyline></svg>
                        <span>Save Configuration</span>
                        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><polyline points="9 18 15 12 9 6"></polyline></svg>
                    </button>
                    <button type="button" class="btn" id="btn-delete-station" onclick="deleteCurrentStation()" style="margin-top: 8px; width: 100%; border: 1px solid rgba(239, 68, 68, 0.3); background: rgba(239, 68, 68, 0.08); color: #f87171; border-radius: 8px; padding: 10px; font-size: 13px; font-weight: 600; cursor: pointer;">
                        <span>🗑 Delete This Station</span>
                    </button>"""

if old_save_btn in html:
    html = html.replace(old_save_btn, new_save_btn)
    print("index.html: save button section updated successfully")
else:
    print("index.html: old_save_btn not found")

with open("templates/index.html", "w", encoding="utf-8") as f:
    f.write(html)


# --- 2. UPDATE static/js/app.js ---
with open("static/js/app.js", "r", encoding="utf-8") as f:
    js = f.read()

# Update drawCanvasOverlay to eliminate clutter and only highlight the active station
old_draw = """function drawCanvasOverlay() {
    if (!App.ctx) return;
    App.ctx.clearRect(0, 0, App.canvas.width, App.canvas.height);

    // 1. Draw existing TV stations from App.state
    if (App.state && App.state.tvs) {
        App.state.tvs.forEach((tv, idx) => {
            const isPrimary = (idx === 0 || tv.id === 2);
            const strokeColor = isPrimary ? '#16B978' : '#16B8FF';
            const tagText = tv.name ? `${tv.name}` : `TV ${tv.id}`;

            if (tv.corners && tv.corners.length === 4) {
                // Quadrilateral polygon
                App.ctx.save();
                App.ctx.beginPath();
                App.ctx.moveTo(tv.corners[0][0], tv.corners[0][1]);
                App.ctx.lineTo(tv.corners[1][0], tv.corners[1][1]);
                App.ctx.lineTo(tv.corners[2][0], tv.corners[2][1]);
                App.ctx.lineTo(tv.corners[3][0], tv.corners[3][1]);
                App.ctx.closePath();
                App.ctx.fillStyle = isPrimary ? 'rgba(22, 185, 120, 0.08)' : 'rgba(22, 184, 255, 0.08)';
                App.ctx.fill();
                App.ctx.strokeStyle = strokeColor;
                App.ctx.lineWidth = 2;
                App.ctx.stroke();
                drawCVTag(App.ctx, `${tagText} 📐`, tv.corners[0][0], tv.corners[0][1], strokeColor, strokeColor, 'rgba(6, 26, 53, 0.90)');
                App.ctx.restore();
            } else if (tv.roi) {
                const [rx, ry, rw, rh] = tv.roi;
                App.ctx.save();
                App.ctx.fillStyle = isPrimary ? 'rgba(22, 185, 120, 0.08)' : 'rgba(22, 184, 255, 0.08)';
                App.ctx.fillRect(rx, ry, rw, rh);
                App.ctx.strokeStyle = strokeColor;
                App.ctx.lineWidth = 2;
                App.ctx.strokeRect(rx, ry, rw, rh);
                drawCVTag(App.ctx, tagText, rx, ry, strokeColor, strokeColor, 'rgba(6, 26, 53, 0.90)');
                App.ctx.restore();
            }
        });
    }"""

new_draw = """function drawCanvasOverlay() {
    if (!App.ctx) return;
    App.ctx.clearRect(0, 0, App.canvas.width, App.canvas.height);

    const stationSelect = document.getElementById('station-select');
    const activeTvId = stationSelect ? (stationSelect.value === 'new' ? null : parseInt(stationSelect.value, 10)) : null;
    const chkShowAll = document.getElementById('chk-show-all-tvs');
    const showAllTvs = chkShowAll ? chkShowAll.checked : false;

    // 1. Draw existing TV stations from App.state (Clean, clutter-free rendering)
    if (App.state && App.state.tvs) {
        App.state.tvs.forEach((tv) => {
            const isActive = (tv.id === activeTvId);
            if (!isActive && !showAllTvs) {
                return; // Hide non-active TVs to eliminate visual clutter!
            }
            
            const strokeColor = isActive ? '#10B981' : 'rgba(6, 182, 212, 0.35)';
            const lineWidth = isActive ? 2 : 1;
            const tagText = tv.name ? `${tv.name}` : `TV ${tv.id}`;

            if (tv.corners && tv.corners.length === 4) {
                App.ctx.save();
                App.ctx.beginPath();
                App.ctx.moveTo(tv.corners[0][0], tv.corners[0][1]);
                App.ctx.lineTo(tv.corners[1][0], tv.corners[1][1]);
                App.ctx.lineTo(tv.corners[2][0], tv.corners[2][1]);
                App.ctx.lineTo(tv.corners[3][0], tv.corners[3][1]);
                App.ctx.closePath();
                App.ctx.fillStyle = isActive ? 'rgba(16, 185, 129, 0.08)' : 'transparent';
                App.ctx.fill();
                App.ctx.strokeStyle = strokeColor;
                App.ctx.lineWidth = lineWidth;
                if (!isActive) App.ctx.setLineDash([4, 4]);
                App.ctx.stroke();
                if (isActive) {
                    drawCVTag(App.ctx, `${tagText} 📐`, tv.corners[0][0], tv.corners[0][1], strokeColor, strokeColor, 'rgba(6, 26, 53, 0.90)');
                }
                App.ctx.restore();
            } else if (tv.roi) {
                const [rx, ry, rw, rh] = tv.roi;
                App.ctx.save();
                App.ctx.fillStyle = isActive ? 'rgba(16, 185, 129, 0.08)' : 'transparent';
                App.ctx.fillRect(rx, ry, rw, rh);
                App.ctx.strokeStyle = strokeColor;
                App.ctx.lineWidth = lineWidth;
                if (!isActive) App.ctx.setLineDash([4, 4]);
                App.ctx.strokeRect(rx, ry, rw, rh);
                if (isActive) {
                    drawCVTag(App.ctx, tagText, rx, ry, strokeColor, strokeColor, 'rgba(6, 26, 53, 0.90)');
                }
                App.ctx.restore();
            }
        });
    }"""

if old_draw in js:
    js = js.replace(old_draw, new_draw)
    print("app.js: drawCanvasOverlay updated successfully")
else:
    print("app.js: old_draw not found")

# Add updateStationDropdown helper and attach to fetchState
old_fetch = """        if (App.currentView === 'home') renderTvList(data.tvs);"""
new_fetch = """        updateStationDropdown(data.tvs);
        if (App.currentView === 'home') renderTvList(data.tvs);"""

if old_fetch in js:
    js = js.replace(old_fetch, new_fetch, 1)
    print("app.js: fetchState hook updated successfully")
else:
    print("app.js: old_fetch not found")

# Add helper functions updateStationDropdown, clearAllTvCalibrations, autoApplyAllDetectedTvs, deleteCurrentStation
extra_functions = """
// ============================================================
// DYNAMIC STATION DROPDOWN & MULTI-TV HELPERS
// ============================================================
window.updateStationDropdown = function(tvs) {
    const select = document.getElementById('station-select');
    if (!select || !tvs) return;
    const currentVal = select.value;
    const existingOptions = Array.from(select.options).map(o => o.value);
    
    // Check if options changed
    const targetValues = tvs.map(t => String(t.id)).concat(['new']);
    const isSame = existingOptions.length === targetValues.length && existingOptions.every((v, i) => v === targetValues[i]);
    if (isSame) return;

    select.innerHTML = '';
    tvs.forEach(tv => {
        const opt = document.createElement('option');
        opt.value = String(tv.id);
        opt.textContent = `TV ${tv.id} (${tv.name || 'Station'})`;
        select.appendChild(opt);
    });
    const addOpt = document.createElement('option');
    addOpt.value = 'new';
    addOpt.textContent = '+ Add New Station';
    select.appendChild(addOpt);

    if (currentVal && Array.from(select.options).some(o => o.value === currentVal)) {
        select.value = currentVal;
    } else if (tvs.length > 0) {
        select.value = String(tvs[0].id);
    } else {
        select.value = 'new';
    }
};

window.clearAllTvCalibrations = async function() {
    if (!confirm('Are you sure you want to clear all TV calibrations and start with a clean slate?')) return;
    try {
        const res = await fetch('/api/tv/clear_all', { method: 'POST' });
        const data = await res.json();
        showToast(data.message || 'All TV boxes cleared!');
        await fetchState();
        if (App.ctx && App.canvas) App.ctx.clearRect(0, 0, App.canvas.width, App.canvas.height);
        window.applyKeystonePreset('flat');
    } catch (e) {
        showToast('Error clearing boxes: ' + e.message, 'error');
    }
};

window.autoApplyAllDetectedTvs = async function() {
    try {
        showToast('Applying all detected screens across the room...');
        const res = await fetch('/api/calibration/auto_apply_all_tvs', { method: 'POST' });
        const data = await res.json();
        if (data.success) {
            showToast(data.message || 'All TV stations configured!');
            await fetchState();
            drawCanvasOverlay();
        } else {
            showToast(data.message || 'No screens found. Run Auto-Detect first.', 'warning');
        }
    } catch (e) {
        showToast('Error applying TVs: ' + e.message, 'error');
    }
};

window.deleteCurrentStation = async function() {
    const select = document.getElementById('station-select');
    if (!select || select.value === 'new') {
        showToast('Select an existing TV station to delete.', 'warning');
        return;
    }
    const tvId = parseInt(select.value, 10);
    if (!confirm(`Delete TV ${tvId}?`)) return;
    try {
        const res = await fetch(`/api/tv/delete/${tvId}`, { method: 'POST' });
        const data = await res.json();
        showToast(data.message || `TV ${tvId} deleted.`);
        await fetchState();
        drawCanvasOverlay();
    } catch (e) {
        showToast('Error deleting station: ' + e.message, 'error');
    }
};
"""

js += extra_functions

with open("static/js/app.js", "w", encoding="utf-8") as f:
    f.write(js)
print("Finished frontend optimizations!")
