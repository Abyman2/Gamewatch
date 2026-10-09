import os

# --- 1. UPDATE templates/index.html ---
with open("templates/index.html", "r", encoding="utf-8") as f:
    html = f.read()

# Add script tag before app.js
old_script = '<script src="/static/js/app.js?v=14"></script>'
new_script = '<script src="/static/js/offline_engine.js?v=2"></script>\n    <script src="/static/js/app.js?v=14"></script>'

if old_script in html:
    html = html.replace(old_script, new_script, 1)
    print("1. index.html script tag added")
else:
    print("1. index.html old_script not found")

# Add offline badge style in <head>
css_pill = """
    <style>
        .offline-badge-pill {
            display: inline-flex;
            align-items: center;
            gap: 6px;
            padding: 5px 12px;
            border-radius: 9999px;
            font-size: 11px;
            font-weight: 700;
            letter-spacing: 0.03em;
            text-transform: uppercase;
            transition: all 0.2s ease;
        }
        .offline-badge-pill.online {
            background: rgba(16, 185, 129, 0.12);
            border: 1px solid rgba(16, 185, 129, 0.35);
            color: #10b981;
        }
        .offline-badge-pill.offline {
            background: rgba(245, 158, 11, 0.15);
            border: 1px solid rgba(245, 158, 11, 0.45);
            color: #f59e0b;
        }
        .offline-badge-pill.syncing {
            background: rgba(6, 182, 212, 0.15);
            border: 1px solid rgba(6, 182, 212, 0.45);
            color: #06b6d4;
        }
        .offline-badge-pill.pending {
            background: rgba(139, 92, 246, 0.15);
            border: 1px solid rgba(139, 92, 246, 0.45);
            color: #a78bfa;
        }
    </style>
</head>"""

if "</head>" in html and ".offline-badge-pill" not in html:
    html = html.replace("</head>", css_pill, 1)
    print("2. index.html badge CSS added")

with open("templates/index.html", "w", encoding="utf-8") as f:
    f.write(html)


# --- 2. UPDATE static/js/app.js ---
with open("static/js/app.js", "r", encoding="utf-8") as f:
    js = f.read()

# Update fetchState to cache state & load cached state when offline
old_fetch = """async function fetchState() {
    try {
        const res = await fetch('/api/state');
        if (!res.ok) return;
        const data = await res.json();
        App.state = data;"""

new_fetch = """async function fetchState() {
    try {
        const res = await fetch('/api/state');
        if (res.ok) {
            const data = await res.json();
            App.state = data;
            if (window.offlineEngine) offlineEngine.setCachedState(data);"""

if old_fetch in js:
    js = js.replace(old_fetch, new_fetch, 1)
    print("3. app.js fetchState online branch updated")
else:
    print("3. app.js old_fetch not found")

# Update fetchState catch block
old_catch = """    } catch (err) {
        console.error('State fetch error:', err);
    }
}"""

new_catch = """    } catch (err) {
        console.warn('State fetch offline, reading from IndexedDB:', err);
        if (window.offlineEngine) {
            const cached = await offlineEngine.getCachedState();
            if (cached) {
                App.state = cached;
                renderHeader(cached);
                updateStationDropdown(cached.tvs);
                if (App.currentView === 'home') renderTvList(cached.tvs);
            }
        }
    }
}"""

if old_catch in js:
    js = js.replace(old_catch, new_catch, 1)
    print("4. app.js fetchState offline cache branch updated")
else:
    print("4. app.js old_catch not found")

# Update submitAdjustment for offline mutation
old_submit_adj = """async function submitAdjustment() {
    if (!App.pendingAdjustment) return;
    const { tvId, actionType } = App.pendingAdjustment;
    
    const selectedOpt = document.querySelector('input[name="adj-reason-opt"]:checked');
    const reason = selectedOpt ? selectedOpt.value : 'Operator adjustment';
    const noteEl = document.getElementById('adj-note');
    const explanation = noteEl ? noteEl.value.trim() : '';
    
    let endpoint = `/api/tv/${tvId}/reset_match`;
    if (actionType === 'ADD_GAME') endpoint = `/api/tv/${tvId}/add_game`;
    if (actionType === 'DEDUCT_GAME') endpoint = `/api/tv/${tvId}/deduct_game`;
    
    const clerkName = App.currentUser?.full_name || (App.currentRole === 'CLERK' ? 'Clerk' : 'Owner');
    
    try {"""

new_submit_adj = """async function submitAdjustment() {
    if (!App.pendingAdjustment) return;
    const { tvId, actionType } = App.pendingAdjustment;
    
    const selectedOpt = document.querySelector('input[name="adj-reason-opt"]:checked');
    const reason = selectedOpt ? selectedOpt.value : 'Operator adjustment';
    const noteEl = document.getElementById('adj-note');
    const explanation = noteEl ? noteEl.value.trim() : '';
    
    let endpoint = `/api/tv/${tvId}/reset_match`;
    if (actionType === 'ADD_GAME') endpoint = `/api/tv/${tvId}/add_game`;
    if (actionType === 'DEDUCT_GAME') endpoint = `/api/tv/${tvId}/deduct_game`;
    
    const clerkName = App.currentUser?.full_name || (App.currentRole === 'CLERK' ? 'Clerk' : 'Owner');
    const payload = { reason, explanation, actor: clerkName };

    // Standalone Offline Interception (Solution 2)
    if (!navigator.onLine) {
        if (window.offlineEngine) {
            await offlineEngine.queueMutation(endpoint, payload, `${actionType} on TV ${tvId}`);
            if (actionType === 'ADD_GAME') offlineEngine.optimisticAddGame(tvId, reason);
            else if (actionType === 'DEDUCT_GAME') offlineEngine.optimisticDeductGame(tvId);
            else if (actionType === 'RESET_MATCH') offlineEngine.optimisticResetMatch(tvId);
        }
        closeAdjustmentModal();
        showToast(`⚡ Offline Mode: ${actionType} saved to device outbox!`, 'warning');
        return;
    }

    try {"""

if old_submit_adj in js:
    js = js.replace(old_submit_adj, new_submit_adj, 1)
    print("5. app.js submitAdjustment offline interception added")
else:
    print("5. app.js old_submit_adj not found")

# Update confirmCheckoutPayment for offline mutation
old_checkout = """    try {
        const res = await fetch(`/api/tv/${App.activeCheckoutTvId}/checkout`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });"""

new_checkout = """    // Standalone Offline Interception (Solution 2)
    if (!navigator.onLine) {
        if (window.offlineEngine) {
            await offlineEngine.queueMutation(`/api/tv/${App.activeCheckoutTvId}/checkout`, payload, `Checkout TV ${App.activeCheckoutTvId}`);
            offlineEngine.optimisticCheckout(App.activeCheckoutTvId, App.activePaymentMethod, payload.amount_received);
        }
        closeCheckoutModal();
        showToast('⚡ Offline Mode: Checkout saved to device outbox! Will sync on reconnect.', 'warning');
        return;
    }

    try {
        const res = await fetch(`/api/tv/${App.activeCheckoutTvId}/checkout`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });"""

if old_checkout in js:
    js = js.replace(old_checkout, new_checkout, 1)
    print("6. app.js confirmCheckoutPayment offline interception added")
else:
    print("6. app.js old_checkout not found")

with open("static/js/app.js", "w", encoding="utf-8") as f:
    f.write(js)


# --- 3. UPDATE app_server.py (Cloud Frame Ingest & Relay) ---
with open("app_server.py", "r", encoding="utf-8") as f:
    py = f.read()

# Add Cloud Relay Frame Ingest endpoint
cloud_relay_code = """
# Cloud Relay Frame Storage for Remote Monitoring
CLOUD_RELAY_FRAME: Optional[np.ndarray] = None
CLOUD_RELAY_TIMESTAMP: float = 0.0

@app.route("/api/cloud/relay_frame", methods=["POST"])
def api_cloud_relay_frame():
    \"\"\"Receives a lightweight compressed frame snapshot from a local lounge PC edge node.\"\"\"
    global CLOUD_RELAY_FRAME, CLOUD_RELAY_TIMESTAMP
    data = request.json or {}
    b64_data = data.get("frame_base64")
    if not b64_data:
        return jsonify({"success": False, "message": "frame_base64 required"}), 400
    try:
        if "," in b64_data:
            b64_data = b64_data.split(",")[1]
        img_bytes = base64.b64decode(b64_data)
        np_arr = np.frombuffer(img_bytes, np.uint8)
        frame = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)
        if frame is not None:
            CLOUD_RELAY_FRAME = frame
            CLOUD_RELAY_TIMESTAMP = time.time()
            return jsonify({"success": True, "message": "Relay frame received"})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 400
    return jsonify({"success": False, "message": "Invalid image payload"}), 400
"""

if "/api/cloud/relay_frame" not in py:
    py += cloud_relay_code
    print("7. app_server.py cloud relay endpoint added")

with open("app_server.py", "w", encoding="utf-8") as f:
    f.write(py)

print("Done integrating offline engine & cloud relay!")
