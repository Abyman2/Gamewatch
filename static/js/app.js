/**
 * GameWatch™ — Mobile-First App Controller
 * Play · Manage · Connect
 */

const App = {
    currentView: 'home',
    currentRole: 'clerk',
    activeShift: null,
    pendingAdjustment: null,
    state: null,
    pollTimer: null,
    canvas: null,
    ctx: null,
    isDrawing: false,
    startX: 0,
    startY: 0,
    currentBox: null,
    lastAnalysis: null,
    activeCheckoutTvId: null,
    activePaymentMethod: 'TELEBIRR'
};

// ============================================================
// INITIALIZATION
// ============================================================
document.addEventListener('DOMContentLoaded', () => {
    initTheme();
    initSplashScreen();
    initAuthAndRole();
    initNavigation();
    initClock();
    initCalibrationCanvas();
    initCheckoutModal();
    initAdjustmentModal();
    initEndShiftModal();
    initWaitingListModal();
    initAiDiagnostics();
    initSimulationToggle();
    initKeyboardShortcuts();
    initSponsorCarousels();

    fetchShiftStatus();
    fetchWaitingList();
    fetchCameraSources();
    fetchState();
    App.pollTimer = setInterval(fetchState, 700);
});

// ============================================================
// THEME ARCHITECTURE — Dark Obsidian & Studio Light Modes
// ============================================================
function initTheme() {
    const saved = localStorage.getItem('gamewatch_theme') || 'light';
    applyTheme(saved);
}

function applyTheme(theme) {
    const isLight = theme === 'light';
    const finalTheme = isLight ? 'light' : 'dark';
    
    document.documentElement.setAttribute('data-theme', finalTheme);
    document.body.setAttribute('data-theme', finalTheme);
    localStorage.setItem('gamewatch_theme', finalTheme);

    // Update Meta Theme Color for mobile browser bars
    const metaTheme = document.querySelector('meta[name="theme-color"]');
    if (metaTheme) {
        metaTheme.setAttribute('content', isLight ? '#f8fafc' : '#060a14');
    }

    // Update Header Capsule UI
    const themeIcon = document.getElementById('header-theme-icon');
    const themeLabel = document.getElementById('header-theme-label');
    if (themeIcon) themeIcon.textContent = isLight ? '☀️' : '🌙';
    if (themeLabel) themeLabel.textContent = isLight ? 'Light' : 'Dark';

    // Update Settings View Badge & Active Button States
    const badge = document.getElementById('current-theme-badge');
    if (badge) {
        badge.textContent = isLight ? 'Light Mode (Studio Crisp)' : 'Dark Mode (Obsidian)';
        badge.className = isLight ? 'badge badge-green' : 'badge badge-cyan';
    }

    const btnDark = document.getElementById('btn-theme-dark');
    const btnLight = document.getElementById('btn-theme-light');
    if (btnDark && btnLight) {
        if (isLight) {
            btnLight.style.borderColor = 'var(--blue-electric)';
            btnLight.style.background = 'rgba(2, 132, 199, 0.12)';
            btnLight.style.color = 'var(--blue-electric)';
            btnDark.style.borderColor = 'var(--border-default)';
            btnDark.style.background = '';
            btnDark.style.color = 'var(--text-secondary)';
        } else {
            btnDark.style.borderColor = 'var(--blue-electric)';
            btnDark.style.background = 'rgba(26, 143, 255, 0.15)';
            btnDark.style.color = 'var(--blue-bright)';
            btnLight.style.borderColor = 'var(--border-default)';
            btnLight.style.background = '';
        }
    }

    // Update Operator Profile Card Theme Chips
    const opcDark = document.getElementById('opc-theme-dark');
    const opcLight = document.getElementById('opc-theme-light');
    if (opcDark && opcLight) {
        opcDark.classList.toggle('active', !isLight);
        opcLight.classList.toggle('active', isLight);
    }
}

function toggleTheme() {
    const current = document.documentElement.getAttribute('data-theme') || 'dark';
    const next = current === 'light' ? 'dark' : 'light';
    applyTheme(next);
}


// ============================================================
// NAVIGATION — Mobile Drawer, Sticky Bottom Bar + Desktop Tabs
// ============================================================
function toggleMobileNavDrawer() {
    const drawer = document.getElementById('mobile-nav-drawer');
    if (!drawer) return;
    if (drawer.classList.contains('open')) {
        closeMobileNavDrawer();
    } else {
        openMobileNavDrawer();
    }
}

function openMobileNavDrawer() {
    const drawer = document.getElementById('mobile-nav-drawer');
    const backdrop = document.getElementById('mobile-nav-backdrop');
    if (drawer) drawer.classList.add('open');
    if (backdrop) backdrop.classList.add('active');
    document.body.classList.add('nav-drawer-open');

    // Update active highlight in drawer
    document.querySelectorAll('.mnd-nav-item').forEach(m => {
        const v = m.getAttribute('data-view');
        m.classList.toggle('active', v === App.currentView || (App.currentView === 'home' && v === 'stations'));
    });

    // Populate user and lounge meta if available
    if (App.user && App.user.role) {
        const roleEl = document.getElementById('mnd-role-badge');
        if (roleEl) roleEl.textContent = App.user.role.toUpperCase();
    }
    if (App.state) {
        const lName = document.getElementById('mnd-lounge-name');
        const lCode = document.getElementById('mnd-lounge-code');
        const tvsEl = document.getElementById('mnd-active-tvs');
        if (lName && App.state.lounge_name) lName.textContent = App.state.lounge_name;
        if (lCode && App.state.lounge_code) lCode.textContent = `${App.state.lounge_code} · ${App.state.area || 'Addis Ababa'}`;
        if (tvsEl && App.state.active_stations !== undefined) tvsEl.textContent = `${App.state.active_stations} LIVE`;
    }
}

function closeMobileNavDrawer() {
    const drawer = document.getElementById('mobile-nav-drawer');
    const backdrop = document.getElementById('mobile-nav-backdrop');
    if (drawer) drawer.classList.remove('open');
    if (backdrop) backdrop.classList.remove('active');
    document.body.classList.remove('nav-drawer-open');
}

function scrollToStations() {
    setTimeout(() => {
        const el = document.getElementById('shift-banner') || document.querySelector('.page-header');
        if (el) el.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }, 100);
}

function initNavigation() {
    // Bottom nav items
    document.querySelectorAll('.mbn-tab, .nav-item').forEach(item => {
        item.addEventListener('click', () => {
            const view = item.getAttribute('data-view');
            if (view) {
                if (view === 'stations') {
                    switchView('home');
                    scrollToStations();
                } else {
                    switchView(view);
                }
            }
        });
    });

    // Desktop tab items
    document.querySelectorAll('.desktop-tab').forEach(tab => {
        tab.addEventListener('click', () => {
            const view = tab.getAttribute('data-view');
            if (view) switchView(view);
        });
    });

    // Close mobile drawer on Escape key
    document.addEventListener('keydown', (e) => {
        if (e.key === 'Escape') closeMobileNavDrawer();
    });
}

function switchView(viewId) {
    App.currentView = viewId;

    // Update bottom nav (mobile)
    document.querySelectorAll('.mbn-tab, .nav-item').forEach(n => {
        const v = n.getAttribute('data-view');
        n.classList.toggle('active', v === viewId || (viewId === 'home' && v === 'stations'));
    });

    // Update desktop tabs
    document.querySelectorAll('.desktop-tab').forEach(t => {
        t.classList.toggle('active', t.getAttribute('data-view') === viewId);
    });

    // Update mobile drawer items
    document.querySelectorAll('.mnd-nav-item').forEach(m => {
        const v = m.getAttribute('data-view');
        m.classList.toggle('active', v === viewId || (viewId === 'home' && v === 'stations'));
    });

    // Switch views
    document.querySelectorAll('.app-view').forEach(v => {
        v.classList.toggle('active', v.id === `view-${viewId}`);
    });

    const isAuthOrRole = (viewId === 'auth' || viewId === 'role-select');

    // Toggle body class for clean full-screen isolation on auth view
    if (isAuthOrRole) {
        document.body.classList.add('auth-view-active');
    } else {
        document.body.classList.remove('auth-view-active');
    }

    // Direct layout element visibility
    const sidebar = document.getElementById('app-sidebar');
    const header = document.getElementById('app-workspace-header');
    const heroBillboard = document.getElementById('hero-sponsor-billboard');
    const marqueeTicker = document.getElementById('discovery-marquee-wrap');
    const mobileBottomNav = document.getElementById('mobile-bottom-nav');

    if (sidebar) sidebar.style.display = isAuthOrRole ? 'none' : '';
    if (header) header.style.display = isAuthOrRole ? 'none' : 'flex';
    if (mobileBottomNav) mobileBottomNav.style.display = isAuthOrRole ? 'none' : '';

    if (heroBillboard) {
        heroBillboard.style.display = (!isAuthOrRole && (viewId === 'home' || viewId === 'customer')) ? 'block' : 'none';
    }
    if (marqueeTicker) {
        marqueeTicker.style.display = (!isAuthOrRole && viewId !== 'setup') ? 'block' : 'none';
    }

    // Scroll to top
    window.scrollTo({ top: 0, behavior: 'smooth' });

    // Canvas init when switching to setup
    if (viewId === 'setup') {
        setTimeout(() => {
            resizeCanvas();
            drawCanvasOverlay();
        }, 50);
        fetchCameraSources();
    } else if (viewId === 'customer') {
        fetchWaitingList();
        renderCustomerLounge();
    } else if (viewId === 'billing') {
        if (App.state) renderBilling(App.state);
    } else if (viewId === 'analytics') {
        loadBusinessAnalytics();
    } else if (viewId === 'settings') {
        loadSettingsView();
        loadPromotions();
    } else if (viewId === 'tournaments') {
        loadTournamentsHub();
    } else if (viewId === 'admin') {
        loadPlatformAdminStats();
    }
}

// ============================================================
// CLOCK
// ============================================================
function initClock() {
    function tick() {
        const now = new Date();
        const t = now.toLocaleTimeString('en-GB', { timeZone: 'Africa/Addis_Ababa', hour12: false, hour: '2-digit', minute: '2-digit', second: '2-digit' });
        const clockEl = document.getElementById('header-clock');
        const clockDesk = document.getElementById('header-clock-desk');
        if (clockEl) clockEl.textContent = t;
        if (clockDesk) clockDesk.textContent = t;
    }
    tick();
    setInterval(tick, 1000);
}

// ============================================================
// STATE POLLING & RENDERING
// ============================================================
async function fetchState() {
    try {
        const res = await fetch('/api/state');
        if (res.ok) {
            const data = await res.json();
            App.state = data;
            if (window.offlineEngine) offlineEngine.setCachedState(data);
        renderHeader(data);

        // Toggle CBE visibility in billing and checkout
        const cbePayTab = document.getElementById('tab-pay-cbe');
        const cbeCell = document.getElementById('ledger-cbe-cell');
        const cbeEnabled = (data.cbe_enabled !== false);
        if (cbePayTab) cbePayTab.style.display = cbeEnabled ? 'inline-flex' : 'none';
        if (cbeCell) cbeCell.style.display = cbeEnabled ? 'flex' : 'none';

        updateStationDropdown(data.tvs);
        if (App.currentView === 'home') renderTvList(data.tvs);
        else if (App.currentView === 'billing') renderBilling(data);
        else if (App.currentView === 'customer') renderCustomerLounge();
        else if (App.currentView === 'analytics') loadBusinessAnalytics();
        else if (App.currentView === 'settings') loadSettingsView();
        }
    } catch (err) {
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
}

function renderHeader(data) {
    const headerActive = document.getElementById('header-active-tvs');
    if (headerActive) headerActive.textContent = `${data.active_stations}/${data.total_stations}`;
    const headerActiveDesk = document.getElementById('header-active-tvs-desk');
    if (headerActiveDesk) headerActiveDesk.textContent = `${data.active_stations}/${data.total_stations}`;

    const sim = document.getElementById('btn-toggle-simulation');
    if (sim) {
        sim.textContent = data.is_simulation ? 'SIM' : 'LIVE';
        sim.className = data.is_simulation ? 'sim-toggle' : 'sim-toggle live';
    }
    const simDesk = document.getElementById('btn-toggle-simulation-desk');
    if (simDesk) {
        simDesk.textContent = data.is_simulation ? 'SIM' : 'LIVE';
        simDesk.className = data.is_simulation ? 'sim-toggle' : 'sim-toggle live';
    }

    // Telemetry bar
    const qsA = document.getElementById('qs-active');
    const qsTot = document.getElementById('qs-total');
    const qsR = document.getElementById('qs-revenue');
    const qsG = document.getElementById('qs-games');
    if (qsA) qsA.textContent = data.active_stations;
    if (qsTot) qsTot.textContent = data.total_stations;
    if (qsR) qsR.textContent = data.daily_revenue || data.current_lounge_revenue || 0;
    if (qsG) qsG.textContent = data.daily_completed_games || data.total_games || 0;

    // Mobile nav drawer lounge sync
    const mndName = document.getElementById('mnd-lounge-name');
    const mndCode = document.getElementById('mnd-lounge-code');
    const mndRole = document.getElementById('mnd-role-badge');
    if (mndName && (data.lounge_name || (App.currentUser && App.currentUser.lounge_name))) {
        mndName.textContent = data.lounge_name || App.currentUser.lounge_name;
    }
    if (mndCode && (data.lounge_code || (App.currentUser && App.currentUser.lounge_code))) {
        const code = data.lounge_code || App.currentUser.lounge_code;
        const area = data.lounge_area || (App.currentUser && App.currentUser.lounge_area) || 'Addis Ababa';
        mndCode.textContent = `${code} · ${area}`;
    }
    if (mndRole && (App.currentRole || (App.currentUser && App.currentUser.role))) {
        mndRole.textContent = (App.currentRole || App.currentUser.role).toUpperCase();
    }
}

// ============================================================
// TV STATION CARDS (Bespoke Broadcast Aesthetics)
// ============================================================
function renderTvList(tvs) {
    const grid = document.getElementById('tv-stations-grid');
    if (!grid || !tvs) return;

    tvs.forEach(tv => {
        let card = document.getElementById(`tv-card-${tv.id}`);
        if (!card) {
            card = createTvCard(tv);
            grid.appendChild(card);
        } else {
            updateTvCard(card, tv);
        }
    });

    // Remove stale
    grid.querySelectorAll('.tv-card').forEach(card => {
        const id = parseInt(card.id.replace('tv-card-', ''));
        if (!tvs.some(t => t.id === id)) card.remove();
    });
}

function createTvCard(tv) {
    const card = document.createElement('div');
    card.className = 'tv-card';
    card.id = `tv-card-${tv.id}`;

    const isProg = tv.state === 'MATCH_IN_PROGRESS';
    const stClass = isProg ? 'in-progress' : 'waiting';
    const stText = isProg ? 'LIVE MATCH' : (tv.state === 'WAITING' ? 'IDLE' : tv.state);

    card.innerHTML = `
        <div class="tv-card-head">
            <div class="tv-info">
                <div class="tv-title-row">
                    <span class="tv-num">TV ${tv.id}</span>
                    <span class="tv-sep">/</span>
                    <span class="tv-name" id="name-${tv.id}">${tv.name}</span>
                </div>
                <div class="tv-cust-sub" id="cust-${tv.id}">${tv.customer_name ? tv.customer_name : 'Available Station'}</div>
            </div>
            <div class="tv-status-badge ${stClass}" id="status-${tv.id}">
                <span class="status-pulse"></span>
                <span class="status-label">${stText}</span>
            </div>
        </div>

        <div class="tv-video">
            <img src="/api/stream/tv/${tv.id}?t=${Date.now()}" alt="TV ${tv.id}">
            
            <!-- Broadcast Match Bug (Bottom-Left) -->
            <div class="broadcast-hud">
                <div class="hud-item hud-time">
                    <span class="hud-icon">⏱</span>
                    <span class="hud-mono" id="clock-${tv.id}">${tv.clock}</span>
                </div>
                <div class="hud-divider"></div>
                <div class="hud-item hud-score">
                    <span class="hud-mono score" id="score-${tv.id}">${tv.score}</span>
                </div>
            </div>

            <!-- Vision Quality Indicator (Bottom-Right) -->
            <div class="vision-hud" id="conf-badge-${tv.id}">
                <span class="vision-dot"></span>
                <span id="conf-${tv.id}">${tv.confidence}%</span>
            </div>
        </div>

        <div class="tv-card-body">
            <div class="tv-financial-strip">
                <div class="fin-meta">
                    <div class="fin-games-row">
                        <strong id="games-${tv.id}">${tv.completed_games} Games</strong>
                        <span class="fin-badge">Session #${tv.session_id || 1}</span>
                    </div>
                    <span class="fin-rate">25 ETB / game</span>
                </div>
                <div class="fin-total">
                    <span class="fin-total-label">UNBILLED</span>
                    <div class="fin-total-val" id="bill-${tv.id}">${tv.bill_etb} <span class="fin-curr">ETB</span></div>
                </div>
            </div>

            <!-- Action Deck: Dominant Primary CTA + Secondary Utilities -->
            <div class="tv-action-deck">
                <button class="btn-primary-checkout" onclick="openCheckoutModal(${tv.id})">
                    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2"><rect x="2" y="5" width="20" height="14" rx="2"></rect><line x1="2" y1="10" x2="22" y2="10"></line></svg>
                    <span>Checkout <span id="btn-amt-${tv.id}">(${tv.bill_etb} ETB)</span></span>
                </button>
                <div class="tv-utility-row">
                    <button class="btn-util" onclick="openAdjustmentModal(${tv.id}, 'ADD_GAME')" title="Manual Game">+1 Manual</button>
                    <button class="btn-util btn-util-deduct" onclick="openAdjustmentModal(${tv.id}, 'DEDUCT_GAME')" title="Deduct Game">-1 Deduct</button>
                    <button class="btn-util" onclick="openAdjustmentModal(${tv.id}, 'RESET_MATCH')" title="Reset Match">Reset</button>
                    <button class="btn-util" onclick="calibrateTvDirect(${tv.id})" title="Adjust Bounds">Calibrate</button>
                </div>
            </div>
        </div>
    `;
    return card;
}

function updateTvCard(card, tv) {
    const isProg = tv.state === 'MATCH_IN_PROGRESS';
    const sb = card.querySelector(`#status-${tv.id}`);
    if (sb) {
        sb.className = `tv-status-badge ${isProg ? 'in-progress' : 'waiting'}`;
        const lbl = sb.querySelector('.status-label');
        if (lbl) lbl.textContent = isProg ? 'LIVE MATCH' : (tv.state === 'WAITING' ? 'IDLE' : tv.state);
    }

    const el = (id) => card.querySelector(`#${id}`);
    const set = (id, val) => { const e = el(id); if (e) e.textContent = val; };

    set(`clock-${tv.id}`, tv.clock);
    set(`score-${tv.id}`, tv.score);
    set(`conf-${tv.id}`, `${tv.confidence}%`);
    set(`games-${tv.id}`, `${tv.completed_games} Games`);
    
    const billEl = el(`bill-${tv.id}`);
    if (billEl) {
        billEl.innerHTML = `${tv.bill_etb} <span class="fin-curr">ETB</span>`;
    }
    
    const btnAmt = el(`btn-amt-${tv.id}`);
    if (btnAmt) {
        btnAmt.textContent = `(${tv.bill_etb} ETB)`;
    }

    set(`cust-${tv.id}`, tv.customer_name ? tv.customer_name : 'Available Station');
}

// TV Actions & Audited Adjustments (PRD Rule 2)
window.addGame = function(tvId) {
    openAdjustmentModal(tvId, 'ADD_GAME');
};

window.resetMatch = function(tvId) {
    openAdjustmentModal(tvId, 'RESET_MATCH');
};

window.calibrateTvDirect = function(tvId) {
    switchView('setup');
    const select = document.getElementById('station-select');
    if (select) {
        select.value = tvId;
        select.dispatchEvent(new Event('change'));
    }
};

// ============================================================
// CALIBRATION CANVAS (with touch support)
// ============================================================
// ============================================================
// CALIBRATION CANVAS: 4-POINT KEYSTONE & HOMOGRAPHY SYSTEM
// Hardened for Angled CCTV Cameras & Tilted Phone Tripods
// ============================================================
App.calibMode = 'keystone'; // 'keystone' (4-Point Homography) or 'box' (Axis-Aligned Rectangle)
App.antiGlare = true;
App.pins = [
    { x: 80, y: 20, label: 'TL', color: '#10B981' },
    { x: 580, y: 15, label: 'TR', color: '#06B6D4' },
    { x: 600, y: 345, label: 'BR', color: '#8B5CF6' },
    { x: 70, y: 335, label: 'BL', color: '#F59E0B' }
];
App.draggedPinIdx = -1;
App.isDraggingQuad = false;
App.dragStartMouse = { x: 0, y: 0 };
App.dragStartPins = [];

function initPinsFromBox(box) {
    if (!box || box.length < 4) return;
    const [x, y, w, h] = box;
    App.pins = [
        { x: x, y: y, label: 'TL', color: '#10B981' },
        { x: x + w, y: y, label: 'TR', color: '#06B6D4' },
        { x: x + w, y: y + h, label: 'BR', color: '#8B5CF6' },
        { x: x, y: y + h, label: 'BL', color: '#F59E0B' }
    ];
}

function isPointInQuad(px, py, pins) {
    if (!pins || pins.length < 4) return false;
    let inside = false;
    for (let i = 0, j = pins.length - 1; i < pins.length; j = i++) {
        const xi = pins[i].x, yi = pins[i].y;
        const xj = pins[j].x, yj = pins[j].y;
        const intersect = ((yi > py) !== (yj > py)) && (px < (xj - xi) * (py - yi) / (yj - yi) + xi);
        if (intersect) inside = !inside;
    }
    return inside;
}

window.setCalibrationMode = function(mode) {
    App.calibMode = mode;
    const btnKey = document.getElementById('btn-mode-keystone');
    const btnBox = document.getElementById('btn-mode-box');
    if (btnKey) btnKey.classList.toggle('active', mode === 'keystone');
    if (btnBox) btnBox.classList.toggle('active', mode === 'box');

    if (mode === 'keystone') {
        if (!App.pins || App.pins.length !== 4) {
            initPinsFromBox(App.currentBox || [80, 20, 520, 325]);
        }
        triggerKeystoneAnalysis();
    } else {
        if (!App.currentBox && App.pins && App.pins.length === 4) {
            const xs = App.pins.map(p => p.x);
            const ys = App.pins.map(p => p.y);
            App.currentBox = [Math.min(...xs), Math.min(...ys), Math.max(...xs) - Math.min(...xs), Math.max(...ys) - Math.min(...ys)];
        }
        if (App.currentBox) triggerScreenAnalysis(App.currentBox);
    }
    drawCanvasOverlay();
    updateCoordDisplay();
    showToast(mode === 'keystone' ? '⬡ 4-Point Keystone Calibration activated (Angled Security Camera)' : '⬚ Rectangle Box selection activated');
};

window.toggleAntiGlare = function(enabled) {
    App.antiGlare = !!enabled;
    const desc = document.getElementById('anti-glare-desc');
    if (desc) desc.textContent = enabled ? 'Glare: Filter Active' : 'Glare: Off (Raw)';
    if (App.calibMode === 'keystone') {
        triggerKeystoneAnalysis();
    } else if (App.currentBox) {
        triggerScreenAnalysis(App.currentBox);
    }
    showToast(enabled ? '☀ Anti-Glare Filter ON (Ceiling reflections suppressed)' : 'Anti-Glare Filter OFF');
};

window.applyKeystonePreset = function(preset) {
    App.calibMode = 'keystone';
    const btnKey = document.getElementById('btn-mode-keystone');
    const btnBox = document.getElementById('btn-mode-box');
    if (btnKey) btnKey.classList.add('active');
    if (btnBox) btnBox.classList.remove('active');

    let cx = 100, cy = 40, cw = 500, ch = 320;
    if (App.currentBox && App.currentBox[2] > 50) {
        [cx, cy, cw, ch] = App.currentBox;
    }

    if (preset === 'flat') {
        App.pins = [
            { x: cx, y: cy, label: 'TL', color: '#10B981' },
            { x: cx + cw, y: cy, label: 'TR', color: '#06B6D4' },
            { x: cx + cw, y: cy + ch, label: 'BR', color: '#8B5CF6' },
            { x: cx, y: cy + ch, label: 'BL', color: '#F59E0B' }
        ];
    } else if (preset === 'ceiling') {
        const inset = Math.round(cw * 0.12);
        const pitchDip = Math.round(ch * 0.08);
        App.pins = [
            { x: cx, y: cy, label: 'TL', color: '#10B981' },
            { x: cx + cw, y: cy, label: 'TR', color: '#06B6D4' },
            { x: cx + cw - inset, y: cy + ch + pitchDip, label: 'BR', color: '#8B5CF6' },
            { x: cx + inset, y: cy + ch + pitchDip, label: 'BL', color: '#F59E0B' }
        ];
    } else if (preset === 'left') {
        const skew = Math.round(ch * 0.15);
        App.pins = [
            { x: cx, y: cy, label: 'TL', color: '#10B981' },
            { x: cx + cw, y: cy + skew, label: 'TR', color: '#06B6D4' },
            { x: cx + cw, y: cy + ch - skew, label: 'BR', color: '#8B5CF6' },
            { x: cx, y: cy + ch, label: 'BL', color: '#F59E0B' }
        ];
    } else if (preset === 'right') {
        const skew = Math.round(ch * 0.15);
        App.pins = [
            { x: cx, y: cy + skew, label: 'TL', color: '#10B981' },
            { x: cx + cw, y: cy, label: 'TR', color: '#06B6D4' },
            { x: cx + cw, y: cy + ch, label: 'BR', color: '#8B5CF6' },
            { x: cx, y: cy + ch - skew, label: 'BL', color: '#F59E0B' }
        ];
    }

    drawCanvasOverlay();
    updateCoordDisplay();
    triggerKeystoneAnalysis();
    showToast(`📐 Preset '${preset.toUpperCase()}' applied!`);
};

window.resetActivePins = function() {
    window.applyKeystonePreset('flat');
};

function initCalibrationCanvas() {
    App.canvas = document.getElementById('calibration-canvas');
    if (!App.canvas) return;
    App.ctx = App.canvas.getContext('2d');

    App.canvas.width = 1280;
    App.canvas.height = 576;

    // Mouse events
    App.canvas.addEventListener('mousedown', onPointerStart);
    App.canvas.addEventListener('mousemove', onPointerMove);
    App.canvas.addEventListener('mouseup', onPointerEnd);

    // Touch events
    App.canvas.addEventListener('touchstart', (e) => { e.preventDefault(); onPointerStart(e.touches[0]); }, { passive: false });
    App.canvas.addEventListener('touchmove', (e) => { e.preventDefault(); onPointerMove(e.touches[0]); }, { passive: false });
    App.canvas.addEventListener('touchend', (e) => { e.preventDefault(); onPointerEnd(e); }, { passive: false });

    function getCanvasCoords(e) {
        const rect = App.canvas.getBoundingClientRect();
        const scaleX = App.canvas.width / rect.width;
        const scaleY = App.canvas.height / rect.height;
        return {
            x: (e.clientX - rect.left) * scaleX,
            y: (e.clientY - rect.top) * scaleY
        };
    }

    function onPointerStart(e) {
        const coords = getCanvasCoords(e);

        if (App.calibMode === 'keystone' && App.pins && App.pins.length === 4) {
            // 1. Check if clicking on any of the 4 corner pins (radius 22)
            for (let i = 0; i < App.pins.length; i++) {
                const dist = Math.hypot(App.pins[i].x - coords.x, App.pins[i].y - coords.y);
                if (dist <= 24) {
                    App.draggedPinIdx = i;
                    App.isDrawing = true;
                    return;
                }
            }

            // 2. Check if clicking inside quad to move the whole polygon
            if (isPointInQuad(coords.x, coords.y, App.pins)) {
                App.isDraggingQuad = true;
                App.dragStartMouse = coords;
                App.dragStartPins = App.pins.map(p => ({ x: p.x, y: p.y }));
                App.isDrawing = true;
                return;
            }
        }

        // Box Mode fallback or clicking outside quad
        App.isDrawing = true;
        App.startX = coords.x;
        App.startY = coords.y;
        App.currentBox = null;
    }

    function onPointerMove(e) {
        const coords = getCanvasCoords(e);

        // Update cursor style on hover
        if (!App.isDrawing && App.calibMode === 'keystone' && App.pins) {
            let hitPin = false;
            for (let i = 0; i < App.pins.length; i++) {
                if (Math.hypot(App.pins[i].x - coords.x, App.pins[i].y - coords.y) <= 24) {
                    hitPin = true;
                    break;
                }
            }
            if (hitPin) {
                App.canvas.style.cursor = 'grab';
            } else if (isPointInQuad(coords.x, coords.y, App.pins)) {
                App.canvas.style.cursor = 'move';
            } else {
                App.canvas.style.cursor = 'crosshair';
            }
        }

        if (!App.isDrawing) return;

        if (App.calibMode === 'keystone' && App.draggedPinIdx >= 0) {
            App.canvas.style.cursor = 'grabbing';
            App.pins[App.draggedPinIdx].x = Math.max(0, Math.min(App.canvas.width, Math.round(coords.x)));
            App.pins[App.draggedPinIdx].y = Math.max(0, Math.min(App.canvas.height, Math.round(coords.y)));
            drawCanvasOverlay();
            updateCoordDisplay();
            return;
        }

        if (App.calibMode === 'keystone' && App.isDraggingQuad) {
            App.canvas.style.cursor = 'grabbing';
            const dx = coords.x - App.dragStartMouse.x;
            const dy = coords.y - App.dragStartMouse.y;
            for (let i = 0; i < App.pins.length; i++) {
                App.pins[i].x = Math.max(0, Math.min(App.canvas.width, Math.round(App.dragStartPins[i].x + dx)));
                App.pins[i].y = Math.max(0, Math.min(App.canvas.height, Math.round(App.dragStartPins[i].y + dy)));
            }
            drawCanvasOverlay();
            updateCoordDisplay();
            return;
        }

        // Standard Box drag
        const x = Math.min(App.startX, coords.x);
        const y = Math.min(App.startY, coords.y);
        const w = Math.abs(coords.x - App.startX);
        const h = Math.abs(coords.y - App.startY);
        App.currentBox = [Math.round(x), Math.round(y), Math.round(w), Math.round(h)];
        if (App.calibMode === 'keystone') {
            initPinsFromBox(App.currentBox);
        }
        drawCanvasOverlay();
        updateCoordDisplay(App.currentBox);
    }

    function onPointerEnd() {
        if (!App.isDrawing) return;
        App.isDrawing = false;
        App.canvas.style.cursor = 'default';

        if (App.calibMode === 'keystone') {
            const wasPin = (App.draggedPinIdx >= 0 || App.isDraggingQuad);
            App.draggedPinIdx = -1;
            App.isDraggingQuad = false;
            triggerKeystoneAnalysis();
            return;
        }

        App.draggedPinIdx = -1;
        App.isDraggingQuad = false;
        if (App.currentBox && App.currentBox[2] > 30 && App.currentBox[3] > 30) {
            triggerScreenAnalysis(App.currentBox);
        }
    }

    document.getElementById('btn-clear-selection').addEventListener('click', () => {
        App.currentBox = null;
        if (App.calibMode === 'keystone') {
            window.applyKeystonePreset('flat');
        } else {
            drawCanvasOverlay();
            updateCoordDisplay(null);
            resetAnalysisPanel();
        }
    });

    document.getElementById('btn-analyze-now').addEventListener('click', () => {
        if (App.calibMode === 'keystone') {
            triggerKeystoneAnalysis();
        } else if (App.currentBox) {
            triggerScreenAnalysis(App.currentBox);
        } else {
            showToast('Calibrate TV boundaries first');
        }
    });

    document.getElementById('btn-studio-save-station').addEventListener('click', saveStationFromStudio);

    const stationSelect = document.getElementById('station-select');
    stationSelect.addEventListener('change', () => {
        const val = stationSelect.value;
        const nameInput = document.getElementById('station-name-input');
        const custInput = document.getElementById('customer-name-input');

        if (val === 'new') {
            const nextId = (App.state && App.state.tvs) ? App.state.tvs.length + 1 : 3;
            nameInput.value = `TV ${nextId} - Station`;
            custInput.value = '';
            window.applyKeystonePreset('flat');
        } else {
            const id = parseInt(val);
            const found = App.state && App.state.tvs ? App.state.tvs.find(t => t.id === id) : null;
            if (found) {
                nameInput.value = found.name;
                custInput.value = found.customer_name || '';
                if (found.corners && found.corners.length === 4) {
                    window.setCalibrationMode('keystone');
                    App.pins = [
                        { x: found.corners[0][0], y: found.corners[0][1], label: 'TL', color: '#10B981' },
                        { x: found.corners[1][0], y: found.corners[1][1], label: 'TR', color: '#06B6D4' },
                        { x: found.corners[2][0], y: found.corners[2][1], label: 'BR', color: '#8B5CF6' },
                        { x: found.corners[3][0], y: found.corners[3][1], label: 'BL', color: '#F59E0B' }
                    ];
                    drawCanvasOverlay();
                    updateCoordDisplay();
                    triggerKeystoneAnalysis();
                } else if (found.roi) {
                    App.currentBox = found.roi;
                    initPinsFromBox(found.roi);
                    drawCanvasOverlay();
                    updateCoordDisplay(App.currentBox);
                    if (App.calibMode === 'keystone') triggerKeystoneAnalysis();
                    else triggerScreenAnalysis(App.currentBox);
                }
            }
        }
    });

    // Initial default trigger
    setTimeout(() => {
        if (App.calibMode === 'keystone' && App.pins) {
            triggerKeystoneAnalysis();
        }
    }, 600);
}

function resizeCanvas() {
    if (!App.canvas) return;
    App.canvas.width = 1280;
    App.canvas.height = 576;
}

function drawCVTag(ctx, text, x, y, borderColor, textColor, bgColor) {
    ctx.save();
    ctx.font = 'bold 11px Inter, sans-serif';
    const textWidth = ctx.measureText(text).width;
    const padX = 7;
    const tagH = 18;
    const tagW = textWidth + padX * 2;
    const tagY = Math.max(4, y - tagH - 4);
    const radius = 4;

    ctx.fillStyle = bgColor || 'rgba(6, 26, 53, 0.90)';
    ctx.beginPath();
    if (ctx.roundRect) {
        ctx.roundRect(x, tagY, tagW, tagH, radius);
    } else {
        ctx.rect(x, tagY, tagW, tagH);
    }
    ctx.fill();

    ctx.strokeStyle = borderColor || textColor;
    ctx.lineWidth = 1;
    ctx.stroke();

    ctx.fillStyle = textColor;
    ctx.textBaseline = 'middle';
    ctx.fillText(text, x + padX, tagY + tagH / 2);
    ctx.restore();
}

function drawCanvasOverlay() {
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
    }

    // 2. Render active calibration selection
    if (App.calibMode === 'keystone' && App.pins && App.pins.length === 4) {
        const [tl, tr, br, bl] = App.pins;

        App.ctx.save();
        // Quad fill
        App.ctx.beginPath();
        App.ctx.moveTo(tl.x, tl.y);
        App.ctx.lineTo(tr.x, tr.y);
        App.ctx.lineTo(br.x, br.y);
        App.ctx.lineTo(bl.x, bl.y);
        App.ctx.closePath();
        App.ctx.fillStyle = 'rgba(7, 95, 232, 0.12)';
        App.ctx.fill();

        // Dashed outline
        App.ctx.strokeStyle = '#075FE8';
        App.ctx.lineWidth = 2.5;
        App.ctx.setLineDash([8, 5]);
        App.ctx.stroke();
        App.ctx.setLineDash([]);

        // Subtle diagonals
        App.ctx.beginPath();
        App.ctx.moveTo(tl.x, tl.y);
        App.ctx.lineTo(br.x, br.y);
        App.ctx.moveTo(tr.x, tr.y);
        App.ctx.lineTo(bl.x, bl.y);
        App.ctx.strokeStyle = 'rgba(255, 255, 255, 0.16)';
        App.ctx.lineWidth = 1;
        App.ctx.stroke();

        // Center move handle
        const midX = (tl.x + tr.x + br.x + bl.x) / 4;
        const midY = (tl.y + tr.y + br.y + bl.y) / 4;
        App.ctx.beginPath();
        App.ctx.arc(midX, midY, 15, 0, Math.PI * 2);
        App.ctx.fillStyle = 'rgba(7, 95, 232, 0.90)';
        App.ctx.fill();
        App.ctx.strokeStyle = '#FFFFFF';
        App.ctx.lineWidth = 2;
        App.ctx.stroke();

        App.ctx.fillStyle = '#FFFFFF';
        App.ctx.font = '13px sans-serif';
        App.ctx.textAlign = 'center';
        App.ctx.textBaseline = 'middle';
        App.ctx.fillText('✥', midX, midY);

        drawCVTag(App.ctx, 'Keystone Quadrilateral (Drag Corners to Align)', tl.x, tl.y, '#075FE8', '#FFFFFF', 'rgba(7, 95, 232, 0.95)');

        // Draw 4 Corner Pin Handles
        App.pins.forEach((p, idx) => {
            // Glowing outer ring
            App.ctx.beginPath();
            App.ctx.arc(p.x, p.y, 16, 0, Math.PI * 2);
            App.ctx.fillStyle = `${p.color}33`;
            App.ctx.fill();

            // Pin solid circle
            App.ctx.beginPath();
            App.ctx.arc(p.x, p.y, 9, 0, Math.PI * 2);
            App.ctx.fillStyle = p.color;
            App.ctx.fill();
            App.ctx.strokeStyle = '#FFFFFF';
            App.ctx.lineWidth = 2.5;
            App.ctx.stroke();

            // Pin label pill
            const tagX = p.x + (idx === 1 || idx === 2 ? 14 : -38);
            const tagY = p.y + (idx >= 2 ? 14 : -18);
            App.ctx.fillStyle = '#061A35';
            App.ctx.beginPath();
            if (App.ctx.roundRect) App.ctx.roundRect(tagX, tagY, 26, 16, 4);
            else App.ctx.rect(tagX, tagY, 26, 16);
            App.ctx.fill();
            App.ctx.strokeStyle = p.color;
            App.ctx.lineWidth = 1;
            App.ctx.stroke();

            App.ctx.fillStyle = '#FFFFFF';
            App.ctx.font = 'bold 10px Inter, sans-serif';
            App.ctx.textAlign = 'center';
            App.ctx.textBaseline = 'middle';
            App.ctx.fillText(p.label, tagX + 13, tagY + 8);
        });

        App.ctx.restore();
    } else if (App.currentBox) {
        const [x, y, w, h] = App.currentBox;
        App.ctx.save();
        App.ctx.fillStyle = 'rgba(22, 135, 255, 0.12)';
        App.ctx.fillRect(x, y, w, h);
        App.ctx.strokeStyle = '#1687FF';
        App.ctx.lineWidth = 2;
        App.ctx.strokeRect(x, y, w, h);
        drawCVTag(App.ctx, 'Selecting Screen...', x, y, '#1687FF', '#FFFFFF', 'rgba(7, 95, 232, 0.92)');

        if (App.lastAnalysis && App.lastAnalysis.scoreboard_box) {
            const [sx, sy, sw, sh] = App.lastAnalysis.scoreboard_box;
            App.ctx.strokeStyle = '#16B8FF';
            App.ctx.lineWidth = 1.5;
            App.ctx.strokeRect(x + sx, y + sy, sw, sh);
            const conf = Math.round((App.lastAnalysis.confidence || 0.95) * 100);
            drawCVTag(App.ctx, `Scoreboard (${conf}%)`, x + sx, y + sy, '#16B8FF', '#16B8FF', 'rgba(6, 26, 53, 0.92)');
        }
        App.ctx.restore();
    }
}

function updateCoordDisplay(box) {
    const el = document.getElementById('roi-coords-display');
    if (!el) return;
    if (App.calibMode === 'keystone' && App.pins && App.pins.length === 4) {
        el.textContent = App.pins.map(p => `${p.label}:[${Math.round(p.x)},${Math.round(p.y)}]`).join(' ');
    } else if (box) {
        el.textContent = `x:${box[0]}, y:${box[1]}, w:${box[2]}, h:${box[3]}`;
    } else {
        el.textContent = 'TL:--, TR:--, BR:--, BL:--';
    }
}

async function triggerKeystoneAnalysis() {
    if (!App.pins || App.pins.length !== 4) return;
    const badge = document.getElementById('crop-status-badge');
    const badgeText = document.getElementById('crop-status-text');
    if (badgeText) badgeText.textContent = 'Rectifying Screen...';

    const corners = App.pins.map(p => [Math.round(p.x), Math.round(p.y)]);
    
    try {
        const res = await fetch('/api/tv/analyze_crop', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                corners: corners,
                anti_glare: App.antiGlare !== false
            })
        });
        const data = await res.json();
        App.lastAnalysis = data;

        if (data.success) {
            if (data.tv_preview) {
                document.getElementById('preview-tv-container').innerHTML = `<img src="${data.tv_preview}" alt="TV">`;
            }
            if (data.scoreboard_preview) {
                document.getElementById('preview-sb-container').innerHTML = `<img src="${data.scoreboard_preview}" alt="SB">`;
            }
            const clockEl = document.getElementById('crop-clock-read');
            const scoreEl = document.getElementById('crop-score-read');
            const confEl = document.getElementById('crop-conf-read');
            if (clockEl) clockEl.textContent = data.clock_str || '--:--';
            if (scoreEl) scoreEl.textContent = data.score || '-:-';
            if (confEl) confEl.textContent = `${Math.round((data.ocr_confidence || 0) * 100)}%`;

            // Update keystone telemetry badges
            const kBadge = document.getElementById('keystone-angle-badge');
            const kDesc = document.getElementById('keystone-tilt-desc');
            if (data.keystone) {
                const tilt = data.keystone.composite_tilt || 0;
                const txt = `📐 Keystone: ${tilt}° (${data.keystone.is_angled ? 'Compensated' : 'Flat'})`;
                if (kBadge) kBadge.textContent = txt;
                if (kDesc) kDesc.textContent = `Angle: ${tilt}° (${data.keystone.yaw_angle}° Yaw, ${data.keystone.pitch_angle}° Pitch)`;
            }

            if (data.scoreboard_found) {
                if (badge) badge.className = 'crop-status verified';
                if (badgeText) badgeText.textContent = `Scoreboard found (${Math.round((data.confidence || 0.95) * 100)}%)`;
            } else {
                if (badge) badge.className = 'crop-status';
                if (badgeText) badgeText.textContent = 'Screen Rectified (Ready for Match)';
            }
            drawCanvasOverlay();
        }
    } catch (e) {
        console.error('Keystone analysis error:', e);
        if (badgeText) badgeText.textContent = 'Error';
    }
}

async function triggerScreenAnalysis(box) {
    const badge = document.getElementById('crop-status-badge');
    const badgeText = document.getElementById('crop-status-text');
    badge.className = 'crop-status';
    badgeText.textContent = 'Analyzing...';

    try {
        const res = await fetch('/api/tv/analyze_crop', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ 
                x: box[0], y: box[1], width: box[2], height: box[3],
                anti_glare: App.antiGlare !== false
            })
        });
        const data = await res.json();
        App.lastAnalysis = data;

        if (data.success) {
            if (data.tv_preview) {
                document.getElementById('preview-tv-container').innerHTML = `<img src="${data.tv_preview}" alt="TV">`;
            }
            if (data.scoreboard_preview) {
                document.getElementById('preview-sb-container').innerHTML = `<img src="${data.scoreboard_preview}" alt="SB">`;
            }
            document.getElementById('crop-clock-read').textContent = data.clock_str;
            document.getElementById('crop-score-read').textContent = data.score;
            document.getElementById('crop-conf-read').textContent = `${Math.round(data.ocr_confidence * 100)}%`;

            if (data.scoreboard_found) {
                badge.className = 'crop-status verified';
                badgeText.textContent = `Scoreboard found (${Math.round(data.confidence * 100)}%)`;
            } else {
                badge.className = 'crop-status';
                badgeText.textContent = 'TV locked (waiting for match)';
            }
            drawCanvasOverlay();
        }
    } catch (e) {
        console.error('Analysis error:', e);
        badgeText.textContent = 'Error';
    }
}

function resetAnalysisPanel() {
    App.lastAnalysis = null;
    document.getElementById('preview-tv-container').innerHTML = '<span class="placeholder-text">Draw box</span>';
    document.getElementById('preview-sb-container').innerHTML = '<span class="placeholder-text">Auto-detect</span>';
    document.getElementById('crop-clock-read').textContent = '--:--';
    document.getElementById('crop-score-read').textContent = '-:-';
    document.getElementById('crop-conf-read').textContent = '--%';
    document.getElementById('crop-status-badge').className = 'crop-status';
    document.getElementById('crop-status-text').textContent = 'Awaiting selection';
}

async function saveStationFromStudio() {
    const select = document.getElementById('station-select');
    let tvId = select.value === 'new' ? ((App.state && App.state.tvs) ? App.state.tvs.length + 1 : 3) : parseInt(select.value);
    const name = document.getElementById('station-name-input').value.trim() || `TV ${tvId}`;
    const cust = document.getElementById('customer-name-input').value.trim() || '';

    let corners = null;
    let roi = App.currentBox;

    if (App.calibMode === 'keystone' && App.pins && App.pins.length === 4) {
        corners = App.pins.map(p => [Math.round(p.x), Math.round(p.y)]);
        const xs = corners.map(p => p[0]);
        const ys = corners.map(p => p[1]);
        const minX = Math.min(...xs), maxX = Math.max(...xs);
        const minY = Math.min(...ys), maxY = Math.max(...ys);
        roi = [minX, minY, maxX - minX, maxY - minY];
    }

    if (!corners && !roi) {
        showToast('Calibrate TV screen boundaries first', 'error');
        return;
    }

    const payload = {
        tv_id: tvId,
        name: name,
        customer_name: cust,
        roi: roi,
        corners: corners,
        enable_anti_glare: App.antiGlare !== false,
        scoreboard_roi: App.lastAnalysis && App.lastAnalysis.scoreboard_box ? App.lastAnalysis.scoreboard_box : null
    };

    try {
        const res = await fetch('/api/tv/save', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });
        const data = await res.json();
        showToast(data.message || `TV ${tvId} saved!`);
        await fetchState();

        if (select.value === 'new') {
            const opt = document.createElement('option');
            opt.value = tvId;
            opt.textContent = name;
            select.insertBefore(opt, select.lastElementChild);
            select.value = tvId;
        }
    } catch (e) { showToast('Error saving station', 'error'); }
}

// ============================================================
// CHECKOUT MODAL
// ============================================================
// ============================================================
// CHECKOUT MODAL (PRD Rule 13, 14, 15, 19)
// ============================================================
function initCheckoutModal() {
    const modal = document.getElementById('checkout-modal');
    const closeBtn = document.getElementById('btn-close-modal');
    const cancelBtn = document.getElementById('btn-modal-cancel');
    if (closeBtn) closeBtn.addEventListener('click', closeCheckoutModal);
    if (cancelBtn) cancelBtn.addEventListener('click', closeCheckoutModal);

    if (modal) {
        modal.addEventListener('click', (e) => {
            if (e.target === modal) closeCheckoutModal();
        });
    }

    document.querySelectorAll('.pay-tab').forEach(tab => {
        tab.addEventListener('click', () => {
            document.querySelectorAll('.pay-tab').forEach(t => t.classList.remove('active'));
            tab.classList.add('active');
            App.activePaymentMethod = tab.getAttribute('data-method');
            updateModalQrView();
        });
    });

    const confirmBtn = document.getElementById('btn-modal-confirm-pay');
    if (confirmBtn) confirmBtn.addEventListener('click', confirmCheckoutPayment);
}

function openCheckoutModal(tvId) {
    if (!App.state || !App.state.tvs) return;
    const tv = App.state.tvs.find(t => String(t.id) === String(tvId));
    if (!tv) return;

    App.activeCheckoutTvId = tv.id;
    App.activePaymentMethod = 'CASH'; // Fast, seamless 1-tap checkout default for Owner & Clerk

    const stationEl = document.getElementById('modal-station-title');
    const custEl = document.getElementById('modal-customer-name');
    const gamesEl = document.getElementById('modal-verified-games');
    const rateEl = document.getElementById('modal-rate-display');
    const totalEl = document.getElementById('modal-total-price');
    const discountEl = document.getElementById('modal-discount-price');

    if (stationEl) stationEl.textContent = tv.name;
    if (custEl) custEl.textContent = tv.customer_name || 'Walk-in Gamer';
    if (gamesEl) gamesEl.textContent = `${tv.completed_games} Games`;
    if (rateEl) rateEl.textContent = `25 ETB/game`;
    if (discountEl) discountEl.textContent = `0 ETB`;
    if (totalEl) totalEl.textContent = `${tv.bill_etb} ETB`;

    const cashInput = document.getElementById('checkout-cash-received');
    if (cashInput) cashInput.value = tv.bill_etb || 0;

    const digitalRefInput = document.getElementById('checkout-digital-ref');
    if (digitalRefInput) digitalRefInput.value = '';

    const notesInput = document.getElementById('checkout-notes-input');
    if (notesInput) notesInput.value = '';

    calculateCashChange();

    // Reset payment proof safely
    try { clearPaymentProof(); } catch (e) {}
    try { stopWebcamProofStream(); } catch (e) {}

    document.querySelectorAll('.pay-tab').forEach(t => {
        t.classList.toggle('active', t.getAttribute('data-method') === App.activePaymentMethod);
    });
    updateModalQrView();

    const modal = document.getElementById('checkout-modal');
    if (modal) modal.classList.add('open');
}
window.openCheckoutModal = openCheckoutModal;

function closeCheckoutModal() {
    stopWebcamProofStream();
    const modal = document.getElementById('checkout-modal');
    if (modal) modal.classList.remove('open');
    App.activeCheckoutTvId = null;
}
window.closeCheckoutModal = closeCheckoutModal;

function calculateCashChange() {
    const cashInput = document.getElementById('checkout-cash-received');
    const changeDisplay = document.getElementById('checkout-cash-change');
    if (!cashInput || !changeDisplay) return;

    const received = parseFloat(cashInput.value) || 0;
    let total = 0;
    if (App.state && App.activeCheckoutTvId) {
        const tv = App.state.tvs.find(t => t.id === App.activeCheckoutTvId);
        if (tv) total = tv.bill_etb || 0;
    }
    const change = Math.max(0, received - total);
    changeDisplay.textContent = `${change} ETB`;
}
window.calculateCashChange = calculateCashChange;

function updateModalQrView() {
    const qrSection = document.getElementById('qr-display-section');
    const cashSection = document.getElementById('cash-display-section');
    const qrImg = document.getElementById('modal-qr-image');
    const confirmBtn = document.getElementById('btn-modal-confirm-pay');
    const qrRecipient = document.getElementById('modal-qr-recipient');
    const qrPhone = document.getElementById('modal-qr-phone');
    const qrHint = document.getElementById('modal-qr-hint');
    const qrMethodPill = document.getElementById('modal-qr-method-pill');

    if (App.activePaymentMethod === 'TELEBIRR') {
        if (cashSection) cashSection.style.display = 'none';
        if (qrSection) qrSection.style.display = 'flex';
        if (qrImg) qrImg.src = '/api/payment_qr/telebirr?t=' + Date.now();
        if (qrMethodPill) qrMethodPill.textContent = '🟢 TELEBIRR DIGITAL';
        const tbAcc = (App.state && App.state.contact_phone) || '0911561432';
        const tbName = (App.state && App.state.lounge_name) || 'ABEL (Lounge Cashier)';
        if (qrRecipient) qrRecipient.innerHTML = `Recipient: <strong>${escapeHtml(tbName)}</strong>`;
        if (qrPhone) qrPhone.innerHTML = `Phone: <code>${escapeHtml(tbAcc)}</code>`;
        if (qrHint) qrHint.innerHTML = 'Customer scans with <strong>Telebirr App</strong>';
        if (confirmBtn) confirmBtn.innerHTML = `✓ Confirm Telebirr`;
    } else if (App.activePaymentMethod === 'CBE') {
        if (cashSection) cashSection.style.display = 'none';
        if (qrSection) qrSection.style.display = 'flex';
        if (qrImg) qrImg.src = '/api/payment_qr/cbe?t=' + Date.now();
        if (qrMethodPill) qrMethodPill.textContent = '🏦 CBE BANK TRANSFER';
        if (qrRecipient) qrRecipient.innerHTML = 'Account Name: <strong>Lounge Cashier</strong>';
        if (qrPhone) qrPhone.innerHTML = 'CBE Account: <code>1000293847123</code>';
        if (qrHint) qrHint.innerHTML = 'Customer transfers via <strong>CBE Birr / Mobile Banking</strong>';
        if (confirmBtn) confirmBtn.innerHTML = `✓ Confirm CBE`;
    } else {
        if (qrSection) qrSection.style.display = 'none';
        if (cashSection) cashSection.style.display = 'block';
        if (confirmBtn) confirmBtn.innerHTML = `Confirm Cash Payment`;
    }
}

// ============================================================
// PAYMENT PROOF CAMERA & PHOTO CAPTURE WORKFLOW
// ============================================================
let webcamProofStream = null;

window.handlePaymentProofSelected = function(event) {
    const file = event.target.files && event.target.files[0];
    if (!file) return;
    const reader = new FileReader();
    reader.onload = function(e) {
        setPaymentProof(e.target.result, file.name || 'Photo captured');
    };
    reader.readAsDataURL(file);
};

function setPaymentProof(dataUrl, label) {
    App.activePaymentProof = dataUrl;
    const card = document.getElementById('proof-preview-card');
    const img = document.getElementById('proof-preview-img');
    const badge = document.getElementById('proof-status-badge');
    const sizeText = document.getElementById('proof-filesize-text');
    const btns = document.getElementById('proof-input-buttons');

    if (img) img.src = dataUrl;
    if (card) card.style.display = 'flex';
    if (btns) btns.style.display = 'none';
    if (badge) {
        badge.textContent = '✔ Proof Attached';
        badge.className = 'proof-badge-verified';
    }
    if (sizeText) sizeText.textContent = label || 'Photo ready for verification';
    showToast('📸 Client payment proof photo attached!');
}

function clearPaymentProof() {
    App.activePaymentProof = null;
    const card = document.getElementById('proof-preview-card');
    const btns = document.getElementById('proof-input-buttons');
    const badge = document.getElementById('proof-status-badge');
    const camInp = document.getElementById('input-proof-camera');
    const fileInp = document.getElementById('input-proof-file');
    if (camInp) camInp.value = '';
    if (fileInp) fileInp.value = '';
    if (card) card.style.display = 'none';
    if (btns) btns.style.display = 'flex';
    if (badge) {
        badge.textContent = 'Photo or SMS Code';
        badge.className = 'proof-badge-pending';
    }
}
window.clearPaymentProof = clearPaymentProof;

function stopWebcamProofStream() {
    if (webcamProofStream) {
        webcamProofStream.getTracks().forEach(t => t.stop());
        webcamProofStream = null;
    }
    const view = document.getElementById('webcam-proof-view');
    if (view) view.style.display = 'none';
}
window.stopWebcamProofStream = stopWebcamProofStream;

window.toggleWebcamProofSnapshot = async function() {
    const view = document.getElementById('webcam-proof-view');
    const video = document.getElementById('webcam-proof-video');
    if (!view || !video) return;
    if (webcamProofStream) {
        stopWebcamProofStream();
        return;
    }
    try {
        view.style.display = 'block';
        webcamProofStream = await navigator.mediaDevices.getUserMedia({
            video: { facingMode: 'environment', width: { ideal: 1280 }, height: { ideal: 720 } }
        });
        video.srcObject = webcamProofStream;
    } catch (e) {
        showToast('Camera access denied or unavailable. Please use "Take Photo" button.', 'info');
        view.style.display = 'none';
    }
};

window.captureWebcamSnapshot = function() {
    const video = document.getElementById('webcam-proof-video');
    if (!video) return;
    const canvas = document.createElement('canvas');
    canvas.width = video.videoWidth || 640;
    canvas.height = video.videoHeight || 480;
    const ctx = canvas.getContext('2d');
    ctx.drawImage(video, 0, 0, canvas.width, canvas.height);
    const dataUrl = canvas.toDataURL('image/jpeg', 0.85);
    setPaymentProof(dataUrl, 'Camera snapshot');
    stopWebcamProofStream();
};

async function confirmCheckoutPayment() {
    if (!App.activeCheckoutTvId) return;

    let payload = {
        payment_method: App.activePaymentMethod,
        notes: (document.getElementById('checkout-notes-input')?.value || '').trim()
    };

    if (App.activePaymentMethod === 'CASH') {
        const received = parseFloat(document.getElementById('checkout-cash-received')?.value) || 0;
        let total = 0;
        if (App.state && App.activeCheckoutTvId) {
            const tv = App.state.tvs.find(t => t.id === App.activeCheckoutTvId);
            if (tv) total = tv.bill_etb || 0;
        }
        if (received < total) {
            showToast(`Amount received (${received} ETB) is less than total due (${total} ETB)`, 'error');
            return;
        }
        payload.amount_received = received;
        payload.change_given = Math.max(0, received - total);
    } else {
        // Digital Payment: Telebirr / CBE
        const ref = (document.getElementById('checkout-digital-ref')?.value || '').trim();
        const hasPhoto = Boolean(App.activePaymentProof);

        payload.payment_reference = ref || (hasPhoto ? 'PHOTO_VERIFIED' : 'DIGITAL_VERIFIED');
        if (hasPhoto) {
            payload.payment_proof_base64 = App.activePaymentProof;
        }
    }

    // Standalone Offline Interception (Solution 2)
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
        });
        const data = await res.json();
        if (!res.ok || !data.success) {
            showToast(data.message || data.error || 'Checkout failed', 'error');
            return;
        }
        closeCheckoutModal();
        showToast(`✅ Session closed. Paid via ${App.activePaymentMethod} (Verified)`);
        fetchState();
        fetchShiftStatus();
    } catch (e) {
        showToast('Payment processing error', 'error');
    }
}

// ============================================================
// PRD SECTION 16: TRANSACTION DETAILS MODAL
// ============================================================
async function openTxDetailModal(txId) {
    const modal = document.getElementById('tx-detail-modal');
    if (!modal) return;

    try {
        const res = await fetch(`/api/transaction/${txId}`);
        if (!res.ok) {
            showToast('Failed to load transaction details', 'error');
            return;
        }
        const data = await res.json();
        const tx = data.transaction;

        const set = (id, val) => {
            const el = document.getElementById(id);
            if (el) el.textContent = val;
        };

        set('txd-id', `TRANSACTION #${tx.formatted_id || `GW-${String(tx.id).padStart(6, '0')}`}`);
        set('txd-status-badge', tx.payment_status || 'PAID');
        set('txd-customer', tx.customer_name || 'Walk-in Gamer');
        set('txd-station', tx.station_name || `TV ${tx.tv_id}`);
        set('txd-clerk', tx.clerk_name || 'On-duty Clerk');

        set('txd-start', tx.session_start || '—');
        set('txd-end', tx.session_end || '—');
        set('txd-duration', tx.duration_formatted || '—');

        set('txd-games-calc', `${tx.games_count} × ${tx.price_per_game} ETB`);
        set('txd-games-total', `${tx.subtotal} ETB`);

        set('txd-subtotal', `${tx.subtotal} ETB`);
        set('txd-discount', `${tx.discount} ETB`);
        set('txd-total', `${tx.total} ETB`);

        set('txd-method', tx.payment_method);
        set('txd-received', `${tx.amount_received} ETB`);
        set('txd-change', `${tx.change_given} ETB`);
        set('txd-ref', tx.payment_reference || 'N/A');
        set('txd-status', tx.payment_status || 'PAID');

        set('txd-timestamp', tx.timestamp || '—');
        set('txd-notes', tx.notes || 'None');
        set('txd-adj', tx.adjustment_reason || 'None');

        const cashReceivedRow = document.getElementById('txd-cash-row-received');
        const cashChangeRow = document.getElementById('txd-cash-row-change');
        const digitalRefRow = document.getElementById('txd-digital-row-ref');

        const isCash = (tx.payment_method || '').toUpperCase().includes('CASH');
        if (cashReceivedRow) cashReceivedRow.style.display = isCash ? 'flex' : 'none';
        if (cashChangeRow) cashChangeRow.style.display = isCash ? 'flex' : 'none';
        if (digitalRefRow) digitalRefRow.style.display = isCash ? 'none' : 'flex';

        const proofCard = document.getElementById('txd-proof-card');
        const proofImg = document.getElementById('txd-proof-img');
        if (proofCard && proofImg) {
            if (tx.payment_proof) {
                proofImg.src = tx.payment_proof;
                proofCard.style.display = 'block';
            } else {
                proofCard.style.display = 'none';
            }
        }

        modal.classList.add('open');
    } catch (e) {
        showToast('Error loading transaction details', 'error');
    }
}
window.openTxDetailModal = openTxDetailModal;

function closeTxDetailModal() {
    const modal = document.getElementById('tx-detail-modal');
    if (modal) modal.classList.remove('open');
}
window.closeTxDetailModal = closeTxDetailModal;

// ============================================================
// FORGOT / RESET PASSWORD MODAL
// ============================================================
function openForgotPasswordModal() {
    const modal = document.getElementById('forgot-password-modal');
    if (modal) modal.classList.add('open');
}
window.openForgotPasswordModal = openForgotPasswordModal;

function closeForgotPasswordModal() {
    const modal = document.getElementById('forgot-password-modal');
    if (modal) modal.classList.remove('open');
}
window.closeForgotPasswordModal = closeForgotPasswordModal;

async function handleResetPassword(e) {
    if (e) e.preventDefault();
    const email = document.getElementById('reset-email')?.value.trim();
    const newPwd = document.getElementById('reset-new-password')?.value;
    const confirmPwd = document.getElementById('reset-confirm-password')?.value;

    if (newPwd !== confirmPwd) {
        showToast('Passwords do not match', 'error');
        return;
    }

    try {
        const res = await fetch('/api/auth/reset_password', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ email: email, new_password: newPwd, confirm_password: confirmPwd })
        });
        const data = await res.json();
        if (!res.ok) {
            showToast(data.error || 'Password reset failed', 'error');
            return;
        }
        closeForgotPasswordModal();
        showToast('Password reset successfully! Please sign in.');
    } catch (err) {
        showToast('Network error while resetting password', 'error');
    }
}
window.handleResetPassword = handleResetPassword;

// ============================================================
// BILLING VIEW (PRD Rule 13, 14, 16, 17, 18)
// ============================================================
function renderBilling(data) {
    const revEl = document.getElementById('ledger-daily-revenue');
    const gamesEl = document.getElementById('ledger-daily-games');
    const cashEl = document.getElementById('ledger-cash-revenue');
    const tbEl = document.getElementById('ledger-telebirr-revenue');
    const cbeEl = document.getElementById('ledger-cbe-revenue');

    if (revEl) revEl.textContent = data.daily_revenue || 0;
    if (gamesEl) gamesEl.textContent = data.daily_completed_games || 0;
    if (cashEl) cashEl.textContent = data.daily_cash || 0;
    if (tbEl) tbEl.textContent = data.daily_telebirr || 0;
    if (cbeEl) cbeEl.textContent = data.daily_cbe || 0;

    fetchAuditLogs();

    const txContainer = document.getElementById('ledger-transactions-body');
    if (!txContainer) return;

    if (!data.recent_transactions || data.recent_transactions.length === 0) {
        txContainer.innerHTML = '<div class="empty-state">No transactions yet today. Revenue = 0 ETB.</div>';
        return;
    }

    txContainer.innerHTML = data.recent_transactions.map(tx => {
        const method = (tx.payment_method || 'CASH').toUpperCase();
        let methodBadge = '💵 CASH';
        let methodClass = 'cash';
        if (method.includes('TELEBIRR')) {
            methodBadge = '🟢 TELEBIRR';
            methodClass = 'telebirr';
        } else if (method.includes('CBE')) {
            methodBadge = '🏦 CBE';
            methodClass = 'cbe';
        }

        const customerName = tx.customer_name || 'Walk-in Gamer';
        const tvName = tx.tv_name || `TV ${tx.tv_id}`;
        const timeStr = tx.checkout_time ? (tx.checkout_time.split(' ')[1] || tx.checkout_time) : '--:--';
        const formattedId = tx.formatted_id || `#GW-${String(tx.id).padStart(6, '0')}`;

        return `
            <div class="tx-card" onclick="openTxDetailModal(${tx.id})" style="cursor: pointer;" title="View Financial Breakdown">
                <div class="tx-top">
                    <span class="tx-id">${formattedId}</span>
                    <span class="tx-time">${timeStr}</span>
                </div>
                <div class="tx-mid">
                    <span class="tx-customer">${customerName}</span>
                    <span class="tx-amount">+${tx.total} ETB</span>
                </div>
                <div class="tx-bottom">
                    <span class="tx-tag ${methodClass}">${methodBadge}</span>
                    <span class="tx-tag settled">✓ Settled</span>
                    <span class="tx-station">${tvName}</span>
                    <span class="tx-games">${tx.completed_games} games</span>
                </div>
            </div>
        `;
    }).join('');
}

// ============================================================
// AI DIAGNOSTICS
// ============================================================
function initAiDiagnostics() {
    const askBtn = document.getElementById('btn-ask-ai');
    if (!askBtn) return;

    askBtn.addEventListener('click', async () => {
        const tvId = parseInt(document.getElementById('ai-tv-select').value);
        const query = document.getElementById('ai-query-input').value.trim();
        const output = document.getElementById('ai-report-output');

        output.textContent = 'Running diagnostic...';

        try {
            const res = await fetch('/api/ai/diagnose', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ tv_id: tvId, query: query })
            });
            const data = await res.json();
            output.textContent = data.success ? data.explanation : (data.message || 'Failed');
        } catch (e) {
            output.textContent = 'Connection error';
        }
    });
}

// ============================================================
// SIMULATION TOGGLE
// ============================================================
let isTogglingSim = false;
function initSimulationToggle() {
    const btn = document.getElementById('btn-toggle-simulation');
    if (!btn) return;
    btn.addEventListener('click', async () => {
        if (isTogglingSim) return;
        isTogglingSim = true;
        btn.disabled = true;
        btn.style.opacity = '0.6';
        try {
            const res = await fetch('/api/simulation/toggle', { method: 'POST' });
            const data = await res.json();
            if (res.ok && data.mode !== undefined) {
                showToast(`Mode: ${data.is_simulation ? 'SIMULATION' : 'LIVE CAMERA'}`);
                btn.textContent = data.is_simulation ? 'SIM' : 'LIVE';
                btn.className = data.is_simulation ? 'sim-toggle' : 'sim-toggle live';
                fetchState();
            } else {
                showToast(data.message || data.error || 'Failed to toggle simulation', 'error');
            }
        } catch (e) {
            showToast('Simulation toggle network error', 'error');
        } finally {
            btn.disabled = false;
            btn.style.opacity = '';
            isTogglingSim = false;
        }
    });
}

// ============================================================
// TOAST NOTIFICATIONS (top center for mobile)
// ============================================================
function showToast(message, type = 'success') {
    const container = document.getElementById('toast-container');
    if (!container) return;

    const toast = document.createElement('div');
    toast.className = `toast ${type}`;
    toast.innerHTML = `<span>${message}</span>`;
    container.appendChild(toast);

    setTimeout(() => {
        toast.style.opacity = '0';
        toast.style.transform = 'translateY(-10px)';
        setTimeout(() => toast.remove(), 300);
    }, 3000);
}

// ============================================================
// PRD ROLE SWITCHER (Owner vs Clerk vs Customer)
// ============================================================
window.switchRole = function(role) {
    App.currentRole = role;
    localStorage.setItem('gw_role', role);
    updateHeaderUserBadge(App.currentUser, role);


    // Shift banner display
    const shiftBanner = document.getElementById('shift-banner');
    if (shiftBanner) {
        shiftBanner.style.display = role === 'clerk' ? 'flex' : 'none';
    }

    // Role-tailored navigation visibility
    const setupTab = document.getElementById('dtab-setup');
    const bnavSetup = document.getElementById('bnav-setup');
    const aiTab = document.getElementById('dtab-ai');
    const bnavAi = document.getElementById('bnav-ai');

    if (role === 'customer') {
        if (setupTab) setupTab.style.display = 'none';
        if (bnavSetup) bnavSetup.style.display = 'none';
        if (aiTab) aiTab.style.display = 'none';
        if (bnavAi) bnavAi.style.display = 'none';
        switchView('customer');
    } else {
        if (setupTab) setupTab.style.display = 'flex';
        if (bnavSetup) bnavSetup.style.display = 'flex';
        if (aiTab) aiTab.style.display = 'flex';
        if (bnavAi) bnavAi.style.display = 'flex';
        if (App.currentView === 'customer' || App.currentView === 'auth' || App.currentView === 'role-select') {
            switchView('home');
        }
    }

    const toastMsg = role === 'owner' ? '👑 Owner Command Center Active' :
                     role === 'clerk' ? '👤 Clerk Workspace Active' :
                     '🎮 Player Lounge Active';
    showToast(toastMsg);
};

// ============================================================
// PRD RULE 2: AUDITED ADJUSTMENT MODAL
// ============================================================
function initAdjustmentModal() {
    const modal = document.getElementById('adjustment-modal');
    if (!modal) return;
    
    const closeBtn = document.getElementById('btn-close-adj-modal');
    const cancelBtn = document.getElementById('btn-cancel-adj');
    const submitBtn = document.getElementById('btn-submit-adj');
    
    if (closeBtn) closeBtn.addEventListener('click', closeAdjustmentModal);
    if (cancelBtn) cancelBtn.addEventListener('click', closeAdjustmentModal);
    if (submitBtn) submitBtn.addEventListener('click', submitAdjustment);
    
    modal.addEventListener('click', (e) => {
        if (e.target === modal) closeAdjustmentModal();
    });
}

function openAdjustmentModal(tvId, actionType) {
    App.pendingAdjustment = { tvId, actionType };
    const modal = document.getElementById('adjustment-modal');
    if (!modal) return;
    
    const titleEl = document.getElementById('adj-modal-title');
    const stEl = document.getElementById('adj-modal-station');
    const sumEl = document.getElementById('adj-action-summary');
    const reasonContainer = document.querySelector('#adjustment-modal .reason-options');
    
    stEl.textContent = `TV ${tvId}`;
    if (actionType === 'ADD_GAME') {
        titleEl.textContent = 'Manual Match Add';
        sumEl.textContent = `Recording +1 Verified Game (+25 ETB) on TV ${tvId}`;
        if (reasonContainer) {
            reasonContainer.innerHTML = `
                <label class="reason-option"><input type="radio" name="adj-reason-opt" value="Camera missed detection" checked><span>GameWatch missed detection</span></label>
                <label class="reason-option"><input type="radio" name="adj-reason-opt" value="Player obscured TV"><span>Player or object blocked screen</span></label>
                <label class="reason-option"><input type="radio" name="adj-reason-opt" value="Pre-registered walk-in match"><span>Walk-in manual addition</span></label>
                <label class="reason-option"><input type="radio" name="adj-reason-opt" value="Other"><span>Other verified reason</span></label>
            `;
        }
    } else if (actionType === 'DEDUCT_GAME') {
        titleEl.textContent = 'Deduct Match (-1 Game)';
        sumEl.textContent = `Deducting -1 completed match (-25 ETB) on TV ${tvId}`;
        if (reasonContainer) {
            reasonContainer.innerHTML = `
                <label class="reason-option"><input type="radio" name="adj-reason-opt" value="Console crash / system freeze" checked><span>Console crash / system freeze</span></label>
                <label class="reason-option"><input type="radio" name="adj-reason-opt" value="Customer dispute / wrong match counted"><span>Customer dispute / wrong match counted</span></label>
                <label class="reason-option"><input type="radio" name="adj-reason-opt" value="Testing / accidental operator increment"><span>Testing / accidental increment</span></label>
                <label class="reason-option"><input type="radio" name="adj-reason-opt" value="Power outage / match aborted"><span>Power outage / match aborted</span></label>
                <label class="reason-option"><input type="radio" name="adj-reason-opt" value="Other dispute"><span>Other valid dispute</span></label>
            `;
        }
    } else {
        titleEl.textContent = 'Reset Active Match';
        sumEl.textContent = `Resetting match state on TV ${tvId} to WAITING / IDLE`;
        if (reasonContainer) {
            reasonContainer.innerHTML = `
                <label class="reason-option"><input type="radio" name="adj-reason-opt" value="Match aborted by players" checked><span>Match aborted by players</span></label>
                <label class="reason-option"><input type="radio" name="adj-reason-opt" value="Console reset / power cycle"><span>Console reset / power cycle</span></label>
                <label class="reason-option"><input type="radio" name="adj-reason-opt" value="Testing / recalibration"><span>Testing / recalibration</span></label>
            `;
        }
    }
    
    const noteEl = document.getElementById('adj-note');
    if (noteEl) noteEl.value = '';
    
    modal.classList.add('open');
}
window.openAdjustmentModal = openAdjustmentModal;

function closeAdjustmentModal() {
    const modal = document.getElementById('adjustment-modal');
    if (modal) modal.classList.remove('open');
    App.pendingAdjustment = null;
}
window.closeAdjustmentModal = closeAdjustmentModal;

async function submitAdjustment() {
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

    try {
        const res = await fetch(endpoint, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                reason: reason,
                explanation: explanation,
                actor: clerkName
            })
        });
        const data = await res.json();
        if (!res.ok || !data.success) {
            showToast(data.message || 'Error recording adjustment', 'error');
            return;
        }
        closeAdjustmentModal();
        showToast(data.message || 'Adjustment audited and recorded');
        fetchState();
        fetchShiftStatus();
        fetchAuditLogs();
    } catch (e) {
        showToast('Error recording adjustment', 'error');
    }
}
window.submitAdjustment = submitAdjustment;

// ============================================================
// PRD SHIFT LIFECYCLE & RECONCILIATION (PRD Sections 9, 12, 26)
// ============================================================
function initEndShiftModal() {
    const modal = document.getElementById('end-shift-modal');
    if (!modal) return;
    
    const closeBtn = document.getElementById('btn-close-end-shift');
    const cancelBtn = document.getElementById('btn-cancel-end-shift');
    const submitBtn = document.getElementById('btn-submit-end-shift');
    
    if (closeBtn) closeBtn.addEventListener('click', closeEndShiftModal);
    if (cancelBtn) cancelBtn.addEventListener('click', closeEndShiftModal);
    if (submitBtn) submitBtn.addEventListener('click', submitEndShift);
    
    modal.addEventListener('click', (e) => {
        if (e.target === modal) closeEndShiftModal();
    });
}

async function fetchShiftStatus() {
    try {
        const res = await fetch('/api/shift/active');
        const data = await res.json();
        
        const banner = document.getElementById('shift-banner');
        const dot = document.getElementById('shift-indicator-dot');
        const title = document.getElementById('shift-title');
        const meta = document.getElementById('shift-meta');
        const btn = document.getElementById('btn-shift-action');
        
        if (data.active && data.shift) {
            App.activeShift = data.shift;
            if (banner) banner.className = 'shift-banner';
            if (dot) dot.className = 'shift-indicator';
            if (title) title.textContent = `${data.shift.clerk_name}'s Shift`;
            
            const startH = (data.shift.start_time || '').split(' ')[1] || '';
            if (meta) meta.textContent = `Started ${startH.slice(0, 5)} · ${data.shift.adjustments_count} Adjustments · ${data.shift.total_collected} ETB`;
            if (btn) {
                btn.textContent = 'End Shift';
                btn.className = 'btn-shift-action';
            }
        } else {
            App.activeShift = null;
            if (banner) banner.className = 'shift-banner inactive';
            if (dot) dot.className = 'shift-indicator';
            if (title) title.textContent = 'No Active Shift';
            if (meta) meta.textContent = 'Start shift to begin operator workspace';
            if (btn) {
                btn.textContent = 'Start Shift';
                btn.className = 'btn-shift-action start';
            }
        }
    } catch (e) {
        console.error('Shift fetch error:', e);
    }
}

async function handleShiftAction() {
    if (!App.activeShift) {
        // Start shift
        const clerkName = App.currentUser?.full_name || 'Clerk';
        try {
            const res = await fetch('/api/shift/start', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ clerk_name: clerkName })
            });
            const data = await res.json();
            showToast(`✅ Shift started for ${clerkName}`);
            fetchShiftStatus();
            fetchAuditLogs();
        } catch (e) {
            showToast('Error starting shift', 'error');
        }
    } else {
        // Open end shift modal with current numbers
        const modal = document.getElementById('end-shift-modal');
        if (!modal) return;
        
        document.getElementById('end-shift-clerk').textContent = `Clerk: ${App.activeShift.clerk_name}`;
        document.getElementById('shift-sum-games').textContent = App.activeShift.games_handled;
        document.getElementById('shift-sum-adj').textContent = App.activeShift.adjustments_count;
        document.getElementById('shift-sum-digital').textContent = `${App.activeShift.telebirr_collected + App.activeShift.cbe_collected} ETB`;
        document.getElementById('shift-sum-cash').textContent = `${App.activeShift.expected_cash} ETB`;
        
        document.getElementById('shift-actual-cash').value = App.activeShift.expected_cash;
        modal.classList.add('open');
    }
}
window.handleShiftAction = handleShiftAction;

function closeEndShiftModal() {
    const modal = document.getElementById('end-shift-modal');
    if (modal) modal.classList.remove('open');
}
window.closeEndShiftModal = closeEndShiftModal;

async function submitEndShift() {
    if (!App.activeShift) return;
    
    const actualCash = parseFloat(document.getElementById('shift-actual-cash').value) || 0;
    const notes = document.getElementById('shift-notes').value.trim();
    
    try {
        const res = await fetch('/api/shift/end', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                shift_id: App.activeShift.id,
                actual_cash: actualCash,
                notes: notes,
                clerk_name: App.activeShift.clerk_name
            })
        });
        const data = await res.json();
        closeEndShiftModal();
        showToast(data.message || 'Shift ended and reconciled');
        fetchShiftStatus();
        fetchAuditLogs();
        fetchState();
    } catch (e) {
        showToast('Error ending shift', 'error');
    }
}
window.submitEndShift = submitEndShift;

// ============================================================
// AUDIT LOGS DISPLAY (PRD Rule 2 & 10)
// ============================================================
async function fetchAuditLogs() {
    const auditContainer = document.getElementById('ledger-audit-body');
    if (!auditContainer) return;
    try {
        const res = await fetch('/api/audit_logs');
        const data = await res.json();
        if (!data.logs || data.logs.length === 0) {
            auditContainer.innerHTML = '<div class="empty-state">No operator adjustments recorded yet.</div>';
            return;
        }
        auditContainer.innerHTML = data.logs.map(log => {
            let tagClass = 'game-add';
            if (log.action.includes('RESET')) tagClass = '';
            if (log.action.includes('SHIFT')) tagClass = 'shift';
            return `
                <div class="audit-card">
                    <div class="audit-top">
                        <span class="audit-action-tag ${tagClass}">${log.action}</span>
                        <span class="audit-time">${log.timestamp}</span>
                    </div>
                    <div class="audit-mid">
                        <strong>${log.actor} ${log.tv_id ? `(TV ${log.tv_id})` : ''}</strong>
                        <span>${log.previous_value || '--'} → <strong>${log.new_value || '--'}</strong></span>
                    </div>
                    <div class="audit-reason">Reason: <em>${log.reason}</em></div>
                    ${log.explanation ? `<div class="audit-meta">Note: ${log.explanation}</div>` : ''}
                </div>
            `;
        }).join('');
    } catch (e) {
        console.error('Audit log fetch error:', e);
    }
}

// ============================================================
// REAL APPLICATION BOOT & SPLASH SCREEN (PRD Rule 2)
// ============================================================
let _splashSafetyTimer = null;

function initSplashScreen() {
    // Snappy auto-dismiss safety timer so user NEVER waits unnecessarily on reload
    if (_splashSafetyTimer) clearTimeout(_splashSafetyTimer);
    _splashSafetyTimer = setTimeout(() => {
        dismissSplashScreen();
    }, 600);
}

function dismissSplashScreen() {
    if (_splashSafetyTimer) {
        clearTimeout(_splashSafetyTimer);
        _splashSafetyTimer = null;
    }
    const sp = document.getElementById('splash-screen');
    if (sp && sp.style.display !== 'none') {
        sp.classList.add('splash-dismissed');
        setTimeout(() => {
            sp.style.display = 'none';
        }, 200);
    }
}

// Workspace global search across station cards
window.handleWorkspaceSearch = function(query) {
    const q = (query || '').toLowerCase().trim();
    const cards = document.querySelectorAll('.tv-card');
    cards.forEach(card => {
        if (!q) {
            card.style.display = '';
            return;
        }
        const text = card.textContent.toLowerCase();
        card.style.display = text.includes(q) ? '' : 'none';
    });
};


function showSplashError(msg) {
    const sp = document.getElementById('splash-screen');
    if (sp) {
        const sub = sp.querySelector('.splash-tagline') || sp.querySelector('.splash-subtitle');
        if (sub) {
            sub.innerHTML = `
                <span style="color: var(--rose-400); font-weight: 600;">Initialization: ${msg}</span>
                <br>
                <button class="btn btn-secondary btn-sm" onclick="location.reload()" style="margin-top: 12px;">Retry</button>
                <button class="btn btn-primary btn-sm" onclick="dismissSplashScreen()" style="margin-top: 12px; margin-left: 8px;">Enter App</button>
            `;
        }
    }
}

// ============================================================
// HEADER USER PILL & BADGE SYNCHRONIZATION
// ============================================================
function updateHeaderUserBadge(user, role) {
    const effectiveRole = (role || (user && user.role) || (App && App.currentRole) || '').toUpperCase();
    const roleLower = effectiveRole.toLowerCase();

    let displayName = 'Guest';
    let displayInitials = 'GW';
    let roleTitle = 'Logged Out';

    if (user) {
        displayName = user.full_name || (user.email ? user.email.split('@')[0] : 'Account');
        const parts = displayName.trim().split(/\s+/);
        if (parts.length >= 2) {
            displayInitials = (parts[0][0] + parts[1][0]).toUpperCase();
        } else if (parts.length === 1 && parts[0].length > 0) {
            displayInitials = parts[0].slice(0, 2).toUpperCase();
        }
    }

    if (effectiveRole === 'OWNER') roleTitle = 'Owner / Admin';
    else if (effectiveRole === 'CLERK') roleTitle = 'Clerk';
    else if (effectiveRole === 'CASHIER') roleTitle = 'Cashier';
    else if (effectiveRole === 'CUSTOMER') roleTitle = 'Player';
    else if (user) roleTitle = 'Active User';

    // 1. Update the visible Workspace Header Profile Badge
    const topAvatar = document.getElementById('top-avatar-initials');
    const topName = document.getElementById('top-operator-name');
    const topRole = document.getElementById('top-operator-role');

    if (topAvatar) topAvatar.textContent = displayInitials;
    if (topName) topName.textContent = displayName;
    if (topRole) topRole.textContent = roleTitle;

    // 2. Update the Dropdown Menu items
    const wpdAvatar = document.getElementById('wpd-avatar');
    const wpdName = document.getElementById('wpd-name');
    const wpdEmail = document.getElementById('wpd-email');
    const wpdRole = document.getElementById('wpd-role-tag');

    if (wpdAvatar) wpdAvatar.textContent = displayInitials;
    if (wpdName) wpdName.textContent = displayName;
    if (wpdEmail) wpdEmail.textContent = user ? (user.email || 'operator@gamewatch.et') : 'Not signed in';
    if (wpdRole) {
        wpdRole.textContent = roleTitle;
        wpdRole.className = `wpd-role-tag ${roleLower}`;
    }

    // Highlight active role in test role switcher chips
    document.querySelectorAll('.wpd-role-chip').forEach(btn => {
        const btnRole = (btn.getAttribute('data-role') || '').toUpperCase();
        btn.classList.toggle('active', btnRole === effectiveRole);
    });

    // 3. Update hidden compatibility elements for existing legacy logic
    const badgeEl = document.getElementById('header-user-badge');
    const nameEl = document.getElementById('header-user-name');
    const roleTagEl = document.getElementById('header-user-role-tag');
    const iconWrapEl = document.getElementById('header-user-icon-wrap');

    if (nameEl) nameEl.textContent = displayName;
    if (roleTagEl) {
        if (effectiveRole) {
            roleTagEl.textContent = roleTitle;
            roleTagEl.className = `user-pill-role-tag ${roleLower}`;
            roleTagEl.style.display = '';
        } else {
            roleTagEl.style.display = 'none';
        }
    }
    if (iconWrapEl) iconWrapEl.className = `user-avatar-badge ${roleLower}`;
    if (badgeEl) badgeEl.title = user ? `${displayName} · ${effectiveRole || 'Active'}` : 'Current Active Session';

    // 4. Update Settings Operator Profile Card
    const setOpName = document.getElementById('settings-operator-name');
    const setOpRole = document.getElementById('settings-operator-role');
    const setOpEmail = document.getElementById('settings-operator-email');
    if (setOpName) setOpName.textContent = displayName;
    if (setOpRole) {
        setOpRole.textContent = roleTitle;
        setOpRole.className = `user-pill-role-tag ${roleLower}`;
    }
    if (setOpEmail) {
        setOpEmail.textContent = (user && user.email) ? user.email : (effectiveRole ? `${roleLower}@gamewatch.et` : 'operator@gamewatch.et');
    }

    // 5. Update Mobile Nav Drawer
    const mndName = document.getElementById('mnd-lounge-name');
    const mndCode = document.getElementById('mnd-lounge-code');
    const mndRole = document.getElementById('mnd-role-badge');
    if (mndName && (user?.lounge_name || App.state?.lounge_name)) {
        mndName.textContent = user?.lounge_name || App.state?.lounge_name;
    }
    if (mndCode && (user?.lounge_code || App.state?.lounge_code)) {
        const code = user?.lounge_code || App.state?.lounge_code;
        const area = user?.lounge_area || App.state?.lounge_area || 'Bole';
        mndCode.textContent = `${code} · ${area}`;
    }
    if (mndRole && effectiveRole) {
        mndRole.textContent = effectiveRole;
    }
}

// User Profile Dropdown & Testing Persona Actions
window.toggleUserProfileDropdown = function(e) {
    if (e) {
        e.stopPropagation();
        e.preventDefault();
    }
    const dd = document.getElementById('workspace-profile-dropdown');
    if (dd) dd.classList.toggle('open');
};

window.closeUserProfileDropdown = function() {
    const dd = document.getElementById('workspace-profile-dropdown');
    if (dd) dd.classList.remove('open');
};

document.addEventListener('click', (e) => {
    const wrap = document.getElementById('workspace-profile-wrapper');
    if (wrap && !wrap.contains(e.target)) {
        window.closeUserProfileDropdown();
    }
});

window.openSettingsFromDropdown = function() {
    window.closeUserProfileDropdown();
    if (App.currentRole === 'OWNER') {
        switchView('settings');
    } else {
        showToast('ℹ Lounge configuration is reserved for the Owner account', 'info');
    }
};

window.switchTestRole = async function(role) {
    window.closeUserProfileDropdown();
    try {
        const res = await fetch('/api/auth/switch_role', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ role: role })
        });
        const data = await res.json();
        if (!res.ok) {
            showToast(data.error || 'Role switch failed', 'error');
            return;
        }
        App.currentUser = data.user;
        showToast(`Role switched to ${role} (${data.user.full_name})`);
        applyRole(role);
    } catch (err) {
        showToast('Connection error switching role', 'error');
    }
};

window.quickTestLogin = async function(role) {
    try {
        const res = await fetch('/api/auth/test_login', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ role: role })
        });
        const data = await res.json();
        if (!res.ok) {
            showToast(data.error || 'Test login failed', 'error');
            return;
        }
        App.currentUser = data.user;
        showToast(`Logged in as ${data.user.full_name} (${role})`);
        applyRole(role);
    } catch (err) {
        showToast('Connection error during test login', 'error');
    }
};

window.logout = window.handleLogout;

// ============================================================
// ROLE APPLICATION & PERMISSIONS (Hoisted Function Declaration)
// ============================================================
function applyRole(role) {
    role = (role || '').toUpperCase();
    App.currentRole = role;
    if (App.currentUser) {
        App.currentUser.role = role;
    }

    updateHeaderUserBadge(App.currentUser, role);

    const loungePill = document.getElementById('header-lounge-pill');
    const loungeCodeText = document.getElementById('header-lounge-code-text');
    const exploreBtn = document.getElementById('btn-header-explore');
    const effectiveLoungeCode = App.currentUser?.lounge_code || App.currentUser?.joined_lounge_code || (App.state && App.state.lounge_code) || 'GW-BOLE-101';

    const setLoungeCode = document.getElementById('settings-lounge-code');
    if (setLoungeCode) setLoungeCode.textContent = effectiveLoungeCode;

    if (loungePill) loungePill.style.display = 'none';
    if (loungeCodeText) loungeCodeText.textContent = effectiveLoungeCode;
    if (exploreBtn) exploreBtn.style.display = 'none';

    const setupTab = document.getElementById('dtab-setup');
    const bnavSetup = document.getElementById('bnav-setup');
    const billingTab = document.getElementById('dtab-billing');
    const bnavBilling = document.getElementById('bnav-billing');
    const aiTab = document.getElementById('dtab-ai');
    const bnavAi = document.getElementById('bnav-ai');
    const analyticsTab = document.getElementById('dtab-analytics');
    const bnavAnalytics = document.getElementById('bnav-analytics');
    const settingsTab = document.getElementById('dtab-settings');
    const bnavSettings = document.getElementById('bnav-settings');
    const homeTab = document.getElementById('dtab-home');
    const bnavHome = document.getElementById('bnav-home');
    const shiftBanner = document.getElementById('shift-banner');

    if (role === 'CUSTOMER') {
        // Customer sees ONLY consumer lounge
        if (homeTab) homeTab.style.display = 'none';
        if (bnavHome) bnavHome.style.display = 'none';
        if (setupTab) setupTab.style.display = 'none';
        if (bnavSetup) bnavSetup.style.display = 'none';
        if (billingTab) billingTab.style.display = 'none';
        if (bnavBilling) bnavBilling.style.display = 'none';
        if (aiTab) aiTab.style.display = 'none';
        if (bnavAi) bnavAi.style.display = 'none';
        if (analyticsTab) analyticsTab.style.display = 'none';
        if (bnavAnalytics) bnavAnalytics.style.display = 'none';
        if (settingsTab) settingsTab.style.display = 'none';
        if (bnavSettings) bnavSettings.style.display = 'none';
        if (shiftBanner) shiftBanner.style.display = 'none';

        switchView('customer');
    } else if (role === 'CLERK') {
        if (!App.currentUser?.joined_lounge_code) {
            openClerkCodeModal();
            return;
        }
        // Clerk sees Stations, Billing, Analytics, Customer, and Shift Banner
        if (homeTab) homeTab.style.display = 'flex';
        if (bnavHome) bnavHome.style.display = 'flex';
        if (billingTab) billingTab.style.display = 'flex';
        if (bnavBilling) bnavBilling.style.display = 'flex';
        if (setupTab) setupTab.style.display = 'none';
        if (bnavSetup) bnavSetup.style.display = 'none';
        if (aiTab) aiTab.style.display = 'none';
        if (bnavAi) bnavAi.style.display = 'none';
        if (analyticsTab) analyticsTab.style.display = 'flex';
        if (bnavAnalytics) bnavAnalytics.style.display = 'flex';
        if (settingsTab) settingsTab.style.display = 'none';
        if (bnavSettings) bnavSettings.style.display = 'none';
        if (shiftBanner) shiftBanner.style.display = 'flex';

        if (App.currentView === 'customer' || App.currentView === 'auth' || App.currentView === 'role-select' || App.currentView === 'setup' || App.currentView === 'settings') {
            switchView('home');
        }
    } else {
        // OWNER: Full command center
        if (homeTab) homeTab.style.display = 'flex';
        if (bnavHome) bnavHome.style.display = 'flex';
        if (setupTab) setupTab.style.display = 'flex';
        if (bnavSetup) bnavSetup.style.display = 'flex';
        if (billingTab) billingTab.style.display = 'flex';
        if (bnavBilling) bnavBilling.style.display = 'flex';
        if (aiTab) aiTab.style.display = 'flex';
        if (bnavAi) bnavAi.style.display = 'flex';
        if (analyticsTab) analyticsTab.style.display = 'flex';
        if (bnavAnalytics) bnavAnalytics.style.display = 'flex';
        if (settingsTab) settingsTab.style.display = 'flex';
        if (bnavSettings) bnavSettings.style.display = 'flex';
        if (shiftBanner) shiftBanner.style.display = 'none';

        if (App.currentView === 'auth' || App.currentView === 'role-select') {
            switchView('home');
        }
    }

    const ownerCreateEventBtn = document.getElementById('btn-owner-create-event');
    if (ownerCreateEventBtn) {
        ownerCreateEventBtn.style.display = (role === 'OWNER') ? 'inline-flex' : 'none';
    }
}
window.applyRole = applyRole;

// ============================================================
// REAL AUTHENTICATION & ROLE ENFORCEMENT (PRD Rule 3, 4, 5, 6, 21, 22)
// ============================================================
async function initAuthAndRole() {
    try {
        const res = await fetch('/api/auth/me');
        if (!res.ok) {
            // Not authenticated: Show Onboarding role selection FIRST (Professional Experience)
            App.currentUser = null;
            updateHeaderUserBadge(null, null);
            dismissSplashScreen();
            switchView('role-select');
            return;
        }

        const data = await res.json();
        App.currentUser = data.user;

        // Update header user info badge
        updateHeaderUserBadge(data.user, data.user?.role);

        if (!data.user || !data.user.role) {
            // Logged in but needs role selection
            dismissSplashScreen();
            switchView('role-select');
        } else if (data.user.role === 'CLERK' && !data.user.joined_lounge_code) {
            dismissSplashScreen();
            switchView('role-select');
            openClerkCodeModal();
        } else {
            dismissSplashScreen();
            applyRole(data.user.role);
        }
    } catch (err) {
        console.error('Auth initialization error:', err);
        dismissSplashScreen();
        switchView('role-select');
        showSplashError('Session check failed — please log in');
    }
}

// Onboarding Step 1 -> Step 2 Transitions
window.chooseOnboardingRole = function(role) {
    role = (role || 'OWNER').toUpperCase();
    App.selectedRole = role;

    const banner = document.getElementById('auth-role-pill-banner');
    const icon = document.getElementById('arhp-icon');
    const label = document.getElementById('arhp-role-label');

    if (banner) banner.style.display = 'flex';

    if (role === 'OWNER') {
        if (icon) icon.textContent = '👑';
        if (label) label.textContent = 'Lounge Owner';
    } else if (role === 'CLERK') {
        if (icon) icon.textContent = '👤';
        if (label) label.textContent = 'Station Clerk';
    } else {
        if (icon) icon.textContent = '🎮';
        if (label) label.textContent = 'Customer / Player';
    }

    // If user is already logged in, assign role directly
    if (App.currentUser) {
        if (role === 'CLERK' && !App.currentUser.joined_lounge_code) {
            openClerkCodeModal();
        } else {
            handleSelectRole(role);
        }
    } else {
        // Unauthenticated: Proceed smoothly to Step 2 (Sign In / Register card)
        switchView('auth');
    }
};

window.goToSignInWithoutRole = function() {
    App.selectedRole = null;
    const banner = document.getElementById('auth-role-pill-banner');
    if (banner) banner.style.display = 'none';
    switchView('auth');
};

window.toggleAuthMode = function(mode) {
    const tabLogin = document.getElementById('tab-auth-login');
    const tabSignup = document.getElementById('tab-auth-signup');
    const formLogin = document.getElementById('form-auth-login');
    const formSignup = document.getElementById('form-auth-signup');

    if (tabLogin && tabSignup && formLogin && formSignup) {
        tabLogin.classList.toggle('active', mode === 'login');
        tabSignup.classList.toggle('active', mode === 'signup');
        formLogin.style.display = mode === 'login' ? 'flex' : 'none';
        formSignup.style.display = mode === 'signup' ? 'flex' : 'none';
    }
};

window.togglePasswordVisibility = function(inputId) {
    const input = document.getElementById(inputId);
    if (!input) return;
    input.type = input.type === 'password' ? 'text' : 'password';
};

// ============================================================
// FORM VALIDATION & PASSWORD COMPLEXITY RULES
// ============================================================
window.clearFieldError = function(fieldId) {
    const input = document.getElementById(fieldId);
    if (input) {
        input.classList.remove('has-error');
        const wrap = input.closest('.input-wrap');
        if (wrap) wrap.classList.remove('has-error');
    }
    const errSpan = document.getElementById('err-' + fieldId);
    if (errSpan) {
        errSpan.textContent = '';
        errSpan.classList.remove('visible');
    }
};

window.setFieldError = function(fieldId, message) {
    const input = document.getElementById(fieldId);
    if (input) {
        input.classList.add('has-error');
        const wrap = input.closest('.input-wrap');
        if (wrap) wrap.classList.add('has-error');
        input.focus();
    }
    const errSpan = document.getElementById('err-' + fieldId);
    if (errSpan) {
        errSpan.textContent = message;
        errSpan.classList.add('visible');
    }
};

window.validateRealEmailInput = function(input) {
    clearFieldError(input.id);
    const val = input.value.trim();
    if (!val) return;
    const emailRegex = /^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z]{2,}$/;
    if (!emailRegex.test(val)) {
        setFieldError(input.id, '⚠ Please enter a valid email address (e.g. name@domain.com)');
    }
};

window.onPasswordInput = function(val) {
    clearFieldError('signup-password');
    const hasLen = val.length >= 6;
    const hasUpper = /[A-Z]/.test(val);
    const hasLower = /[a-z]/.test(val);
    const hasSpecial = /[!@#$%^&*()_+\-=\[\]{};':"\\|,.<>\/?~`]/.test(val);

    updatePwdChip('pwd-rule-len', hasLen, 'Min 6 chars');
    updatePwdChip('pwd-rule-upper', hasUpper, 'Capital Letter (A-Z)');
    updatePwdChip('pwd-rule-lower', hasLower, 'Small Letter (a-z)');
    updatePwdChip('pwd-rule-special', hasSpecial, 'Special (!@#$...)');
};

function updatePwdChip(chipId, isValid, label) {
    const chip = document.getElementById(chipId);
    if (!chip) return;
    if (isValid) {
        chip.classList.add('valid');
        chip.innerHTML = `<span class="chip-icon">✓</span> ${label}`;
    } else {
        chip.classList.remove('valid');
        chip.innerHTML = `<span class="chip-icon">○</span> ${label}`;
    }
}

// ============================================================
// GOOGLE OAUTH MODAL (Replacing Raw Prompt)
// ============================================================
window.handleGoogleAuth = function() {
    const modal = document.getElementById('google-oauth-modal');
    if (modal) modal.classList.add('open');
};

window.closeGoogleAuthModal = function() {
    const modal = document.getElementById('google-oauth-modal');
    if (modal) modal.classList.remove('open');
};

window.submitGoogleAuthWithEmail = async function(email, fullName) {
    closeGoogleAuthModal();
    try {
        const res = await fetch('/api/auth/google', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ 
                credential: email, 
                email: email, 
                name: fullName,
                role: App.selectedRole 
            })
        });
        const data = await res.json();
        if (!res.ok) {
            showToast(data.error || 'Google login failed', 'error');
            return;
        }

        App.currentUser = data.user;
        showToast(`Google authenticated as ${data.user.full_name}`);
        const effectiveRole = data.user.role || App.selectedRole;
        if (!effectiveRole) {
            switchView('role-select');
        } else if (effectiveRole === 'CLERK' && !data.user.joined_lounge_code) {
            openClerkCodeModal();
        } else if (!data.user.role && App.selectedRole) {
            handleSelectRole(App.selectedRole);
        } else {
            applyRole(data.user.role);
        }
    } catch (err) {
        showToast('Network error during Google authentication', 'error');
    }
};

window.handleCustomGoogleSubmit = function(e) {
    if (e) e.preventDefault();
    const email = document.getElementById('custom-google-email')?.value.trim();
    if (!email) return;
    const name = email.split('@')[0].replace(/[._-]/g, ' ');
    submitGoogleAuthWithEmail(email, name);
};

// ============================================================
// EMAIL SIGN IN & REGISTRATION HANDLERS
// ============================================================
window.handleEmailLogin = async function(e) {
    if (e) e.preventDefault();
    clearFieldError('input-login-email');
    clearFieldError('input-login-password');

    const email = document.getElementById('input-login-email')?.value.trim();
    const password = document.getElementById('input-login-password')?.value;

    let hasError = false;
    if (!email) {
        setFieldError('input-login-email', '⚠ Email address is required');
        hasError = true;
    }
    if (!password) {
        setFieldError('input-login-password', '⚠ Password is required');
        hasError = true;
    }
    if (hasError) return;

    const emailRegex = /^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z]{2,}$/;
    if (!emailRegex.test(email)) {
        setFieldError('input-login-email', '⚠ Please enter a valid email address');
        return;
    }

    try {
        const res = await fetch('/api/auth/login', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ email, password })
        });
        const data = await res.json();
        if (!res.ok) {
            showToast(data.error || 'Login failed', 'error');
            return;
        }

        App.currentUser = data.user;
        showToast(`Welcome back, ${data.user.full_name}`);

        const effectiveRole = data.user.role || App.selectedRole;
        if (!effectiveRole) {
            switchView('role-select');
        } else if (effectiveRole === 'CLERK' && !data.user.joined_lounge_code) {
            openClerkCodeModal();
        } else if (!data.user.role && App.selectedRole) {
            handleSelectRole(App.selectedRole);
        } else {
            applyRole(data.user.role);
        }
    } catch (err) {
        showToast('Connection error during login', 'error');
    }
};

window.handleRegistration = async function(e) {
    if (e) e.preventDefault();
    clearFieldError('signup-full-name');
    clearFieldError('signup-email');
    clearFieldError('signup-password');
    clearFieldError('signup-confirm-password');

    const fullName = document.getElementById('signup-full-name')?.value.trim();
    const email = document.getElementById('signup-email')?.value.trim();
    const phone = document.getElementById('signup-phone')?.value.trim();
    const password = document.getElementById('signup-password')?.value;
    const confirmPassword = document.getElementById('signup-confirm-password')?.value;

    let hasError = false;
    if (!fullName) {
        setFieldError('signup-full-name', '⚠ Full name is required');
        hasError = true;
    }
    if (!email) {
        setFieldError('signup-email', '⚠ Email address is required');
        hasError = true;
    }
    if (!password) {
        setFieldError('signup-password', '⚠ Password is required');
        hasError = true;
    }
    if (!confirmPassword) {
        setFieldError('signup-confirm-password', '⚠ Please confirm your password');
        hasError = true;
    }
    if (hasError) return;

    const emailRegex = /^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z]{2,}$/;
    if (!emailRegex.test(email)) {
        setFieldError('signup-email', '⚠ Please enter a real email address (e.g. name@domain.com)');
        return;
    }

    // Password complexity rules
    const hasLen = password.length >= 6;
    const hasUpper = /[A-Z]/.test(password);
    const hasLower = /[a-z]/.test(password);
    const hasSpecial = /[!@#$%^&*()_+\-=\[\]{};':"\\|,.<>\/?~`]/.test(password);

    if (!hasLen || !hasUpper || !hasLower || !hasSpecial) {
        setFieldError('signup-password', '⚠ Password must include uppercase, lowercase, special characters, and min 6 chars');
        return;
    }

    if (password !== confirmPassword) {
        setFieldError('signup-confirm-password', '⚠ Passwords do not match');
        return;
    }

    try {
        const res = await fetch('/api/auth/register', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                full_name: fullName,
                email: email,
                phone: phone,
                password: password,
                confirm_password: confirmPassword,
                role: App.selectedRole
            })
        });
        const data = await res.json();
        if (!res.ok) {
            showToast(data.error || 'Registration failed', 'error');
            return;
        }

        App.currentUser = data.user;
        showToast(`Account created! Welcome, ${data.user.full_name}`);
        const effectiveRole = data.user.role || App.selectedRole;
        if (!effectiveRole) {
            switchView('role-select');
        } else if (effectiveRole === 'CLERK' && !data.user.joined_lounge_code) {
            openClerkCodeModal();
        } else if (!data.user.role && App.selectedRole) {
            handleSelectRole(App.selectedRole);
        } else {
            applyRole(data.user.role);
        }
    } catch (err) {
        showToast('Connection error during registration', 'error');
    }
};

window.handleSelectRole = async function(role) {
    role = (role || '').toUpperCase();
    if (role === 'CLERK' && !App.currentUser?.joined_lounge_code) {
        openClerkCodeModal();
        return;
    }
    try {
        const res = await fetch('/api/auth/set_role', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ role: role })
        });
        const data = await res.json();
        if (!res.ok) {
            showToast(data.error || 'Role assignment failed', 'error');
            return;
        }

        if (App.currentUser) App.currentUser.role = role;
        showToast(`Workspace role set to ${role}`);
        applyRole(role);
    } catch (err) {
        showToast('Network error assigning role', 'error');
    }
};

window.handleLogout = async function() {
    try {
        await fetch('/api/auth/logout', { method: 'POST' });
    } catch (e) {}

    App.currentUser = null;
    App.selectedRole = null;
    updateHeaderUserBadge(null, null);
    showToast('Logged out of GameWatch');
    switchView('role-select'); // Shows Onboarding FIRST!
};

window.toggleLoungeSettingsEdit = function(showEdit) {
    const card = document.getElementById('lounge-profile-card');
    const form = document.getElementById('form-lounge-settings');
    if (card) card.style.display = showEdit ? 'none' : 'block';
    if (form) form.style.display = showEdit ? 'block' : 'none';
};

window.toggleCbeInputs = function(isNone) {
    const wrap = document.getElementById('cbe-inputs-wrap');
    const nameInp = document.getElementById('cfg-cbe-name');
    const numInp = document.getElementById('cfg-cbe-number');
    if (wrap) wrap.style.opacity = isNone ? '0.35' : '1';
    if (nameInp) nameInp.disabled = isNone;
    if (numInp) numInp.disabled = isNone;
};

window.previewTelebirrQr = function(e) {
    const file = e.target.files[0];
    if (!file) return;
    const reader = new FileReader();
    reader.onload = function(evt) {
        App.telebirrQrBase64 = evt.target.result;
        const box = document.getElementById('telebirr-qr-preview-box');
        const img = document.getElementById('telebirr-qr-preview-img');
        if (box && img) {
            img.src = evt.target.result;
            box.style.display = 'block';
        }
    };
    reader.readAsDataURL(file);
};

function loadSettingsView() {
    if (!App.state) return;
    const s = App.state;

    // Populate card
    const nameEl = document.getElementById('lpc-name-display');
    const areaEl = document.getElementById('lpc-area-display');
    const addrEl = document.getElementById('lpc-address-display');
    const codeEl = document.getElementById('lpc-code-display');
    const rateEl = document.getElementById('lpc-rate-display');
    const phoneEl = document.getElementById('lpc-phone-display');
    const emailEl = document.getElementById('lpc-email-display');
    const cbeEl = document.getElementById('lpc-cbe-display');

    const currentLoungeName = s.lounge_name || App.currentUser?.lounge_name || 'GameWatch Lounge';
    const currentLoungeCode = s.lounge_code || App.currentUser?.lounge_code || 'GW-BOLE-101';
    const currentLoungeArea = s.lounge_area || App.currentUser?.lounge_area || '4 Kilo';

    if (nameEl) nameEl.textContent = currentLoungeName;
    if (areaEl) areaEl.textContent = `📍 ${currentLoungeArea}`;
    if (addrEl) addrEl.textContent = s.contact_address || 'Addis Ababa, Ethiopia';
    if (codeEl) codeEl.textContent = currentLoungeCode;
    if (rateEl) rateEl.textContent = s.price_per_game || '25';
    if (phoneEl) phoneEl.textContent = s.contact_phone || '+251 900 000000';
    if (emailEl) emailEl.textContent = s.contact_email || 'support@gamewatch.et';
    if (cbeEl) cbeEl.textContent = (s.cbe_enabled !== false) ? '🏦 Active' : 'None (Disabled)';

    // Populate edit form
    const fName = document.getElementById('cfg-lounge-name');
    const fArea = document.getElementById('cfg-area');
    const fRate = document.getElementById('cfg-rate');
    const fAddr = document.getElementById('cfg-address');
    const fTbName = document.getElementById('cfg-telebirr-name');
    const fTbPhone = document.getElementById('cfg-telebirr-phone');
    const fCbeName = document.getElementById('cfg-cbe-name');
    const fCbeNum = document.getElementById('cfg-cbe-number');
    const fCbeNone = document.getElementById('cfg-cbe-none');
    const fPhone = document.getElementById('cfg-phone');
    const fEmail = document.getElementById('cfg-email');

    if (fName) fName.value = s.lounge_name || App.currentUser?.lounge_name || '';
    if (fArea) fArea.value = currentLoungeArea;
    if (fRate) fRate.value = s.price_per_game || 25;
    if (fAddr) fAddr.value = s.contact_address || '';
    if (fTbName) fTbName.value = s.telebirr_recipient || '';
    if (fTbPhone) fTbPhone.value = s.telebirr_phone || '';
    if (fCbeName) fCbeName.value = s.cbe_recipient || '';
    if (fCbeNum) fCbeNum.value = s.cbe_account || '';
    if (fCbeNone) {
        fCbeNone.checked = (s.cbe_enabled === false);
        toggleCbeInputs(fCbeNone.checked);
    }
    if (fPhone) fPhone.value = s.contact_phone || '';
    if (fEmail) fEmail.value = s.contact_email || '';
}

window.handleSaveSettings = async function(e) {
    if (e) e.preventDefault();
    const cbeNone = document.getElementById('cfg-cbe-none')?.checked;
    const payload = {
        lounge_name: document.getElementById('cfg-lounge-name')?.value.trim(),
        lounge_area: document.getElementById('cfg-area')?.value || '4 Kilo',
        price_per_game: parseFloat(document.getElementById('cfg-rate')?.value) || 25,
        contact_address: document.getElementById('cfg-address')?.value.trim(),
        telebirr_account_name: document.getElementById('cfg-telebirr-name')?.value.trim(),
        telebirr_phone: document.getElementById('cfg-telebirr-phone')?.value.trim(),
        cbe_enabled: !cbeNone,
        cbe_account_name: cbeNone ? '' : document.getElementById('cfg-cbe-name')?.value.trim(),
        cbe_account_number: cbeNone ? '' : document.getElementById('cfg-cbe-number')?.value.trim(),
        contact_phone: document.getElementById('cfg-phone')?.value.trim(),
        contact_email: document.getElementById('cfg-email')?.value.trim()
    };
    if (App.telebirrQrBase64) {
        payload.telebirr_qr_base64 = App.telebirrQrBase64;
    }

    try {
        const res = await fetch('/api/lounge_config', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });
        const data = await res.json();
        if (!res.ok) {
            showToast(data.error || 'Failed to save settings', 'error');
            return;
        }
        showToast('Lounge location & configuration saved successfully!');
        toggleLoungeSettingsEdit(false);
        if (data.lounge) {
            App.state.lounge_name = data.lounge.name;
            App.state.lounge_code = data.lounge.lounge_code;
            App.state.lounge_area = data.lounge.area;
            App.state.contact_address = data.lounge.address;
            App.state.contact_phone = data.lounge.phone;
            App.state.contact_email = data.lounge.email;
            App.state.price_per_game = data.lounge.rate_per_game;
            if (App.currentUser) {
                App.currentUser.lounge_name = data.lounge.name;
                App.currentUser.lounge_code = data.lounge.lounge_code;
                App.currentUser.lounge_area = data.lounge.area;
            }
        } else {
            App.state.lounge_name = payload.lounge_name;
            App.state.lounge_area = payload.lounge_area;
            App.state.contact_address = payload.contact_address;
            App.state.contact_phone = payload.contact_phone;
            App.state.contact_email = payload.contact_email;
            App.state.price_per_game = payload.price_per_game;
            if (App.currentUser) {
                App.currentUser.lounge_name = payload.lounge_name;
                App.currentUser.lounge_area = payload.lounge_area;
            }
        }
        loadSettingsView();
        const mndName = document.getElementById('mnd-lounge-name');
        const mndCode = document.getElementById('mnd-lounge-code');
        if (mndName) mndName.textContent = App.state.lounge_name;
        if (mndCode) mndCode.textContent = `${App.state.lounge_code || 'GW'} · ${App.state.lounge_area || 'Bole'}`;
        await fetchState();
    } catch (err) {
        showToast('Error saving settings', 'error');
    }
};

// ============================================================
// PROMOTIONS & ADS MANAGEMENT
// ============================================================
async function loadPromotions() {
    try {
        const res = await fetch('/api/promotions');
        if (!res.ok) return;
        const data = await res.json();
        const list = document.getElementById('settings-promotions-list');
        if (!list) return;
        if (!data.promotions || data.promotions.length === 0) {
            list.innerHTML = '<div style="color:var(--text-secondary); font-size:0.8rem; padding:12px;">No promotional campaigns added yet. Click "+ Create New Promotion" to publish your first ad.</div>';
            return;
        }
        list.innerHTML = data.promotions.map(p => `
            <div class="promo-mgmt-card ${p.is_active ? 'active-ad' : ''}">
                <div class="pmc-left">
                    <span class="pmc-badge">${escapeHtml(p.badge_text || 'PROMO')} ${p.is_active ? '🟢 LIVE BANNER' : '⚪ INACTIVE'}</span>
                    <div class="pmc-title">${escapeHtml(p.title)}</div>
                    <div class="pmc-desc">${escapeHtml(p.description)} (${escapeHtml(p.promo_rate || '')})</div>
                </div>
                <div class="pmc-actions">
                    <button type="button" class="btn btn-sm ${p.is_active ? 'btn-secondary' : 'btn-outline-cyan'}" onclick="togglePromoActive(${p.id}, ${p.is_active ? 0 : 1})">
                        ${p.is_active ? 'Deactivate' : 'Set Live'}
                    </button>
                    <button type="button" class="btn btn-sm btn-secondary" onclick="openCreatePromoModal(${p.id})">✏️</button>
                    <button type="button" class="btn btn-sm btn-secondary" onclick="deletePromo(${p.id})" style="color:#f87171;">🗑️</button>
                </div>
            </div>
        `).join('');
    } catch (e) {
        console.warn('Failed to load promotions:', e);
    }
}
window.loadPromotions = loadPromotions;

window.openCreatePromoModal = async function(promoId = null) {
    const modal = document.getElementById('modal-create-promo');
    if (!modal) return;
    const titleEl = document.getElementById('promo-modal-title');
    const idInp = document.getElementById('promo-edit-id');
    const titleInp = document.getElementById('promo-inp-title');
    const badgeInp = document.getElementById('promo-inp-badge');
    const descInp = document.getElementById('promo-inp-desc');
    const rateInp = document.getElementById('promo-inp-rate');
    const activeInp = document.getElementById('promo-inp-active');

    if (promoId) {
        titleEl.textContent = 'Edit Promotion / Ad';
        idInp.value = promoId;
        try {
            const res = await fetch('/api/promotions');
            const data = await res.json();
            const p = (data.promotions || []).find(x => x.id === promoId);
            if (p) {
                titleInp.value = p.title || '';
                badgeInp.value = p.badge_text || '🔥 HAPPY HOUR SPECIAL';
                descInp.value = p.description || '';
                rateInp.value = p.promo_rate || '';
                activeInp.checked = Boolean(p.is_active);
            }
        } catch (e) {}
    } else {
        titleEl.textContent = 'Create Promotion / Ad';
        idInp.value = '';
        titleInp.value = '';
        descInp.value = '';
        rateInp.value = 'Play for 15 ETB';
        activeInp.checked = true;
    }
    modal.classList.add('open');
};

window.closeCreatePromoModal = function() {
    const modal = document.getElementById('modal-create-promo');
    if (modal) modal.classList.remove('open');
};

window.handleSavePromo = async function(e) {
    if (e) e.preventDefault();
    const id = document.getElementById('promo-edit-id').value;
    const payload = {
        title: document.getElementById('promo-inp-title').value.trim(),
        badge_text: document.getElementById('promo-inp-badge').value.trim(),
        description: document.getElementById('promo-inp-desc').value.trim(),
        promo_rate: document.getElementById('promo-inp-rate').value.trim(),
        is_active: document.getElementById('promo-inp-active').checked ? 1 : 0
    };
    try {
        const url = id ? `/api/promotions/${id}` : '/api/promotions';
        const method = id ? 'PUT' : 'POST';
        const res = await fetch(url, {
            method: method,
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });
        const data = await res.json();
        if (!res.ok || !data.success) {
            showToast(data.message || 'Error saving promotion', 'error');
            return;
        }
        closeCreatePromoModal();
        showToast('Promotion published successfully!');
        loadPromotions();
        fetchState();
    } catch (err) {
        showToast('Error saving promotion', 'error');
    }
};

window.togglePromoActive = async function(promoId, isActive) {
    try {
        const res = await fetch(`/api/promotions/${promoId}/toggle`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ is_active: Boolean(isActive) })
        });
        const data = await res.json();
        if (data.success) {
            showToast(isActive ? 'Promotion set live on Gamer Lounge!' : 'Promotion deactivated');
            loadPromotions();
            fetchState();
        }
    } catch (e) {
        showToast('Error updating promotion', 'error');
    }
};

window.deletePromo = async function(promoId) {
    if (!confirm('Are you sure you want to delete this promotion?')) return;
    try {
        const res = await fetch(`/api/promotions/${promoId}`, { method: 'DELETE' });
        const data = await res.json();
        if (data.success) {
            showToast('Promotion deleted');
            loadPromotions();
            fetchState();
        }
    } catch (e) {
        showToast('Error deleting promotion', 'error');
    }
};

// ============================================================
// TOURNAMENTS & EVENTS MANAGEMENT
// ============================================================
window.openCreateEventModal = async function(eventId = null) {
    const modal = document.getElementById('modal-create-event');
    if (!modal) return;
    const titleEl = document.getElementById('event-modal-title');
    const idInp = document.getElementById('event-edit-id');
    const titleInp = document.getElementById('event-title');
    const gameInp = document.getElementById('event-game');
    const prizeInp = document.getElementById('event-prize');
    const dateInp = document.getElementById('event-date');
    const timeInp = document.getElementById('event-time');
    const feeInp = document.getElementById('event-fee');
    const maxInp = document.getElementById('event-max');
    const rulesInp = document.getElementById('event-rules');

    if (eventId) {
        titleEl.textContent = 'Edit Tournament';
        idInp.value = eventId;
        try {
            const res = await fetch('/api/events');
            const data = await res.json();
            const ev = (data.events || []).find(x => x.id === eventId);
            if (ev) {
                titleInp.value = ev.title || '';
                gameInp.value = ev.game || 'EA FC 25';
                prizeInp.value = ev.prize_pool || '5,000 ETB';
                dateInp.value = ev.event_date || '';
                timeInp.value = ev.event_time || '';
                feeInp.value = ev.entry_fee || 100;
                maxInp.value = ev.max_participants || 16;
                rulesInp.value = ev.rules || '';
            }
        } catch (e) {}
    } else {
        titleEl.textContent = 'Create Tournament / Event';
        idInp.value = '';
        titleInp.value = '';
        dateInp.value = 'Saturday, Oct 10';
        timeInp.value = '3:00 PM';
        feeInp.value = 100;
        maxInp.value = 16;
        prizeInp.value = '5,000 ETB';
        rulesInp.value = '';
    }
    modal.classList.add('open');
};

window.closeCreateEventModal = function() {
    const modal = document.getElementById('modal-create-event');
    if (modal) modal.classList.remove('open');
};

window.handleSaveEvent = async function(e) {
    if (e) e.preventDefault();
    const id = document.getElementById('event-edit-id').value;
    const payload = {
        title: document.getElementById('event-title').value.trim(),
        game: document.getElementById('event-game').value.trim(),
        prize_pool: document.getElementById('event-prize').value.trim(),
        event_date: document.getElementById('event-date').value.trim(),
        event_time: document.getElementById('event-time').value.trim(),
        entry_fee: parseFloat(document.getElementById('event-fee').value) || 0,
        max_participants: parseInt(document.getElementById('event-max').value) || 16,
        rules: document.getElementById('event-rules').value.trim()
    };
    try {
        const url = id ? `/api/events/${id}` : '/api/events';
        const method = id ? 'PUT' : 'POST';
        const res = await fetch(url, {
            method: method,
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });
        const data = await res.json();
        if (!res.ok || !data.success) {
            showToast(data.message || 'Error saving tournament', 'error');
            return;
        }
        closeCreateEventModal();
        showToast('Tournament published successfully!');
        fetchState();
    } catch (err) {
        showToast('Error saving tournament', 'error');
    }
};

window.deleteEvent = async function(eventId) {
    if (!confirm('Are you sure you want to delete this tournament?')) return;
    try {
        const res = await fetch(`/api/events/${eventId}`, { method: 'DELETE' });
        const data = await res.json();
        if (data.success) {
            showToast('Tournament deleted');
            fetchState();
        }
    } catch (e) {
        showToast('Error deleting tournament', 'error');
    }
};

// Participants Management Modal
window.openParticipantsModal = async function(eventId) {
    App.activeEventId = eventId;
    const modal = document.getElementById('modal-manage-participants');
    if (!modal) return;
    modal.classList.add('open');
    await reloadParticipantsList(eventId);
};

window.closeParticipantsModal = function() {
    const modal = document.getElementById('modal-manage-participants');
    if (modal) modal.classList.remove('open');
    App.activeEventId = null;
};

async function reloadParticipantsList(eventId) {
    try {
        const res = await fetch(`/api/events/${eventId}/participants`);
        if (!res.ok) return;
        const data = await res.json();
        const ev = data.event || {};
        const parts = data.participants || [];

        const titleEl = document.getElementById('mpart-event-title');
        const metaEl = document.getElementById('mpart-event-meta');
        if (titleEl) titleEl.textContent = `${ev.title} (${ev.game})`;
        if (metaEl) metaEl.textContent = `${ev.event_date} at ${ev.event_time} · Prize Pool: ${ev.prize_pool}`;

        const maxSlots = ev.max_participants || 16;
        const currCount = parts.length;
        const slotsLeft = Math.max(0, maxSlots - currCount);
        const collected = parts.filter(p => p.fee_paid).length * (ev.entry_fee || 0);

        const statCount = document.getElementById('mpart-stat-count');
        const statLeft = document.getElementById('mpart-stat-left');
        const statCol = document.getElementById('mpart-stat-collected');

        if (statCount) statCount.textContent = `${currCount} / ${maxSlots}`;
        if (statLeft) statLeft.textContent = `${slotsLeft} Slots Left`;
        if (statCol) statCol.textContent = `${collected} ETB`;

        const tbody = document.getElementById('mpart-table-body');
        if (!tbody) return;
        if (parts.length === 0) {
            tbody.innerHTML = '<tr><td colspan="6" style="text-align:center; color:var(--text-secondary); padding:20px;">No registered participants yet. Add walk-in gamer above!</td></tr>';
            return;
        }

        tbody.innerHTML = parts.map((p, idx) => `
            <tr>
                <td>${idx + 1}</td>
                <td><strong>${escapeHtml(p.customer_name)}</strong></td>
                <td>${escapeHtml(p.customer_phone || '--')}</td>
                <td>
                    <span class="lhh-pill ${p.fee_paid ? 'lhh-pill-green' : 'lhh-pill-code'}">
                        ${p.fee_paid ? `Paid (${p.fee_amount || ev.entry_fee} ETB)` : 'Unpaid'}
                    </span>
                </td>
                <td>
                    <span class="lhh-pill ${p.checked_in ? 'lhh-pill-green' : 'lhh-pill-code'}">
                        ${p.checked_in ? 'Checked In' : 'Pending'}
                    </span>
                </td>
                <td>
                    <div style="display:flex; gap:4px;">
                        ${!p.fee_paid ? `<button type="button" class="btn btn-sm btn-primary" onclick="markParticipantPaid(${p.id}, ${ev.entry_fee})">Paid</button>` : ''}
                        <button type="button" class="btn btn-sm ${p.checked_in ? 'btn-secondary' : 'btn-outline-cyan'}" onclick="toggleParticipantCheckIn(${p.id}, ${p.checked_in ? 0 : 1})">
                            ${p.checked_in ? 'Undo In' : 'Check In'}
                        </button>
                    </div>
                </td>
            </tr>
        `).join('');
    } catch (e) {
        console.warn('Error loading participants:', e);
    }
}

window.handleAddWalkInParticipant = async function(e) {
    if (e) e.preventDefault();
    if (!App.activeEventId) return;
    const nameInp = document.getElementById('mpart-walkin-name');
    const phoneInp = document.getElementById('mpart-walkin-phone');
    const pmInp = document.getElementById('mpart-walkin-pm');

    const name = nameInp ? nameInp.value.trim() : '';
    const phone = phoneInp ? phoneInp.value.trim() : '';
    const pm = pmInp ? pmInp.value : 'CASH';

    if (!name) return;

    try {
        const res = await fetch(`/api/events/${App.activeEventId}/register`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                customer_name: name,
                customer_phone: phone,
                payment_method: pm
            })
        });
        const data = await res.json();
        if (data.success) {
            nameInp.value = '';
            phoneInp.value = '';
            showToast(`${name} registered in tournament!`);
            await reloadParticipantsList(App.activeEventId);
            fetchState();
        } else {
            showToast(data.message || 'Registration failed', 'error');
        }
    } catch (err) {
        showToast('Error registering walk-in', 'error');
    }
};

window.markParticipantPaid = async function(regId, amount) {
    try {
        const res = await fetch(`/api/events/participants/${regId}/pay`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ amount: amount, payment_method: 'CASH' })
        });
        const data = await res.json();
        if (data.success) {
            showToast('Entry fee marked as paid!');
            if (App.activeEventId) reloadParticipantsList(App.activeEventId);
        }
    } catch (e) {
        showToast('Error recording payment', 'error');
    }
};

window.toggleParticipantCheckIn = async function(regId, checkedIn) {
    try {
        const res = await fetch(`/api/events/participants/${regId}/checkin`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ checked_in: Boolean(checkedIn) })
        });
        const data = await res.json();
        if (data.success) {
            showToast(checkedIn ? 'Gamer checked in!' : 'Check-in undone');
            if (App.activeEventId) reloadParticipantsList(App.activeEventId);
        }
    } catch (e) {
        showToast('Error updating check-in', 'error');
    }
};

// Customer Join Tournament Modal
window.openJoinEventModal = function(eventId) {
    const modal = document.getElementById('modal-join-event');
    if (!modal || !App.state) return;
    const ev = (App.state.events || []).find(x => x.id === eventId);
    if (!ev) return;

    document.getElementById('join-event-id').value = eventId;
    document.getElementById('join-event-title').textContent = ev.title;
    document.getElementById('join-event-sub').textContent = `${ev.game} · ${ev.event_date} at ${ev.event_time}`;
    document.getElementById('join-event-fee-display').textContent = `${ev.entry_fee} ETB`;

    const nameInp = document.getElementById('join-gamer-name');
    const phoneInp = document.getElementById('join-gamer-phone');
    if (nameInp) nameInp.value = App.currentUser?.full_name || '';
    if (phoneInp) phoneInp.value = App.currentUser?.phone || '';

    modal.classList.add('open');
};

window.closeJoinEventModal = function() {
    const modal = document.getElementById('modal-join-event');
    if (modal) modal.classList.remove('open');
};

window.handleSubmitJoinEvent = async function(e) {
    if (e) e.preventDefault();
    const eventId = document.getElementById('join-event-id').value;
    const name = document.getElementById('join-gamer-name').value.trim();
    const phone = document.getElementById('join-gamer-phone').value.trim();
    const pm = document.getElementById('join-gamer-pm').value;

    if (!name || !phone) return;

    try {
        const res = await fetch(`/api/events/${eventId}/register`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                customer_name: name,
                customer_phone: phone,
                payment_method: pm
            })
        });
        const data = await res.json();
        if (!res.ok || !data.success) {
            showToast(data.message || 'Registration failed', 'error');
            return;
        }
        closeJoinEventModal();
        showToast('🎉 You are officially registered in the tournament! Pay at counter or Telebirr.');
        fetchState();
    } catch (err) {
        showToast('Error registering for event', 'error');
    }
};

// ============================================================
// BUSINESS ANALYTICS & WEEKLY INTELLIGENCE
// ============================================================
async function loadBusinessAnalytics() {
    try {
        const res = await fetch('/api/analytics/business');
        if (!res.ok) return;
        const data = await res.json();
        if (!data.success || !data.analytics) return;
        const a = data.analytics;

        const revEl = document.getElementById('ana-week-revenue');
        if (revEl) revEl.textContent = Number(a.weekly_revenue || 0).toLocaleString();

        const pill = document.getElementById('ana-growth-pill');
        if (pill) {
            const up = a.growth_percentage >= 0;
            pill.className = `trend-pill ${up ? 'trend-up' : 'trend-down'}`;
            pill.textContent = `${up ? '📈 +' : '📉 '}${a.growth_percentage}%`;
        }

        const gamesEl = document.getElementById('ana-week-games');
        if (gamesEl) gamesEl.textContent = a.total_games || 0;

        const txsEl = document.getElementById('ana-week-txs');
        if (txsEl) txsEl.textContent = `${a.total_transactions || 0} checkout sessions`;

        const peakEl = document.getElementById('ana-peak-hours');
        if (peakEl) peakEl.textContent = a.peak_hours || '4:00 PM – 8:00 PM';

        const capEl = document.getElementById('ana-peak-capacity');
        if (capEl) capEl.textContent = a.peak_capacity || '84% peak capacity';

        const topStEl = document.getElementById('ana-top-station');
        if (topStEl && a.station_performance && a.station_performance[0]) {
            topStEl.textContent = a.station_performance[0].name;
        }

        // Render Bar Chart
        const chartEl = document.getElementById('weekly-bar-chart');
        if (chartEl && Array.isArray(a.days)) {
            const maxRev = Math.max(...a.days.map(d => d.revenue), 100);
            chartEl.innerHTML = a.days.map(d => {
                const heightPct = Math.max(8, Math.round((d.revenue / maxRev) * 100));
                return `
                    <div class="weekly-bar-col">
                        <div class="weekly-bar-track">
                            <div class="weekly-bar-fill" style="height:${heightPct}%;">
                                ${d.revenue > 0 ? `<span class="weekly-bar-amt">${Math.round(d.revenue)}</span>` : ''}
                            </div>
                        </div>
                        <span class="weekly-bar-label">${d.day}</span>
                    </div>
                `;
            }).join('');
        }

        // Render Payment Channels
        const payEl = document.getElementById('ana-payment-channels');
        if (payEl && Array.isArray(a.payment_breakdown)) {
            payEl.innerHTML = a.payment_breakdown.map(p => {
                const m = p.method.toUpperCase();
                const cls = m.includes('TELEBIRR') ? 'pci-fill-telebirr' : (m.includes('CBE') ? 'pci-fill-cbe' : 'pci-fill-cash');
                return `
                    <div class="pay-chan-item">
                        <div class="pci-head">
                            <span class="pci-name">${p.method} (${p.count} txs)</span>
                            <span class="pci-amt">${Number(p.amount).toLocaleString()} ETB (${p.percentage}%)</span>
                        </div>
                        <div class="pci-track">
                            <div class="pci-fill ${cls}" style="width:${Math.max(5, p.percentage)}%;"></div>
                        </div>
                    </div>
                `;
            }).join('');
        }

        // Render Station table
        const tbody = document.getElementById('ana-stations-tbody');
        if (tbody && Array.isArray(a.station_performance)) {
            tbody.innerHTML = a.station_performance.map(s => `
                <tr>
                    <td><strong>${s.name}</strong></td>
                    <td>${s.games} matches</td>
                    <td style="color:var(--cyan-accent); font-weight:700;">${Number(s.revenue).toLocaleString()} ETB</td>
                    <td>${s.sessions}</td>
                </tr>
            `).join('');
        }

        // Render AI Advisor
        const aiList = document.getElementById('ana-ai-advisor-list');
        if (aiList && Array.isArray(a.ai_insights)) {
            aiList.innerHTML = a.ai_insights.map(item => `
                <div class="ai-advisor-item">
                    <span class="ai-adv-icon">${item.icon || '✨'}</span>
                    <div>
                        <div class="ai-adv-title">${escapeHtml(item.title)}</div>
                        <div class="ai-adv-rec">${escapeHtml(item.recommendation)}</div>
                    </div>
                </div>
            `).join('');
        }
    } catch (e) {
        console.warn('Analytics fetch error:', e);
    }
}
window.loadBusinessAnalytics = loadBusinessAnalytics;

// ============================================================
// CUSTOMER LOUNGE & WAITING LIST
// ============================================================
function initWaitingListModal() {
    const modal = document.getElementById('waiting-list-modal');
    if (!modal) return;
    modal.addEventListener('click', (e) => {
        if (e.target === modal) closeWaitingListModal();
    });
}

function openWaitingListModal(prefStation = '') {
    const modal = document.getElementById('waiting-list-modal');
    if (prefStation) {
        const select = document.getElementById('queue-station-select');
        if (select) select.value = prefStation;
    }
    if (modal) modal.classList.add('open');
}
window.openWaitingListModal = openWaitingListModal;

function closeWaitingListModal() {
    const modal = document.getElementById('waiting-list-modal');
    if (modal) modal.classList.remove('open');
}
window.closeWaitingListModal = closeWaitingListModal;

async function submitWaitingList(e) {
    if (e) e.preventDefault();
    const name = document.getElementById('queue-name-input').value.trim();
    const phone = document.getElementById('queue-phone-input').value.trim();
    const station = document.getElementById('queue-station-select').value;

    try {
        const res = await fetch('/api/waiting_list', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ name, phone, station })
        });
        const data = await res.json();
        closeWaitingListModal();
        showToast(`✅ ${name} joined the waiting queue!`);
        fetchWaitingList();
    } catch (err) {
        showToast('Error joining queue', 'error');
    }
}
window.submitWaitingList = submitWaitingList;

async function fetchWaitingList() {
    const queueBody = document.getElementById('customer-queue-body');
    const countDisplay = document.getElementById('queue-count-display');
    if (!queueBody) return;

    try {
        const res = await fetch('/api/waiting_list');
        const data = await res.json();
        const list = data.waiting_list || [];

        if (countDisplay) {
            countDisplay.textContent = `${list.length} player${list.length === 1 ? '' : 's'} in line`;
        }

        if (list.length === 0) {
            queueBody.innerHTML = '<div class="empty-state">No players currently waiting. Stations available right now!</div>';
            return;
        }

        queueBody.innerHTML = list.map((item, idx) => {
            const timeStr = (item.joined_time || '').split(' ')[1] || '';
            return `
                <div class="queue-item">
                    <div class="queue-item-left">
                        <span class="queue-pos">#${idx + 1}</span>
                        <div>
                            <span class="queue-player-name">${item.customer_name}</span>
                            <div class="queue-pref">${item.preferred_station} · Joined ${timeStr.slice(0, 5)}</div>
                        </div>
                    </div>
                    <span class="badge-games">Next Up</span>
                </div>
            `;
        }).join('');
    } catch (e) {
        console.error('Waiting list error:', e);
    }
}

function renderCustomerLounge() {
    if (!App.state) return;

    // 1. Update Lounge Header Hero Info
    const heroName = document.getElementById('cust-hero-lounge-name');
    const heroArea = document.getElementById('cust-hero-lounge-area');
    const heroCode = document.getElementById('cust-hero-lounge-code');
    const lName = App.state.lounge_name || 'Abyman GameZone';
    const lArea = App.state.lounge_area || '4 Kilo';
    const lCode = App.state.lounge_code || 'GW-OWNER-050';

    if (heroName) heroName.textContent = lName;
    if (heroArea) heroArea.textContent = `📍 ${lArea}, Addis Ababa`;
    if (heroCode) heroCode.textContent = lCode;

    // Footer brand & contact cards
    const footerTitle = document.getElementById('cust-lounge-title');
    const footerAddr = document.getElementById('cust-footer-address');
    const footerPhone = document.getElementById('cust-footer-phone');
    const footerEmail = document.getElementById('cust-footer-email');
    if (footerTitle) footerTitle.textContent = lName;
    if (footerAddr) footerAddr.textContent = App.state.contact_address || `${lArea}, Addis Ababa`;
    if (footerPhone) footerPhone.textContent = App.state.contact_phone || '0921615614';
    if (footerEmail) footerEmail.textContent = App.state.contact_email || 'contact@gamewatch.et';

    // 2. Dynamic Promotional Banner
    const promoBanner = document.getElementById('customer-promo-banner');
    const promo = App.state.active_promotion;
    if (promoBanner) {
        if (promo) {
            promoBanner.style.display = 'flex';
            const bTag = document.getElementById('promo-badge-text');
            const bTitle = document.getElementById('promo-title-text');
            const bSub = document.getElementById('promo-sub-text');
            const bRate = document.getElementById('promo-regular-rate');
            if (bTag) bTag.textContent = promo.badge_text || '🔥 SPECIAL OFFER';
            if (bTitle) bTitle.textContent = promo.title;
            if (bSub) bSub.innerHTML = `${escapeHtml(promo.description)} (Rate: <strong>${promo.promo_rate || App.state.price_per_game} ETB</strong>)`;
            if (bRate) bRate.textContent = App.state.price_per_game || 25;
        } else {
            promoBanner.style.display = 'flex';
            const bTag = document.getElementById('promo-badge-text');
            const bTitle = document.getElementById('promo-title-text');
            const bSub = document.getElementById('promo-sub-text');
            if (bTag) bTag.textContent = '🔥 LIVE GAMING ARENA';
            if (bTitle) bTitle.textContent = `Play on PlayStation 5 for ${App.state.price_per_game || 25} ETB / Match`;
            if (bSub) bSub.textContent = `Automated referee, low latency screens and live leaderboards`;
        }
    }

    // 3. Render Stations Grid
    const list = document.getElementById('customer-tvs-list');
    if (list && App.state.tvs) {
        list.innerHTML = App.state.tvs.map(tv => {
            const isPlaying = tv.state === 'MATCH_IN_PROGRESS';
            const statusBadge = isPlaying ? 
                `<span class="cust-tv-badge busy">🔴 IN MATCH</span>` :
                `<span class="cust-tv-badge available">🟢 AVAILABLE NOW</span>`;
            
            const subtext = isPlaying ? 
                `Playing now · Est. 3 mins remaining` :
                `Ready to play! Open station`;

            const matchBug = isPlaying ? 
                `<div class="cust-tv-matchbug">[ ⏱ ${tv.clock} | ${tv.score} ]</div>` :
                `<div class="cust-tv-matchbug text-emerald">[ CONTROLLERS READY ]</div>`;

            const actionBtn = isPlaying ? 
                `<button class="btn btn-sm btn-secondary" onclick="openWaitingListModal('${tv.name}')">⏳ Join Waiting List</button>` :
                `<button class="btn btn-sm btn-primary" onclick="showToast('Ask clerk at counter to start on ${tv.name}')">🎮 Play on TV ${tv.id}</button>`;

            return `
                <div class="cust-tv-card">
                    <div class="cust-tv-header">
                        <span class="cust-tv-name">${tv.name}</span>
                        ${statusBadge}
                    </div>
                    ${matchBug}
                    <div class="cust-tv-wait">${subtext}</div>
                    <div style="margin-top: 4px;">
                        ${actionBtn}
                    </div>
                </div>
            `;
        }).join('');
    }

    // 4. Render Tournaments & Events List
    const evList = document.getElementById('customer-events-list');
    if (evList) {
        const events = App.state.events || [];
        if (events.length === 0) {
            evList.innerHTML = `
                <div class="empty-state" style="grid-column: 1 / -1; padding: 24px; text-align: center;">
                    No tournaments scheduled currently. Stay tuned for upcoming weekend cups!
                </div>
            `;
        } else {
            const isStaff = (App.currentRole === 'OWNER' || App.currentRole === 'CLERK');
            evList.innerHTML = events.map(ev => {
                const max = ev.max_participants || 16;
                const curr = ev.current_participants || 0;
                const slotsLeft = Math.max(0, max - curr);
                const pct = Math.min(100, Math.round((curr / max) * 100));
                const isFull = slotsLeft === 0;

                const actionArea = isStaff ? `
                    <div class="ev-card-actions">
                        <button type="button" class="btn btn-sm btn-primary" onclick="openParticipantsModal(${ev.id})">
                            <span>👥 Manage Attendees (${curr}/${max})</span>
                        </button>
                        ${App.currentRole === 'OWNER' ? `
                            <button type="button" class="btn btn-sm btn-secondary" onclick="openCreateEventModal(${ev.id})" title="Edit Tournament">✏️</button>
                            <button type="button" class="btn btn-sm btn-outline-danger" onclick="deleteEvent(${ev.id})" title="Delete Tournament">🗑</button>
                        ` : ''}
                    </div>
                ` : `
                    <div class="ev-card-actions">
                        ${isFull ? `
                            <button type="button" class="btn btn-sm btn-secondary" disabled style="opacity:0.6;">
                                <span>🔒 Tournament Full</span>
                            </button>
                        ` : `
                            <button type="button" class="btn btn-sm btn-primary" onclick="openJoinEventModal(${ev.id})">
                                <span>🏆 Register (${ev.entry_fee} ETB)</span>
                            </button>
                        `}
                    </div>
                `;

                return `
                    <div class="event-card">
                        <div class="ev-card-head">
                            <span class="ev-game-tag">🎮 ${escapeHtml(ev.game || 'EA FC 25')}</span>
                            <span class="ev-prize-tag">💰 ${escapeHtml(ev.prize_pool || 'Prize Pool')}</span>
                        </div>
                        <h4 class="ev-title">${escapeHtml(ev.title)}</h4>
                        <div class="ev-date-time">
                            <span>📅 ${escapeHtml(ev.event_date || 'Upcoming')}</span>
                            <span>⏰ ${escapeHtml(ev.event_time || 'TBA')}</span>
                        </div>
                        <div class="ev-fee-row">
                            <span class="ev-fee-lbl">Entry Fee:</span>
                            <span class="ev-fee-val">${ev.entry_fee} ETB</span>
                        </div>
                        <div class="ev-progress-section">
                            <div class="ev-progress-bar-wrap">
                                <div class="ev-progress-bar" style="width:${pct}%;"></div>
                            </div>
                            <div class="ev-slots-meta">
                                <span>${curr} / ${max} Registered</span>
                                <span class="${isFull ? 'text-amber' : 'text-cyan'}">${isFull ? 'Registration Full' : `${slotsLeft} Slots Left`}</span>
                            </div>
                        </div>
                        ${ev.rules ? `<div class="ev-rules-preview">${escapeHtml(ev.rules)}</div>` : ''}
                        ${actionArea}
                    </div>
                `;
            }).join('');
        }
    }
}
window.renderCustomerLounge = renderCustomerLounge;

// ============================================================
// UNIVERSAL KEYBOARD SHORTCUTS & MODAL BACKDROPS
// ============================================================
function initKeyboardShortcuts() {
    document.addEventListener('keydown', (e) => {
        if (e.key === 'Escape') {
            closeCheckoutModal();
            closeAdjustmentModal();
            closeEndShiftModal();
            closeWaitingListModal();
            closeTxDetailModal();
            closeForgotPasswordModal();
            closeAddCameraModal();
        }
    });

    document.querySelectorAll('.modal-bg').forEach(bg => {
        bg.addEventListener('click', (e) => {
            if (e.target === bg) {
                bg.classList.remove('open');
            }
        });
    });
}

// ============================================================
// CAMERA & VIDEO SOURCE CONNECTORS HUB (Hardening Step)
// ============================================================
async function fetchCameraSources() {
    try {
        const res = await fetch('/api/camera_sources');
        if (!res.ok) return;
        const data = await res.json();
        if (data.success && Array.isArray(data.sources)) {
            App.cameraSources = data.sources;
            renderCameraSources(data.sources);
        }
    } catch (err) {
        console.warn('Failed to load camera sources:', err);
    }
}

function renderCameraSources(sources) {
    const grid = document.getElementById('camera-sources-grid');
    const badge = document.getElementById('camera-count-badge');
    if (badge) {
        const count = sources ? sources.length : 0;
        badge.textContent = `${count} ${count === 1 ? 'Feed' : 'Active Feeds'}`;
    }
    if (!grid) return;

    if (!sources || sources.length === 0) {
        grid.innerHTML = `
            <div class="empty-state" style="grid-column: 1 / -1; padding: 24px; text-align: center;">
                No camera connectors configured yet. Click <strong>+ Connect Camera / Phone</strong> to add a feed.
            </div>
        `;
        return;
    }

    grid.innerHTML = sources.map(s => {
        const typeIcon = s.source_type === 'PHONE' ? '📱' :
                         s.source_type === 'USB' ? '📹' :
                         s.source_type === 'RTSP' ? '🌐' : '💻';

        const stationLabel = (s.tv_id && s.tv_id > 0) ? `Assigned to TV ${s.tv_id}` : 'All Stations (Room Overview)';

        const statusClass = (s.status === 'CONNECTED') ? 'connected' :
                            (s.status === 'OFFLINE') ? 'offline' : 'ready';

        const statusDot = (s.status === 'CONNECTED') ? '<span class="live-dot-green"></span>' : '●';

        return `
            <div class="connector-card" id="cam-card-${s.id}">
                <div class="connector-card-top">
                    <div class="connector-card-info">
                        <div class="connector-icon-badge">${typeIcon}</div>
                        <div>
                            <div class="connector-name">${escapeHtml(s.name)}</div>
                            <div class="connector-station-tag">${stationLabel}</div>
                        </div>
                    </div>
                    <span class="connector-status-badge ${statusClass}">
                        ${statusDot} ${s.status}
                    </span>
                </div>

                <div class="connector-address-box">
                    <span>📡</span>
                    <span>${escapeHtml(s.address)}</span>
                </div>

                <div class="connector-specs-row">
                    <span>Resolution: <strong>${s.resolution || '1920x1080'}</strong></span>
                    <span>FPS: <strong>${s.fps || 30}</strong></span>
                </div>

                <div class="connector-actions-row">
                    <button type="button" class="btn-test-cam" onclick="testCameraSource(${s.id}, this)">
                        <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"></polygon></svg>
                        <span>Test Feed</span>
                    </button>
                    <button type="button" class="btn-del-cam" onclick="deleteCameraSource(${s.id})" title="Remove Connector">
                        <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2"><polyline points="3 6 5 6 21 6"></polyline><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"></path></svg>
                    </button>
                </div>
            </div>
        `;
    }).join('');
}

function openAddCameraModal() {
    const modal = document.getElementById('add-camera-modal');
    if (modal) {
        modal.classList.add('open');
        quickFillCamPreset('DROIDCAM');
    }
}

function closeAddCameraModal() {
    const modal = document.getElementById('add-camera-modal');
    if (modal) modal.classList.remove('open');
}

function quickFillCamPreset(preset) {
    document.querySelectorAll('.preset-chip').forEach(c => c.classList.remove('active'));
    const btn = Array.from(document.querySelectorAll('.preset-chip')).find(b => b.textContent.includes(preset.slice(0, 4)));
    if (btn) btn.classList.add('active');

    const nameInput = document.getElementById('cam-name-input');
    const typeSelect = document.getElementById('cam-type-select');
    const addrInput = document.getElementById('cam-address-input');
    const hintSpan = document.getElementById('cam-address-hint');
    const guideTitle = document.getElementById('cgb-title');
    const guideList = document.getElementById('cgb-list');

    if (preset === 'DEVICE_CAM') {
        if (nameInput) nameInput.value = 'Direct Phone Camera (Browser Stream)';
        if (typeSelect) typeSelect.value = 'PHONE';
        if (addrInput) addrInput.value = 'browser:getusermedia';
        if (hintSpan) hintSpan.innerHTML = '✨ Zero install required! Tap <strong>"Start Device Camera"</strong> below to broadcast your phone camera live.';
        if (guideTitle) guideTitle.textContent = '💡 How to Use Direct Phone Camera (Render Cloud Mode):';
        if (guideList) {
            guideList.innerHTML = `
                <li>Works 100% on Render and mobile phones with zero extra apps or IP setup.</li>
                <li>Tap <button type="button" class="btn" onclick="startDeviceCameraStream()" style="background:#10b981;color:#000;font-weight:700;padding:5px 12px;border-radius:6px;border:none;margin:4px 0;cursor:pointer;">📸 Start Phone Camera Now</button></li>
                <li>Allow camera access when prompted, point your phone at the TV wall.</li>
                <li>Your phone relays live frames to Render automatically!</li>
            `;
        }
    } else if (preset === 'DROIDCAM') {
        if (nameInput) nameInput.value = 'Phone Camera (DroidCam)';
        if (typeSelect) typeSelect.value = 'PHONE';
        if (addrInput) addrInput.value = 'http://192.168.1.105:4747/video';
        if (hintSpan) hintSpan.innerHTML = 'For DroidCam on phone, enter: <code>http://&lt;phone-ip&gt;:4747/video</code>';
        if (guideTitle) guideTitle.textContent = '💡 How to Connect Your Smartphone (DroidCam):';
        if (guideList) {
            guideList.innerHTML = `
                <li>Download the free <strong>DroidCam</strong> app on your phone (Android/iOS).</li>
                <li>Connect your phone to the same Wi-Fi router as this GameWatch PC.</li>
                <li>Open DroidCam, note the Wi-Fi IP &amp; Port (4747), enter: <code>http://&lt;phone_ip&gt;:4747/video</code>.</li>
            `;
        }
    } else if (preset === 'IPWEBCAM') {
        if (nameInput) nameInput.value = 'Phone Camera (IP Webcam)';
        if (typeSelect) typeSelect.value = 'PHONE';
        if (addrInput) addrInput.value = 'http://192.168.1.105:8080/video';
        if (hintSpan) hintSpan.innerHTML = 'For IP Webcam on phone, enter: <code>http://&lt;phone-ip&gt;:8080/video</code>';
        if (guideTitle) guideTitle.textContent = '💡 How to Connect Your Smartphone (IP Webcam):';
        if (guideList) {
            guideList.innerHTML = `
                <li>Download free <strong>IP Webcam</strong> by Pavel Khlebovich from Google Play Store.</li>
                <li>Ensure your phone is on the same Wi-Fi router network as GameWatch.</li>
                <li>Scroll to the bottom of the IP Webcam app and tap <strong>Start Server</strong>.</li>
                <li>Enter the exact IPv4 URL shown on your phone screen: <code>http://&lt;phone-ip&gt;:8080/video</code>.</li>
            `;
        }
    } else if (preset === 'USB') {
        if (nameInput) nameInput.value = 'USB Video Capture Card (Elgato / Cam Link)';
        if (typeSelect) typeSelect.value = 'USB';
        if (addrInput) addrInput.value = '0';
        if (hintSpan) hintSpan.innerHTML = 'Device index: enter <code>0</code> for primary camera/HDMI capture, or <code>1</code> for secondary.';
        if (guideTitle) guideTitle.textContent = '💡 How to Connect USB Capture Card / HDMI Link:';
        if (guideList) {
            guideList.innerHTML = `
                <li>Plug your USB HDMI capture card (Cam Link / Elgato / generic HDMI capture) into a USB 3.0 port.</li>
                <li>Connect HDMI OUT from the console or TV splitter to the capture card HDMI IN.</li>
                <li>Enter device index <code>0</code> for built-in camera or <code>1</code> for external capture.</li>
            `;
        }
    } else if (preset === 'RTSP') {
        if (nameInput) nameInput.value = 'CCTV Security Camera (RTSP)';
        if (typeSelect) typeSelect.value = 'RTSP';
        if (addrInput) addrInput.value = 'rtsp://admin:admin123@192.168.1.50:554/live';
        if (hintSpan) hintSpan.innerHTML = 'RTSP URL: enter <code>rtsp://&lt;user&gt;:&lt;pass&gt;@&lt;cctv-ip&gt;:554/stream1</code>';
        if (guideTitle) guideTitle.textContent = '💡 How to Connect IP Security CCTV (RTSP Stream):';
        if (guideList) {
            guideList.innerHTML = `
                <li>Connect an IP surveillance or dome camera covering the lounge gaming wall.</li>
                <li>Find your RTSP URL in the camera or NVR network settings.</li>
                <li>Enter the RTSP stream URL with login credentials: <code>rtsp://&lt;user&gt;:&lt;pass&gt;@&lt;ip&gt;:554/feed</code>.</li>
            `;
        }
    } else if (preset === 'PC') {
        if (nameInput) nameInput.value = 'PC Display Stream / OBS Virtual Cam';
        if (typeSelect) typeSelect.value = 'PC';
        if (addrInput) addrInput.value = 'http://127.0.0.1:8080/live';
        if (hintSpan) hintSpan.innerHTML = 'PC Stream: enter local live stream URL (e.g. <code>http://127.0.0.1:8080/live</code>).';
        if (guideTitle) guideTitle.textContent = '💡 How to Stream PC Screen or OBS Virtual Camera:';
        if (guideList) {
            guideList.innerHTML = `
                <li>In OBS Studio, click <strong>Start Virtual Camera</strong> to stream your monitor.</li>
                <li>If using OBS Virtual Cam, set device type to USB with index <code>1</code> or <code>2</code>.</li>
                <li>If streaming via local network relay, enter the HTTP/WebRTC stream URL.</li>
            `;
        }
    }
}

function onSourceTypeChange(type) {
    if (type === 'PHONE') {
        quickFillCamPreset('IPWEBCAM');
    } else if (type === 'USB') {
        quickFillCamPreset('USB');
    } else if (type === 'RTSP') {
        quickFillCamPreset('RTSP');
    } else {
        quickFillCamPreset('PC');
    }
}

window.toggleTroubleshootGuide = function() {
    const body = document.getElementById('ctb-body');
    const arrow = document.getElementById('ctb-arrow');
    if (!body) return;
    const isHidden = body.style.display === 'none' || !body.style.display;
    body.style.display = isHidden ? 'block' : 'none';
    if (arrow) arrow.textContent = isHidden ? '▲' : '▼';
};

async function saveCameraConnector(e) {
    if (e) e.preventDefault();
    const name = document.getElementById('cam-name-input').value.trim();
    const source_type = document.getElementById('cam-type-select').value;
    const address = document.getElementById('cam-address-input').value.trim();
    const tv_id = parseInt(document.getElementById('cam-tv-select').value, 10);

    if (!name || !address) {
        showToast('Please enter both name and camera address/IP');
        return;
    }

    const submitBtn = document.getElementById('btn-submit-camera');
    if (submitBtn) {
        submitBtn.disabled = true;
        submitBtn.textContent = 'Connecting...';
    }

    try {
        const res = await fetch('/api/camera_sources', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ name, source_type, address, tv_id })
        });
        const data = await res.json();
        if (data.success) {
            if (data.source && data.source.id) {
                try {
                    await fetch(`/api/camera_sources/${data.source.id}/activate`, { method: 'POST' });
                } catch(err) {
                    console.warn('Activate source error:', err);
                }
            }
            showToast(`Connector '${name}' connected & activated live!`);
            closeAddCameraModal();
            fetchCameraSources();

            // Refresh master camera stream
            const masterImg = document.getElementById('master-stream-img');
            if (masterImg) masterImg.src = '/api/stream/full?t=' + Date.now();
        } else {
            showToast(data.message || 'Failed to save camera connector');
        }
    } catch (err) {
        showToast('Error saving camera connector: ' + err.message);
    } finally {
        if (submitBtn) {
            submitBtn.disabled = false;
            submitBtn.innerHTML = `
                <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="20 6 9 17 4 12"></polyline></svg>
                <span>Save &amp; Connect Stream</span>
            `;
        }
    }
}

async function testCameraSource(id, btn) {
    if (btn) {
        btn.disabled = true;
        btn.innerHTML = '<span>⚡ Testing...</span>';
    }
    showToast('Testing camera feed reachability & frames...');

    try {
        const res = await fetch(`/api/camera_sources/${id}/test`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' }
        });
        const data = await res.json();
        if (data.connected || data.status === 'CONNECTED' || data.status === 'READY') {
            showToast(`✅ Stream Verified! ${data.message || 'Feed is active'}`);
        } else {
            showToast(`⚠️ Feed unreachable: ${data.message || 'Check IP or device index'}`);
        }
        fetchCameraSources();
    } catch (err) {
        showToast('Network error while testing camera: ' + err.message);
    } finally {
        if (btn) {
            btn.disabled = false;
            btn.innerHTML = `
                <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"></polygon></svg>
                <span>Test Feed</span>
            `;
        }
    }
}

async function deleteCameraSource(id) {
    if (!confirm('Disconnect and remove this camera connector?')) return;
    try {
        const res = await fetch(`/api/camera_sources/${id}`, {
            method: 'DELETE'
        });
        const data = await res.json();
        if (data.success) {
            showToast('Camera connector removed.');
            fetchCameraSources();
        } else {
            showToast(data.message || 'Failed to remove connector');
        }
    } catch (err) {
        showToast('Error removing camera connector: ' + err.message);
    }
}

// ============================================================
// TV AUTO-DETECTION & SMART ZOOM TO CALIBRATE SCOREBOARDS
// ============================================================
window.triggerAutoDetectTVs = async function() {
    const btn = document.getElementById('btn-auto-detect-tvs');
    const panel = document.getElementById('detected-tvs-panel');
    const grid = document.getElementById('detected-tvs-grid');
    if (!panel || !grid) return;

    if (btn) {
        btn.disabled = true;
        btn.innerHTML = '<span>⚡ Scanning Room Feed...</span>';
    }
    showToast('AI Analyzing room feed for TV screens & sharpness...');

    try {
        const res = await fetch('/api/calibration/auto_detect_tvs', { method: 'POST' });
        const data = await res.json();
        if (!res.ok || !data.success) {
            showToast(data.error || 'Failed to detect TVs', 'error');
            return;
        }

        const screens = data.detected_screens || [];
        if (screens.length === 0) {
            showToast('No TV screens detected in camera feed. Adjust angle or lighting.', 'warning');
            panel.style.display = 'none';
            return;
        }

        panel.style.display = 'block';
        grid.innerHTML = screens.map(s => `
            <div class="dtp-card" onclick="zoomToDetectedTV(${s.tv_id}, ${JSON.stringify(s.bounding_box).replace(/"/g, '&quot;')}, ${JSON.stringify(s.corners || null).replace(/"/g, '&quot;')})">
                <div class="dtp-card-top">
                    <span class="dtp-card-name">📺 ${s.label}</span>
                    <span class="dtp-card-badge">${s.scoreboard_detected ? 'Scoreboard Ready' : 'Screen Located'}</span>
                </div>
                <div class="dtp-card-metrics">
                    <span><strong>Sharpness:</strong> ${s.sharpness_score} (${s.is_blurry ? 'Blurry' : 'Sharp'})</span>
                    <span><strong>Coordinates:</strong> [${s.bounding_box.x}, ${s.bounding_box.y}, ${s.bounding_box.w}x${s.bounding_box.h}]</span>
                    <span><strong>Confidence:</strong> ${s.confidence}%</span>
                </div>
                ${s.warning ? `<div class="dtp-warn-chip">⚠ ${s.warning}</div>` : ''}
                <button type="button" class="btn btn-sm btn-primary" style="margin-top:8px; width:100%;">
                    <span>🎯 Auto-Zoom &amp; Calibrate</span>
                </button>
            </div>
        `).join('');

        drawDetectedTVOverlays(screens);
        showToast(`✨ Auto-detected ${screens.length} TV screen(s)! Click one to calibrate.`);
    } catch (err) {
        showToast('Error during TV auto-detection: ' + err.message, 'error');
    } finally {
        if (btn) {
            btn.disabled = false;
            btn.innerHTML = '<span>✨ Auto-Detect TVs</span>';
        }
    }
};

function drawDetectedTVOverlays(screens) {
    if (!App.canvas || !App.ctx) return;
    App.ctx.clearRect(0, 0, App.canvas.width, App.canvas.height);

    screens.forEach(s => {
        const b = s.bounding_box;
        App.ctx.strokeStyle = s.is_blurry ? '#f59e0b' : '#00d4ff';
        App.ctx.lineWidth = 3;
        App.ctx.strokeRect(b.x, b.y, b.w, b.h);

        App.ctx.fillStyle = s.is_blurry ? 'rgba(245, 158, 11, 0.15)' : 'rgba(0, 212, 255, 0.12)';
        App.ctx.fillRect(b.x, b.y, b.w, b.h);

        App.ctx.fillStyle = s.is_blurry ? '#f59e0b' : '#00d4ff';
        App.ctx.font = 'bold 14px Outfit, sans-serif';
        App.ctx.fillText(`TV ${s.tv_id}: ${s.label} (${s.sharpness_score} pts)`, b.x + 8, Math.max(b.y - 8, 20));
    });
}

window.zoomToDetectedTV = function(tvId, bbox, corners) {
    const select = document.getElementById('station-select');
    if (select) select.value = String(tvId);

    const nameInput = document.getElementById('station-name-input');
    if (nameInput) nameInput.value = `TV ${tvId} - Station`;

    if (corners && corners.length === 4) {
        window.setCalibrationMode('keystone');
        App.pins = [
            { x: corners[0][0], y: corners[0][1], label: 'TL', color: '#10B981' },
            { x: corners[1][0], y: corners[1][1], label: 'TR', color: '#06B6D4' },
            { x: corners[2][0], y: corners[2][1], label: 'BR', color: '#8B5CF6' },
            { x: corners[3][0], y: corners[3][1], label: 'BL', color: '#F59E0B' }
        ];
        drawCanvasOverlay();
        updateCoordDisplay();
        triggerKeystoneAnalysis();
        showToast(`🎯 Zoomed to TV ${tvId}! Keystone perspective calibrated.`);
    } else if (bbox) {
        App.currentBox = [bbox.x, bbox.y, bbox.w, bbox.h];
        initPinsFromBox(App.currentBox);
        drawCanvasOverlay();
        updateCoordDisplay(App.currentBox);
        if (App.calibMode === 'keystone') {
            triggerKeystoneAnalysis();
        } else {
            triggerScreenAnalysis(App.currentBox);
        }
        showToast(`🎯 Zoomed to TV ${tvId}! Scoreboard calibration ready.`);
    }
};

// ============================================================
// CLERK LOUNGE CODE BINDING & CUSTOMER EXPLORER
// ============================================================
window.openClerkCodeModal = function() {
    const modal = document.getElementById('clerk-code-modal');
    if (modal) {
        modal.classList.add('open');
        const codeInput = document.getElementById('input-clerk-code');
        if (codeInput) {
            codeInput.value = '';
            setTimeout(() => codeInput.focus(), 100);
        }
        const errSpan = document.getElementById('err-clerk-code');
        if (errSpan) {
            errSpan.textContent = '';
            errSpan.classList.remove('visible');
        }
    }
};

window.closeClerkCodeModal = function() {
    const modal = document.getElementById('clerk-code-modal');
    if (modal) modal.classList.remove('open');
    if ((App.currentRole === 'CLERK' || App.selectedRole === 'CLERK' || App.currentUser?.role === 'CLERK') && !App.currentUser?.joined_lounge_code) {
        showToast('Lounge Access Code is required for Station Clerks to access stations.', 'warning');
        handleLogout();
    }
};

window.submitClerkLoungeCode = async function(e) {
    if (e) e.preventDefault();
    const codeInput = document.getElementById('input-clerk-code');
    const errSpan = document.getElementById('err-clerk-code');
    const submitBtn = document.getElementById('btn-submit-clerk-code');
    const code = codeInput ? codeInput.value.trim().toUpperCase() : '';

    if (!code) {
        if (errSpan) { errSpan.textContent = '⚠ Lounge code is required'; errSpan.classList.add('visible'); }
        return;
    }
    if (errSpan) { errSpan.textContent = ''; errSpan.classList.remove('visible'); }

    if (submitBtn) {
        submitBtn.disabled = true;
        submitBtn.innerHTML = '<span>Verifying...</span>';
    }

    try {
        const verifyRes = await fetch(`/api/auth/verify_lounge_code?code=${encodeURIComponent(code)}`);
        const verifyData = await verifyRes.json();
        const isValid = verifyData && (verifyData.valid === true || verifyData.success === true) && verifyData.lounge;
        if (!verifyRes.ok || !isValid) {
            if (errSpan) { errSpan.textContent = '⚠ ' + (verifyData.message || verifyData.error || 'Invalid Lounge Access Code'); errSpan.classList.add('visible'); }
            if (submitBtn) {
                submitBtn.disabled = false;
                submitBtn.innerHTML = '<span>Verify &amp; Connect Lounge</span>';
            }
            return;
        }

        const res = await fetch('/api/auth/set_role', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ role: 'CLERK', lounge_code: code })
        });
        const data = await res.json();
        if (data.success) {
            App.currentUser = data.user;
            App.currentUser.joined_lounge_code = code;
            const modal = document.getElementById('clerk-code-modal');
            if (modal) modal.classList.remove('open');
            showToast(`Connected to ${verifyData.lounge.name} as Station Clerk!`);
            applyRole('CLERK');
            fetchState();
        } else {
            if (errSpan) { errSpan.textContent = '⚠ ' + (data.message || data.error || 'Failed to bind clerk'); errSpan.classList.add('visible'); }
        }
    } catch (err) {
        showToast('Error verifying lounge code: ' + err.message, 'error');
    } finally {
        if (submitBtn) {
            submitBtn.disabled = false;
            submitBtn.innerHTML = '<span>Verify &amp; Connect Lounge</span>';
        }
    }
};

window.openCustomerOnboardingModal = function() {
    const modal = document.getElementById('customer-onboarding-modal');
    if (modal) modal.classList.add('open');
};

window.closeCustomerOnboardingModal = function() {
    const modal = document.getElementById('customer-onboarding-modal');
    if (modal) modal.classList.remove('open');
};

window.openLoungeCodeEntry = function() {
    const sec = document.getElementById('cust-code-section');
    if (sec) sec.style.display = 'block';
};

window.submitCustomerLoungeCode = async function(e) {
    if (e) e.preventDefault();
    const code = document.getElementById('input-cust-code')?.value.trim().toUpperCase();
    if (!code) {
        showToast('Please enter a lounge code', 'error');
        return;
    }
    await joinLoungeByCode(code);
    closeCustomerOnboardingModal();
};

window.chooseExploreLounges = function() {
    closeCustomerOnboardingModal();
    openLoungeExplorerModal();
};

window.openLoungeExplorerModal = async function() {
    const modal = document.getElementById('lounge-explorer-modal');
    if (modal) modal.classList.add('open');
    await loadExplorerLounges('');
};

window.closeLoungeExplorerModal = function() {
    const modal = document.getElementById('lounge-explorer-modal');
    if (modal) modal.classList.remove('open');
};

let searchDebounceTimer = null;
window.onExplorerSearchInput = function(query) {
    clearTimeout(searchDebounceTimer);
    searchDebounceTimer = setTimeout(() => {
        loadExplorerLounges(query);
    }, 250);
};

async function loadExplorerLounges(search) {
    const list = document.getElementById('explorer-lounges-list');
    if (!list) return;
    list.innerHTML = '<div style="color:var(--text-secondary); padding:20px; font-size:0.8rem;">Loading gaming lounges...</div>';

    try {
        let url = `/api/lounges?search=${encodeURIComponent(search || '')}`;
        if (App.userLocation && App.userLocation.lat && App.userLocation.lng) {
            url += `&lat=${App.userLocation.lat}&lng=${App.userLocation.lng}`;
        }
        const res = await fetch(url);
        const data = await res.json();
        renderExplorerLounges(data.lounges || []);
    } catch (e) {
        list.innerHTML = '<div style="color:#f87171; padding:20px; font-size:0.8rem;">Error loading lounges</div>';
    }
}

function renderExplorerLounges(lounges) {
    const list = document.getElementById('explorer-lounges-list');
    if (!list) return;
    if (lounges.length === 0) {
        list.innerHTML = '<div style="color:var(--text-secondary); padding:20px; font-size:0.8rem;">No lounges found matching your search.</div>';
        return;
    }

    list.innerHTML = lounges.map(l => {
        const distBadge = (l.distance_km != null) ? 
            `<span class="distance-badge">🚗 ${l.distance_km < 1 ? Math.round(l.distance_km * 1000) + ' m' : l.distance_km.toFixed(1) + ' km'} away</span>` : '';
        const areaBadge = l.area ? `<span class="lhh-pill lhh-pill-area" style="font-size:0.75rem;">📍 ${escapeHtml(l.area)}</span>` : '';

        return `
            <div class="lounge-card" onclick="joinLoungeByCode('${l.lounge_code}')">
                <div class="lc-head">
                    <span class="lc-title">${escapeHtml(l.name)}</span>
                    <span class="lc-code-badge">${l.lounge_code}</span>
                </div>
                <div style="display:flex; gap:6px; align-items:center; flex-wrap:wrap; margin:4px 0;">
                    ${areaBadge}
                    ${distBadge}
                </div>
                <span class="lc-address">${escapeHtml(l.address || 'Addis Ababa')}</span>
                <div class="lc-stats">
                    <span>📺 ${l.total_tvs} Stations</span>
                    <span>🎮 ${l.rate_per_game} ETB / Match</span>
                </div>
                <button type="button" class="btn btn-sm btn-primary" style="margin-top:6px;">
                    <span>Connect &amp; View Live</span>
                </button>
            </div>
        `;
    }).join('');
}

window.requestUserLocation = function() {
    const btn = document.getElementById('btn-gps-locate');
    if (!navigator.geolocation) {
        showToast('Geolocation not supported by this browser', 'error');
        return;
    }
    if (btn) btn.innerHTML = '<span>📡 Locating...</span>';
    navigator.geolocation.getCurrentPosition(
        (pos) => {
            App.userLocation = {
                lat: pos.coords.latitude,
                lng: pos.coords.longitude
            };
            if (btn) {
                btn.classList.add('active');
                btn.innerHTML = '<span>📍 Near Me (Active)</span>';
            }
            showToast('📍 Location detected! Lounges sorted by proximity.');
            const searchVal = document.getElementById('input-explorer-search')?.value || '';
            loadExplorerLounges(searchVal);
        },
        (err) => {
            console.warn('Geolocation error:', err);
            if (btn) btn.innerHTML = '<span>📍 Near Me</span>';
            showToast('Unable to detect GPS. You can filter by area chips below.', 'info');
        },
        { timeout: 8000, enableHighAccuracy: true }
    );
};

window.filterByAreaChip = function(areaName) {
    const input = document.getElementById('input-explorer-search');
    if (input) input.value = areaName;

    const chips = document.querySelectorAll('.area-chip');
    chips.forEach(c => {
        const text = c.textContent.replace('📍', '').trim().toLowerCase();
        if ((!areaName && text.includes('all')) || (areaName && text.toLowerCase() === areaName.toLowerCase())) {
            c.classList.add('active');
        } else {
            c.classList.remove('active');
        }
    });

    loadExplorerLounges(areaName);
};

window.joinLoungeByCode = async function(code) {
    try {
        const res = await fetch('/api/auth/set_role', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ role: 'CUSTOMER', lounge_code: code })
        });
        const data = await res.json();
        if (data.success) {
            closeLoungeExplorerModal();
            showToast(`Connected to Lounge (${code})!`);
            App.currentUser = data.user;
            applyRole('CUSTOMER');
            fetchState();
        } else {
            showToast(data.error || 'Failed to connect to lounge', 'error');
        }
    } catch (e) {
        showToast('Connection error: ' + e.message, 'error');
    }
};

window.copyLoungeCode = function() {
    const code = document.getElementById('settings-lounge-code')?.textContent || 
                 document.getElementById('lpc-code-display')?.textContent || 
                 document.getElementById('header-lounge-code-text')?.textContent || '';
    if (!code) return;
    navigator.clipboard.writeText(code).then(() => {
        showToast(`📋 Copied Lounge Code: ${code}`);
    }).catch(() => {
        showToast(`Lounge Code: ${code}`);
    });
};

// ============================================================
// SPONSORSHIP, PARTNER SHOWCASE & TOURNAMENT STANDINGS
// ============================================================
const PARTNER_DATA = {
    shebatech: {
        title: "ShebaTech Gaming & Accessories",
        sub: "Official Gaming Hardware Partner • Bole Medhanialem",
        icon: "🎮",
        desc: "Addis Ababa's top supplier for genuine Sony PlayStation 5 consoles, DualSense controllers, thumb grips, HDMI 2.1 cables, and replacement analog sticks. GameWatch lounges receive an exclusive 10% wholesale discount.",
        perk: "🎁 Exclusive 10% Discount Code: GAMEWATCH10",
        phone: "0921615614",
        tel: "tel:0921615614"
    },
    hub: {
        title: "Sheba Gaming Hub",
        sub: "PS5 & PS4 Wholesale Accessories Supplier",
        icon: "🕹️",
        desc: "Direct importer of gaming accessories, replacement buttons, high-durability charging docks, and headphone splitters for commercial gaming centers across Ethiopia.",
        perk: "🔥 Bulk Controller Trade-in & Repair Program",
        phone: "0911778899",
        tel: "tel:0911778899"
    },
    fiber: {
        title: "Habesha High-Speed Fiber",
        sub: "Ultra-Low Latency ISP for Commercial Lounges",
        icon: "⚡",
        desc: "Dedicated symmetric fiber optics engineered for multiplayer competitive gaming. Guaranteed 15ms ping to EA Sports servers, with zero packet loss during peak weekend hours.",
        perk: "🚀 Free Static IP + Business Router with Lounge Sign-up",
        phone: "0944112233",
        tel: "tel:0944112233"
    },
    repair: {
        title: "Bole Console Repair Lab",
        sub: "Certified HDMI Port, Liquid Metal & Power Supply Repair",
        icon: "🔧",
        desc: "Specialized maintenance for PS5 & PS4 consoles experiencing overheating, blinking blue lights, or damaged HDMI ports. 24-hour turnaround for GameWatch affiliated lounges.",
        perk: "🛠️ 20% Off Deep Cleaning & Thermal Paste Service",
        phone: "0933556677",
        tel: "tel:0933556677"
    }
};

window.openSponsorLink = function(sponsorId) {
    if (sponsorId === 'predator') {
        showToast("Opening Predator Energy Drink official website...");
        window.open('https://www.predatorenergydrink.com/en-za/', '_blank', 'noopener,noreferrer');
    } else if (sponsorId === 'tournament') {
        openTournamentStandingsModal();
    } else if (PARTNER_DATA[sponsorId]) {
        openPartnerModal(sponsorId);
    } else {
        showToast("Partner info coming soon!", "info");
    }
};

window.openTournamentStandingsModal = function() {
    const modal = document.getElementById('tournament-standings-modal');
    if (modal) {
        modal.classList.add('open');
        document.body.style.overflow = 'hidden';
    }
};

window.closeTournamentModal = function() {
    const modal = document.getElementById('tournament-standings-modal');
    if (modal) {
        modal.classList.remove('open');
        document.body.style.overflow = '';
    }
};

window.handleRegisterTournament = function() {
    closeTournamentModal();
    showToast("Opening Tournament Bracket Registration...");
    switchView('customer');
    setTimeout(() => {
        const custTab = document.querySelector('.cl-tab[data-cltab="tournaments"]');
        if (custTab) custTab.click();
    }, 100);
};

window.openPartnerModal = function(partnerKey) {
    const data = PARTNER_DATA[partnerKey];
    if (!data) return;

    const modal = document.getElementById('modal-sponsor-partner');
    if (!modal) return;

    const iconEl = document.getElementById('ps-modal-icon');
    if (iconEl) iconEl.textContent = data.icon || '🎮';
    const titleEl = document.getElementById('ps-modal-title');
    if (titleEl) titleEl.textContent = data.title;
    const subEl = document.getElementById('ps-modal-sub');
    if (subEl) subEl.textContent = data.sub;
    const descEl = document.getElementById('ps-modal-desc');
    if (descEl) descEl.textContent = data.desc;
    const perkEl = document.getElementById('ps-modal-perk');
    if (perkEl) perkEl.textContent = data.perk;
    const phoneEl = document.getElementById('ps-modal-phone');
    if (phoneEl) phoneEl.textContent = data.phone;
    
    const callBtn = document.getElementById('ps-modal-call-btn');
    if (callBtn) {
        callBtn.href = data.tel;
        callBtn.innerHTML = `<span>Call Partner (${data.phone})</span>`;
    }

    modal.classList.add('open');
    document.body.style.overflow = 'hidden';
};

window.closePartnerModal = function() {
    const modal = document.getElementById('modal-sponsor-partner');
    if (modal) {
        modal.classList.remove('open');
        document.body.style.overflow = '';
    }
};

// Wire backdrop dismissals
document.addEventListener('DOMContentLoaded', () => {
    const tm = document.getElementById('tournament-standings-modal');
    if (tm) {
        tm.addEventListener('click', (e) => {
            if (e.target === tm) closeTournamentModal();
        });
    }
    const pm = document.getElementById('modal-sponsor-partner');
    if (pm) {
        pm.addEventListener('click', (e) => {
            if (e.target === pm) closePartnerModal();
        });
    }
});

// ============================================================
// INTERACTIVE SPONSOR CAROUSELS CONTROLLER
// ============================================================
const HERO_SLIDES = [
    {
        id: "shebatech",
        tag: "Official Gaming Hardware Partner",
        title: "ShebaTech Gaming & Accessories",
        desc: "Original DualSense Controllers, PS5 Discs & Repair Center – Bole Medhanialem",
        img: "/static/img/ps5_3d_hero.jpg",
        ctaText: "Call Store (10% Off) →",
        action: () => openPartnerModal('shebatech')
    },
    {
        id: "predator",
        tag: "Official Gaming Energy Drink",
        title: "Predator Energy Ethiopia",
        desc: "Stay Energized in Every Round. Fuel Your Play with Zero Crash Taurine Formula.",
        img: "/static/img/predator_energy.jpg",
        ctaText: "Visit Predator Energy →",
        action: () => openSponsorLink('predator')
    },
    {
        id: "tournament",
        tag: "Premier National League Title Sponsor",
        title: "Harif Sport & Entertainment",
        desc: "Official EA FC 25 National Tournament Series · 100,000 ETB Grand Final Cash Prize",
        img: "/static/img/ea_fc25_stadium_banner.jpg",
        ctaText: "Tournament Standings →",
        action: () => openTournamentStandingsModal()
    },
    {
        id: "repair",
        tag: "Certified Console Service",
        title: "Bole Precision Console Repair",
        desc: "HDMI Port Replacement, Liquid Metal Thermal Service & DualSense Stick Drift Fix",
        img: "/static/img/ps5_3d_hero.jpg",
        ctaText: "Book Console Repair →",
        action: () => openPartnerModal('repair')
    }
];

let currentHeroIndex = 0;
let heroTimer = null;

function renderHeroSlide(idx) {
    currentHeroIndex = (idx + HERO_SLIDES.length) % HERO_SLIDES.length;
    const s = HERO_SLIDES[currentHeroIndex];
    
    const tag = document.getElementById('hero-tag');
    const title = document.getElementById('hero-title');
    const desc = document.getElementById('hero-desc');
    const img = document.getElementById('hero-img');
    const cta = document.getElementById('hero-cta-label');
    
    if (tag) tag.textContent = s.tag;
    if (title) title.textContent = s.title;
    if (desc) desc.textContent = s.desc;
    if (img) {
        img.src = s.img;
        img.alt = s.title;
    }
    if (cta) cta.textContent = s.ctaText;
    
    const dots = document.querySelectorAll('#hero-dots-container .hsc-dot');
    dots.forEach((d, i) => {
        d.classList.toggle('active', i === currentHeroIndex);
    });
}

window.nextHeroSlide = function() {
    renderHeroSlide(currentHeroIndex + 1);
    resetHeroTimer();
};

window.prevHeroSlide = function() {
    renderHeroSlide(currentHeroIndex - 1);
    resetHeroTimer();
};

window.setHeroSlide = function(idx) {
    renderHeroSlide(idx);
    resetHeroTimer();
};

window.handleHeroCtaClick = function() {
    const s = HERO_SLIDES[currentHeroIndex];
    if (s && typeof s.action === 'function') {
        s.action();
    }
};

function resetHeroTimer() {
    if (heroTimer) clearInterval(heroTimer);
    heroTimer = setInterval(() => {
        renderHeroSlide(currentHeroIndex + 1);
    }, 6000);
}

// ============================================================
// FOOTER PANORAMIC BILLBOARD CONTROLLER
// ============================================================
const FOOTER_SLIDES = [
    {
        tag: "PREMIER NATIONAL LEAGUE TITLE SPONSOR",
        title: "Harif Sport & Entertainment",
        desc: "Official EA FC 25 National Tournament Series • 100,000 ETB Grand Final Cash Prize Pool",
        btnText: "Tournament Standings →",
        action: () => switchView('tournaments')
    },
    {
        tag: "EXHIBITION SHOWCASE & PRIZE POOL",
        title: "Addis Masters Cup 2026",
        desc: "32 Elite Lounges Competing Live across Bole & Kazanchis • Grand Finals Broadcast",
        btnText: "Register Squad →",
        action: () => switchView('tournaments')
    },
    {
        tag: "COMMERCIAL HARDWARE PARTNER",
        title: "ShebaTech Gaming & Accessories",
        desc: "Official DualSense Edge, OEM PS5 Cooling Stations & 2.1 HDMI Cables for Lounges",
        btnText: "Get 10% Voucher →",
        action: () => openPartnerModal('shebatech')
    },
    {
        tag: "ULTRA LOW-PING INFRASTRUCTURE",
        title: "Habesha High-Speed Fiber",
        desc: "Dedicated Esports Bandwidth & 15ms Latency to EA FC 25 Dedicated Match Servers",
        btnText: "Lounge Fiber Plan →",
        action: () => openPartnerModal('fiber')
    }
];

let currentFooterIndex = 0;
let footerTimer = null;

function renderFooterSlide(idx) {
    currentFooterIndex = (idx + FOOTER_SLIDES.length) % FOOTER_SLIDES.length;
    const s = FOOTER_SLIDES[currentFooterIndex];

    const tag = document.getElementById('footer-slide-tag');
    const title = document.getElementById('footer-slide-title');
    const desc = document.getElementById('footer-slide-desc');
    const btnText = document.getElementById('footer-slide-btn-text');

    if (tag) tag.textContent = s.tag;
    if (title) title.textContent = s.title;
    if (desc) desc.textContent = s.desc;
    if (btnText) btnText.textContent = s.btnText;

    const bars = document.querySelectorAll('#footer-bars-container .sbb-bar');
    bars.forEach((b, i) => {
        b.classList.toggle('active', i === currentFooterIndex);
    });
}

window.nextFooterSlide = function() {
    renderFooterSlide(currentFooterIndex + 1);
    resetFooterTimer();
};

window.prevFooterSlide = function() {
    renderFooterSlide(currentFooterIndex - 1);
    resetFooterTimer();
};

window.setFooterSlide = function(idx) {
    renderFooterSlide(idx);
    resetFooterTimer();
};

window.handleFooterCtaClick = function() {
    const s = FOOTER_SLIDES[currentFooterIndex];
    if (s && typeof s.action === 'function') {
        s.action();
    }
};

function resetFooterTimer() {
    if (footerTimer) clearInterval(footerTimer);
    footerTimer = setInterval(() => {
        renderFooterSlide(currentFooterIndex + 1);
    }, 7000);
}

function initSponsorCarousels() {
    renderHeroSlide(0);
    resetHeroTimer();
    renderFooterSlide(0);
    resetFooterTimer();
}





// ============================================================================
// GAMEWATCH TOURNAMENTS & CHAMPIONS LEAGUE HUB MODULE (125-Match Engine)
// UEFA 2010 Style (Groups of 4 -> Knockouts), Glass Tumbler Draw, Owner Analytics
// ============================================================================

let currentTournamentData = null;
let activeArenaTab = 'roster';
let currentTournFilter = 'ALL';
let currentFixtureStage = 'ALL';
let lotteryAnimationId = null;
let lotteryBalls = [];
let lotterySpinning = false;
let lotteryDrawnIndices = [];
function escapeHtml(str) {
    if (str === null || str === undefined) return '';
    return String(str)
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#39;');
}
window.escapeHtml = escapeHtml;

// Club Badges mapping for authentic European Champions League styling
const CLUB_BADGES = {
    'Real Madrid': '🇪🇸 Real Madrid',
    'Manchester City': '🏴󠁧󠁢󠁥󠁮󠁧󠁿 Man City',
    'Arsenal': '🏴󠁧󠁢󠁥󠁮󠁧󠁿 Arsenal',
    'Barcelona': '🇪🇸 FC Barcelona',
    'Bayern Munich': '🇩🇪 Bayern Munich',
    'Liverpool': '🏴󠁧󠁢󠁥󠁮󠁧󠁿 Liverpool',
    'Paris Saint-Germain': '🇫🇷 PSG',
    'Inter Milan': '🇮🇹 Inter Milan',
    'Chelsea': '🏴󠁧󠁢󠁥󠁮󠁧󠁿 Chelsea',
    'AC Milan': '🇮🇹 AC Milan',
    'Atletico Madrid': '🇪🇸 Atl. Madrid',
    'Bayer Leverkusen': '🇩🇪 Leverkusen',
    'Juventus': '🇮🇹 Juventus',
    'Borussia Dortmund': '🇩🇪 Dortmund',
    'Aston Villa': '🏴󠁧󠁢󠁥󠁮󠁧󠁿 Aston Villa',
    'Napoli': '🇮🇹 Napoli'
};

function formatClubName(club) {
    if (!club) return '⚽ Gamer Club';
    return CLUB_BADGES[club] || `⚽ ${club}`;
}

// ----------------------------------------------------------------------------
// 1. CREATE TOURNAMENT MODAL & LIVE PROFIT CALCULATOR
// ----------------------------------------------------------------------------
window.openCreateTournamentModal = function() {
    const modal = document.getElementById('modal-create-event');
    if (!modal) return;
    const form = document.getElementById('form-create-event');
    if (form) form.reset();
    
    // Set realistic defaults matching user specs
    const fmt = document.getElementById('event-format');
    if (fmt) fmt.value = 'CHAMPIONS_LEAGUE';
    const dur = document.getElementById('event-duration');
    if (dur) dur.value = '1_MONTH';
    const maxP = document.getElementById('event-max');
    if (maxP) maxP.value = '32';
    const fee = document.getElementById('event-fee');
    if (fee) fee.value = '200';
    const loser = document.getElementById('event-loser-fee');
    if (loser) loser.value = '25';
    const titleInput = document.getElementById('event-title');
    if (titleInput) titleInput.value = 'Addis Ababa EA FC 25 Champions League';
    const prize = document.getElementById('event-prize-amount');
    if (prize) prize.value = '2500';
    const prizeLabel = document.getElementById('event-prize');
    if (prizeLabel) prizeLabel.value = '2,500 ETB (1st: 2,000, 2nd: 500)';

    updateTournModalCalc();
    modal.classList.add('open');
};

window.closeCreateEventModal = function() {
    const modal = document.getElementById('modal-create-event');
    if (modal) modal.classList.remove('open');
};

window.updateTournModalCalc = function() {
    const fmt = document.getElementById('event-format')?.value || 'CHAMPIONS_LEAGUE';
    const maxP = parseInt(document.getElementById('event-max')?.value, 10) || 32;
    const fee = parseFloat(document.getElementById('event-fee')?.value) || 200;
    const loserFee = parseFloat(document.getElementById('event-loser-fee')?.value) || 25;
    const prizeAmount = parseFloat(document.getElementById('event-prize-amount')?.value) || 2500;

    // Total games calculation based on format:
    // 32-player Champions League 2010: 8 groups * 12 games = 96 group stage games
    // Knockout: R16 (16 games) + QF (8 games) + SF (4 games) + Final (1 game) = 29 games. Total = 125 games.
    let totalGames = 125;
    let groupGames = 96;
    let koGames = 29;
    if (fmt === 'CHAMPIONS_LEAGUE') {
        if (maxP >= 32) {
            totalGames = 125;
            groupGames = 96;
            koGames = 29;
        } else {
            totalGames = 61;
            groupGames = 48;
            koGames = 13;
        }
    } else {
        totalGames = Math.max(1, maxP - 1);
        groupGames = 0;
        koGames = totalGames;
    }

    const entryRev = maxP * fee;
    const matchRev = totalGames * loserFee;
    const grossRev = entryRev + matchRev;
    const netProfit = grossRev - prizeAmount;
    const margin = grossRev > 0 ? ((netProfit / grossRev) * 100).toFixed(1) : 0;

    const elMargin = document.getElementById('tcc-margin-badge');
    const elEntry = document.getElementById('tcc-entry-rev');
    const elMatch = document.getElementById('tcc-match-rev');
    const elGross = document.getElementById('tcc-gross-rev');
    const elNet = document.getElementById('tcc-net-profit');

    if (elMargin) elMargin.textContent = `Owner Margin: ~${margin}%`;
    if (elEntry) elEntry.textContent = `${entryRev.toLocaleString()} ETB`;
    if (elMatch) elMatch.textContent = `${matchRev.toLocaleString()} ETB (${totalGames} games × ${loserFee} ETB)`;
    if (elGross) elGross.textContent = `${grossRev.toLocaleString()} ETB`;
    if (elNet) elNet.textContent = `${netProfit.toLocaleString()} ETB`;
};

window.handleSaveEvent = async function(e) {
    if (e) e.preventDefault();
    const title = (document.getElementById('event-title')?.value || '').trim();
    if (!title) {
        showToast('Please enter a tournament title', 'error');
        return;
    }

    const payload = {
        title: title,
        game: document.getElementById('event-game')?.value || 'EA FC 25',
        tournament_format: document.getElementById('event-format')?.value || 'CHAMPIONS_LEAGUE',
        tournament_duration: document.getElementById('event-duration')?.value || '1_MONTH',
        max_participants: parseInt(document.getElementById('event-max')?.value, 10) || 32,
        entry_fee: parseFloat(document.getElementById('event-fee')?.value) || 200,
        loser_match_fee: parseFloat(document.getElementById('event-loser-fee')?.value) || 25,
        prize_pool: document.getElementById('event-prize')?.value || '2,500 ETB',
        total_prize_amount: parseFloat(document.getElementById('event-prize-amount')?.value) || 2500,
        rules: document.getElementById('event-rules')?.value || ''
    };

    try {
        const res = await fetch('/api/events', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });
        const data = await res.json();
        if (!res.ok || !data.success) {
            showToast(data.message || 'Failed to create tournament', 'error');
            return;
        }

        showToast('🏆 Tournament Created Successfully!', 'success');
        closeCreateEventModal();
        const newId = data.event_id || (data.event && data.event.id);
        if (newId) {
            openTournamentDetail(newId, 'roster');
        }
    } catch (err) {
        console.error('Error creating tournament:', err);
        showToast('Network error creating tournament', 'error');
    }
};

// ----------------------------------------------------------------------------
// 2. TOURNAMENTS LIST & FILTERING
// ----------------------------------------------------------------------------
window.loadTournamentsHub = async function() {
    try {
        const res = await fetch('/api/events');
        const data = await res.json();
        const events = data.events || [];

        const badge = document.getElementById('thub-active-count-badge');
        if (badge) badge.textContent = `${events.length} Tournament${events.length === 1 ? '' : 's'}`;

        renderTournamentsCards(events);
    } catch (err) {
        console.error('Error loading tournaments:', err);
        showToast('Failed to load tournaments list', 'error');
    }
};

window.filterTournaments = function(filter) {
    currentTournFilter = filter;
    document.querySelectorAll('.thub-ftab').forEach(t => {
        t.classList.toggle('active', t.getAttribute('data-filter') === filter);
    });
    loadTournamentsHub();
};

function renderTournamentsCards(events) {
    const grid = document.getElementById('thub-cards-grid');
    if (!grid) return;

    let filtered = events;
    if (currentTournFilter === 'IN_PROGRESS') {
        filtered = events.filter(e => e.draw_completed === 1 && !e.winner_id);
    } else if (currentTournFilter === 'UPCOMING') {
        filtered = events.filter(e => !e.draw_completed);
    } else if (currentTournFilter === 'COMPLETED') {
        filtered = events.filter(e => !!e.winner_id);
    }

    if (!filtered || filtered.length === 0) {
        grid.innerHTML = `
            <div class="thub-empty-state" style="grid-column: 1 / -1; text-align: center; padding: 48px 20px; background: rgba(15,23,42,0.6); border: 1px dashed rgba(255,255,255,0.1); border-radius: 16px;">
                <div style="font-size: 3rem; margin-bottom: 12px;">🏆</div>
                <h3 style="color: var(--text-primary); font-size: 1.2rem; margin-bottom: 6px;">No Tournaments Found</h3>
                <p style="color: var(--text-secondary); max-width: 440px; margin: 0 auto 20px; font-size: 0.9rem;">
                    Launch an authentic 32-player Champions League 2010 tournament with glass tumbler ball draw & verified owner profit ledger.
                </p>
                <button type="button" class="btn btn-primary" onclick="openCreateTournamentModal()">
                    + Create First Tournament
                </button>
            </div>
        `;
        return;
    }

    grid.innerHTML = filtered.map(t => {
        const isCL = (t.tournament_format || 'CHAMPIONS_LEAGUE') === 'CHAMPIONS_LEAGUE';
        const formatLabel = isCL ? 'UEFA Champions League 2010 Style' : 'Single Elimination Knockout';
        const durationMap = { '1_MONTH': '1 Month', '2_WEEKS': '2 Weeks', '2_MONTHS': '2 Months' };
        const durLabel = durationMap[t.tournament_duration] || '1 Month';
        const maxSlots = t.max_participants || 32;
        const currentCount = t.participant_count || 0;
        const pct = Math.min(100, Math.round((currentCount / maxSlots) * 100));

        let statusBadge = '<span class="thub-badge-cyan">⏳ Open Registration</span>';
        if (t.winner_id) {
            statusBadge = `<span class="thub-badge-gold">👑 Champion: ${escapeHtml(t.winner_name || 'Champion')}</span>`;
        } else if (t.draw_completed === 1) {
            statusBadge = '<span class="thub-badge-live">🔥 Live Tournament In Progress</span>';
        } else if (t.roster_locked === 1) {
            statusBadge = '<span class="thub-badge-gold">🔒 Roster Locked • Ready For Draw</span>';
        }

        const isOwner = (App.currentRole || '').toUpperCase() === 'OWNER';

        return `
            <div class="tourn-card" onclick="openTournamentDetail(${t.id})">
                <div class="tourn-card-head">
                    <span class="tourn-badge">${escapeHtml(durLabel)} &bull; ${isCL ? 'Groups of 4' : 'Knockout'}</span>
                    ${statusBadge}
                </div>
                <h3 class="tourn-card-title">${escapeHtml(t.title)}</h3>
                <div class="tourn-card-game">🎮 ${escapeHtml(t.game || 'EA FC 25')} &bull; PS5</div>
                
                <div class="tourn-card-body">
                    <div class="tourn-card-metas">
                        <div class="tcm-item">
                            <span class="tcm-label">Entry Fee</span>
                            <span class="tcm-val text-cyan">${t.entry_fee || 200} ETB</span>
                        </div>
                        <div class="tcm-item">
                            <span class="tcm-label">Loser / Game</span>
                            <span class="tcm-val text-rose">${t.loser_match_fee || 25} ETB</span>
                        </div>
                        <div class="tcm-item">
                            <span class="tcm-label">Prize Pool</span>
                            <span class="tcm-val text-gold">${escapeHtml(t.prize_pool || '2,500 ETB')}</span>
                        </div>
                    </div>

                    <div class="tourn-progress-bar-wrap">
                        <div class="tourn-prog-labels">
                            <span>Players: ${currentCount} / ${maxSlots}</span>
                            <span>${pct}% Full</span>
                        </div>
                        <div class="tourn-prog-track">
                            <div class="tourn-prog-fill" style="width: ${pct}%;"></div>
                        </div>
                    </div>
                </div>

                <div class="tourn-card-foot">
                    <button type="button" class="btn-enter-arena" onclick="event.stopPropagation(); openTournamentDetail(${t.id});">
                        <span>Enter Arena Hub &rarr;</span>
                    </button>
                    ${isOwner ? `
                        <button type="button" class="btn btn-sm btn-outline-danger" onclick="event.stopPropagation(); deleteTournament(${t.id});" title="Delete tournament">
                            🗑️
                        </button>
                    ` : ''}
                </div>
            </div>
        `;
    }).join('');
}

window.deleteTournament = async function(id) {
    if (!confirm('Are you sure you want to delete this tournament? All rosters, matches, and ledger data will be deleted.')) return;
    try {
        const res = await fetch(`/api/events/${id}`, { method: 'DELETE' });
        const data = await res.json();
        if (data.success) {
            showToast('Tournament deleted successfully', 'success');
            loadTournamentsHub();
        } else {
            showToast(data.message || 'Failed to delete tournament', 'error');
        }
    } catch (e) {
        showToast('Error deleting tournament', 'error');
    }
};

// ----------------------------------------------------------------------------
// 3. TOURNAMENT ARENA HUB & NAVIGATION
// ----------------------------------------------------------------------------
window.openTournamentDetail = async function(eventId, initialTab = 'roster') {
    App.activeTournamentId = eventId;

    const listView = document.getElementById('thub-list-view');
    const arenaView = document.getElementById('thub-detail-arena');
    if (listView) listView.style.display = 'none';
    if (arenaView) arenaView.style.display = 'block';

    window.scrollTo({ top: 0, behavior: 'smooth' });

    await fetchAndRenderArena(eventId, initialTab);
};

window.closeTournamentDetail = function() {
    stopLotterySimulation();
    App.activeTournamentId = null;
    currentTournamentData = null;

    const listView = document.getElementById('thub-list-view');
    const arenaView = document.getElementById('thub-detail-arena');
    if (listView) listView.style.display = 'block';
    if (arenaView) arenaView.style.display = 'none';

    loadTournamentsHub();
};

async function fetchAndRenderArena(eventId, preferredTab = null) {
    try {
        const res = await fetch(`/api/events/${eventId}`);
        const data = await res.json();
        if (!data || !data.success) {
            showToast(data.message || 'Failed to load tournament arena', 'error');
            closeTournamentDetail();
            return;
        }

        currentTournamentData = data;
        const e = data.event;
        const isOwner = (App.currentRole || '').toUpperCase() === 'OWNER';

        // Update chips & hero
        const isCL = (e.tournament_format || 'CHAMPIONS_LEAGUE') === 'CHAMPIONS_LEAGUE';
        const durationMap = { '1_MONTH': '⏱ 1 Month', '2_WEEKS': '⏱ 2 Weeks', '2_MONTHS': '⏱ 2 Months' };

        const formatChip = document.getElementById('tarena-format-chip');
        if (formatChip) formatChip.textContent = isCL ? 'UEFA Champions League 2010 (32 Players)' : 'Single Elimination Knockout';

        const durChip = document.getElementById('tarena-duration-chip');
        if (durChip) durChip.textContent = durationMap[e.tournament_duration] || '⏱ 1 Month';

        const statusChip = document.getElementById('tarena-status-chip');
        if (statusChip) {
            if (e.winner_id) statusChip.textContent = `👑 Champion: ${e.winner_name}`;
            else if (e.draw_completed === 1) statusChip.textContent = '🔥 Tournament In Progress';
            else if (e.roster_locked === 1) statusChip.textContent = '🔒 Ready For Ball Draw';
            else statusChip.textContent = '⏳ Registration Open';
        }

        const titleEl = document.getElementById('tarena-title');
        if (titleEl) titleEl.textContent = e.title;

        const gameLabel = document.getElementById('tarena-game-label');
        if (gameLabel) gameLabel.textContent = `${e.game || 'EA FC 25'} • PS5`;

        const entryLabel = document.getElementById('tarena-entry-label');
        if (entryLabel) entryLabel.textContent = `${e.entry_fee || 200} ETB Entry`;

        const prizeLabel = document.getElementById('tarena-prize-label');
        if (prizeLabel) prizeLabel.textContent = `${e.prize_pool || '2,500 ETB'} Prize Pool`;

        const rosterCount = document.getElementById('tarena-roster-count');
        if (rosterCount) rosterCount.textContent = (data.participants || []).length;

        // Owner action controls
        const ownerBar = document.getElementById('tarena-owner-actions-bar');
        const analyticsTab = document.getElementById('tarena-tab-analytics');
        if (ownerBar) ownerBar.style.display = isOwner ? 'flex' : 'none';
        if (analyticsTab) analyticsTab.style.display = isOwner ? 'flex' : 'none';

        const btnLock = document.getElementById('btn-lock-roster');
        if (btnLock) {
            btnLock.innerHTML = e.roster_locked === 1 ? '<span>✓ Roster Locked</span>' : '<span>🔒 Lock Roster</span>';
            btnLock.classList.toggle('btn-secondary', e.roster_locked !== 1);
            btnLock.classList.toggle('btn-outline-gold', e.roster_locked === 1);
        }

        // Determine which tab to show
        let targetTab = preferredTab || activeArenaTab || 'roster';
        if (!preferredTab && e.draw_completed === 1 && activeArenaTab === 'roster') {
            targetTab = 'groups';
        }
        switchArenaTab(targetTab);
    } catch (err) {
        console.error('Error fetching arena data:', err);
        showToast('Error loading arena data', 'error');
    }
}

window.switchArenaTab = function(tabName) {
    activeArenaTab = tabName;

    // Update tab buttons
    document.querySelectorAll('.tarena-tab').forEach(btn => {
        btn.classList.toggle('active', btn.getAttribute('data-arena-tab') === tabName);
    });

    // Update tab panels
    document.querySelectorAll('.tarena-panel').forEach(p => {
        p.classList.toggle('active', p.id === `tarena-panel-${tabName}`);
    });

    if (!currentTournamentData) return;

    if (tabName === 'roster') {
        renderTournamentRoster(currentTournamentData.participants || []);
    } else if (tabName === 'draw') {
        initLotteryBallsCanvas();
    } else if (tabName === 'groups') {
        renderTournamentGroups(currentTournamentData.groups || {});
    } else if (tabName === 'fixtures') {
        renderTournamentFixtures(currentTournamentData.matches || []);
    } else if (tabName === 'bracket') {
        renderKnockoutTree(currentTournamentData.matches || [], currentTournamentData.event?.winner_name);
    } else if (tabName === 'analytics') {
        renderTournamentAnalytics(currentTournamentData.business_analytics, currentTournamentData.event);
    }
};

// ----------------------------------------------------------------------------
// 4. ROSTER & PARTICIPANT REGISTRATION
// ----------------------------------------------------------------------------
function renderTournamentRoster(participants) {
    const tbody = document.getElementById('tarena-roster-tbody');
    if (!tbody) return;

    const countEl = document.getElementById('tarena-roster-count');
    if (countEl) countEl.textContent = participants.length;

    if (!participants || participants.length === 0) {
        tbody.innerHTML = `
            <tr>
                <td colspan="8" style="text-align: center; padding: 32px 16px; color: var(--text-secondary);">
                    No players registered yet. Click <strong>+ Register Player</strong> or Lounge Owner can tap <strong>⚡ Fill 32 Gamers</strong> for instant demo roster.
                </td>
            </tr>
        `;
        return;
    }

    const isOwner = (App.currentRole || '').toUpperCase() === 'OWNER';

    tbody.innerHTML = participants.map((p, idx) => {
        const clubBadge = formatClubName(p.chosen_club);
        const groupBadge = p.group_letter && p.group_letter !== 'UNASSIGNED' 
            ? `<span class="badge badge-cyan">Group ${p.group_letter}</span>` 
            : `<span class="badge badge-muted">Unassigned</span>`;
        const feeBadge = p.fee_paid === 1 
            ? `<span class="text-emerald" style="font-weight:600;">✓ Paid</span>` 
            : `<span class="text-amber" style="font-weight:600;">Pending</span>`;

        return `
            <tr>
                <td style="font-weight:700; color:var(--text-secondary); width:40px;">${idx + 1}</td>
                <td>
                    <div style="display:flex; align-items:center; gap:8px;">
                        <span style="font-size:1.1rem;">👤</span>
                        <strong style="color:var(--text-primary);">${escapeHtml(p.customer_name)}</strong>
                    </div>
                </td>
                <td style="color:var(--text-secondary);">${escapeHtml(p.customer_phone || '—')}</td>
                <td>
                    <span class="roster-club-pill">${clubBadge}</span>
                </td>
                <td>${groupBadge}</td>
                <td>${feeBadge}</td>
                <td style="font-size:0.8rem; color:var(--text-muted);">${escapeHtml((p.registered_at || '').split('T')[0] || 'Today')}</td>
                <td>
                    ${isOwner ? `
                        <button type="button" class="btn btn-xs btn-outline-cyan" onclick="togglePlayerPaid(${p.id}, ${p.fee_paid === 1 ? 0 : 1})" title="Toggle payment status">
                            ${p.fee_paid === 1 ? 'Mark Unpaid' : 'Mark Paid'}
                        </button>
                    ` : '—'}
                </td>
            </tr>
        `;
    }).join('');
}

window.openRegisterPlayerModal = function() {
    const modal = document.getElementById('modal-register-tourn-player');
    if (!modal) return;
    const form = document.getElementById('form-register-tourn-player');
    if (form) form.reset();
    modal.classList.add('open');
};

window.closeRegisterPlayerModal = function() {
    const modal = document.getElementById('modal-register-tourn-player');
    if (modal) modal.classList.remove('open');
};

window.handleSavePlayerRegistration = async function(e) {
    if (e) e.preventDefault();
    if (!App.activeTournamentId) return;

    const name = (document.getElementById('reg-player-name')?.value || '').trim();
    if (!name) {
        showToast('Please enter player name', 'error');
        return;
    }
    const phone = (document.getElementById('reg-player-phone')?.value || '').trim();
    let club = document.getElementById('reg-player-club')?.value || 'Real Madrid';
    if (club === 'Other / Custom') {
        club = (document.getElementById('reg-player-custom-club')?.value || '').trim() || 'Custom FC';
    }
    const pm = document.getElementById('reg-payment-method')?.value || 'CASH';

    try {
        const res = await fetch(`/api/events/${App.activeTournamentId}/register`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                customer_name: name,
                customer_phone: phone,
                chosen_club: club,
                payment_method: pm
            })
        });
        const data = await res.json();
        if (data.success) {
            showToast(`⚽ ${name} registered with ${club}!`, 'success');
            closeRegisterPlayerModal();
            fetchAndRenderArena(App.activeTournamentId, 'roster');
        } else {
            showToast(data.message || 'Registration failed', 'error');
        }
    } catch (err) {
        showToast('Network error during registration', 'error');
    }
};

window.handleSeedDemoRoster = async function() {
    if (!App.activeTournamentId) return;
    try {
        showToast('⚡ Seeding 32 realistic Addis Ababa gamers & European clubs...', 'info');
        const res = await fetch(`/api/events/${App.activeTournamentId}/seed_demo`, { method: 'POST' });
        const data = await res.json();
        if (data.success) {
            showToast('✅ 32 Addis Gamers & European Clubs Loaded!', 'success');
            fetchAndRenderArena(App.activeTournamentId, 'roster');
        } else {
            showToast(data.message || 'Failed to seed gamers', 'error');
        }
    } catch (e) {
        showToast('Error seeding demo gamers', 'error');
    }
};

window.handleLockRoster = async function() {
    if (!App.activeTournamentId) return;
    try {
        const res = await fetch(`/api/events/${App.activeTournamentId}/lock_roster`, { method: 'POST' });
        const data = await res.json();
        if (data.success) {
            showToast('🔒 Roster Locked! Launching Official Glass Sphere Ball Draw...', 'success');
            await fetchAndRenderArena(App.activeTournamentId, 'draw');
        } else {
            showToast(data.message || 'Failed to lock roster', 'error');
        }
    } catch (e) {
        showToast('Error locking roster', 'error');
    }
};

window.togglePlayerPaid = async function(regId, newStatus) {
    if (!App.activeTournamentId) return;
    try {
        const res = await fetch(`/api/events/participants/${regId}/pay`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ fee_paid: newStatus })
        });
        const data = await res.json();
        if (data.success) {
            showToast(newStatus === 1 ? 'Player fee marked as PAID' : 'Player fee marked as UNPAID', 'success');
            fetchAndRenderArena(App.activeTournamentId, 'roster');
        }
    } catch (e) {}
};

// ----------------------------------------------------------------------------
// 5. GLASS SPHERE LOTTERY BALL TUMBLER DRAW (Physical Canvas Simulation)
// Realistic glossy bouncing balls in crystal dome matching user's uploaded image
// ----------------------------------------------------------------------------
const BALL_PALETTE = [
    { bg: '#3B82F6', text: '#FFFFFF', name: 'Blue' },
    { bg: '#EF4444', text: '#FFFFFF', name: 'Red' },
    { bg: '#10B981', text: '#FFFFFF', name: 'Green' },
    { bg: '#F59E0B', text: '#111827', name: 'Yellow' },
    { bg: '#8B5CF6', text: '#FFFFFF', name: 'Purple' },
    { bg: '#EC4899', text: '#FFFFFF', name: 'Magenta' },
    { bg: '#06B6D4', text: '#FFFFFF', name: 'Cyan' },
    { bg: '#F97316', text: '#FFFFFF', name: 'Orange' },
    { bg: '#F8FAFC', text: '#0F172A', name: 'White' },
    { bg: '#1E293B', text: '#F8FAFC', name: 'Slate' }
];

window.initLotteryBallsCanvas = function() {
    stopLotterySimulation();
    const canvas = document.getElementById('lottery-balls-canvas');
    if (!canvas) return;
    const ctx = canvas.getContext('2d');

    const participants = (currentTournamentData?.participants || []);
    const count = Math.max(32, participants.length);

    // Initial sphere center and radius
    const cx = canvas.width / 2;
    const cy = 205;
    const sphereRadius = 175;

    lotteryBalls = [];
    for (let i = 0; i < count; i++) {
        const pal = BALL_PALETTE[i % BALL_PALETTE.length];
        const angle = Math.random() * Math.PI * 2;
        const dist = Math.random() * (sphereRadius - 35);
        lotteryBalls.push({
            id: i + 1,
            num: i + 1,
            x: cx + Math.cos(angle) * dist,
            y: cy + Math.sin(angle) * dist,
            vx: (Math.random() - 0.5) * 3,
            vy: (Math.random() - 0.5) * 3,
            radius: 17,
            color: pal.bg,
            textColor: pal.text,
            isDrawn: false,
            rotation: Math.random() * Math.PI * 2,
            vRot: (Math.random() - 0.5) * 0.1
        });
    }

    renderLotteryGroupsGrid(currentTournamentData?.groups || {});
    updateLotterySpotlight(null);

    // Start physics animation loop
    function animate() {
        ctx.clearRect(0, 0, canvas.width, canvas.height);

        // 1. Draw outer glass container glow
        const glowGrad = ctx.createRadialGradient(cx, cy, sphereRadius * 0.4, cx, cy, sphereRadius + 15);
        glowGrad.addColorStop(0, 'rgba(30, 58, 138, 0.1)');
        glowGrad.addColorStop(0.8, 'rgba(56, 189, 248, 0.15)');
        glowGrad.addColorStop(1, 'rgba(56, 189, 248, 0.35)');
        ctx.fillStyle = glowGrad;
        ctx.beginPath();
        ctx.arc(cx, cy, sphereRadius, 0, Math.PI * 2);
        ctx.fill();

        // 2. Physics update for balls
        const gravity = 0.18;
        const friction = 0.985;
        const spinForce = lotterySpinning ? 1.8 : 0;

        for (let b of lotteryBalls) {
            if (b.isDrawn) continue;

            // Swirling centrifugal whirlwind force when spinning
            if (lotterySpinning) {
                const dx = b.x - cx;
                const dy = b.y - cy;
                const dist = Math.hypot(dx, dy) || 1;
                // Tangential force
                b.vx += (-dy / dist) * spinForce + (Math.random() - 0.5) * 1.5;
                b.vy += (dx / dist) * spinForce + (Math.random() - 0.5) * 1.5;
            } else {
                b.vy += gravity;
            }

            b.vx *= friction;
            b.vy *= friction;
            b.x += b.vx;
            b.y += b.vy;
            b.rotation += b.vRot;

            // Collision with spherical container boundary
            const dx = b.x - cx;
            const dy = b.y - cy;
            const dist = Math.hypot(dx, dy);
            if (dist + b.radius > sphereRadius) {
                const nx = dx / dist;
                const ny = dy / dist;
                // Reflect velocity
                const dot = b.vx * nx + b.vy * ny;
                b.vx -= 1.8 * dot * nx;
                b.vy -= 1.8 * dot * ny;
                // Push back inside
                b.x = cx + nx * (sphereRadius - b.radius);
                b.y = cy + ny * (sphereRadius - b.radius);
            }

            // Draw glossy ball with 3D spherical gradient
            drawLotterySphere(ctx, b);
        }

        // 3. Draw glass rim and specular shine overlays
        drawGlassDomeOverlay(ctx, cx, cy, sphereRadius);

        lotteryAnimationId = requestAnimationFrame(animate);
    }

    animate();
};

function drawLotterySphere(ctx, b) {
    ctx.save();
    ctx.translate(b.x, b.y);
    ctx.rotate(b.rotation);

    // Ball 3D Radial Sphere Gradient
    const grad = ctx.createRadialGradient(-5, -5, 2, 0, 0, b.radius);
    grad.addColorStop(0, '#FFFFFF');
    grad.addColorStop(0.35, b.color);
    grad.addColorStop(1, '#020617');

    ctx.fillStyle = grad;
    ctx.beginPath();
    ctx.arc(0, 0, b.radius, 0, Math.PI * 2);
    ctx.fill();

    // Subtle edge rim shadow
    ctx.strokeStyle = 'rgba(0,0,0,0.3)';
    ctx.lineWidth = 1;
    ctx.stroke();

    // Central White Circular Badge for Number (Matching reference photo)
    ctx.fillStyle = '#FFFFFF';
    ctx.beginPath();
    ctx.arc(0, 0, 8.5, 0, Math.PI * 2);
    ctx.fill();

    // Ball Number text
    ctx.fillStyle = '#0F172A';
    ctx.font = 'bold 9px "Inter", sans-serif';
    ctx.textAlign = 'center';
    ctx.textBaseline = 'middle';
    ctx.fillText(String(b.num), 0, 0.5);

    ctx.restore();
}

function drawGlassDomeOverlay(ctx, cx, cy, radius) {
    ctx.save();

    // Glass rim ring with cyan glow
    ctx.strokeStyle = 'rgba(56, 189, 248, 0.5)';
    ctx.lineWidth = 3;
    ctx.beginPath();
    ctx.arc(cx, cy, radius, 0, Math.PI * 2);
    ctx.stroke();

    // Specular curved glare crescent at top-left
    ctx.beginPath();
    ctx.arc(cx - 30, cy - 30, radius * 0.75, Math.PI * 1.05, Math.PI * 1.45);
    ctx.strokeStyle = 'rgba(255, 255, 255, 0.45)';
    ctx.lineWidth = 6;
    ctx.stroke();

    // Subtle inner refraction highlight
    ctx.beginPath();
    ctx.arc(cx, cy, radius - 6, 0, Math.PI * 2);
    ctx.strokeStyle = 'rgba(255, 255, 255, 0.12)';
    ctx.lineWidth = 1.5;
    ctx.stroke();

    ctx.restore();
}

function stopLotterySimulation() {
    if (lotteryAnimationId) {
        cancelAnimationFrame(lotteryAnimationId);
        lotteryAnimationId = null;
    }
    lotterySpinning = false;
}

window.renderLotteryGroupsGrid = function(groups, newlyAssignedId = null) {
    const grid = document.getElementById('lottery-draw-groups-grid');
    if (!grid) return;

    const groupLetters = ['A', 'B', 'C', 'D', 'E', 'F', 'G', 'H'];
    grid.innerHTML = groupLetters.map(letter => {
        const members = groups[letter] || [];
        return `
            <div class="lottery-group-pod" id="lottery-pod-${letter}">
                <div class="lgp-head">
                    <span class="lgp-letter">Group ${letter}</span>
                    <span class="lgp-count">${members.length} / 4</span>
                </div>
                <div class="lgp-members-list">
                    ${members.map((m, mIdx) => `
                        <div class="lgp-member-row ${m.id === newlyAssignedId ? 'just-drawn' : ''}">
                            <span class="lgp-slot">${mIdx + 1}</span>
                            <div class="lgp-member-info">
                                <span class="lgp-name">${escapeHtml(m.customer_name)}</span>
                                <span class="lgp-club">${formatClubName(m.chosen_club)}</span>
                            </div>
                        </div>
                    `).join('')}
                    ${Array.from({ length: Math.max(0, 4 - members.length) }).map((_, i) => `
                        <div class="lgp-member-row empty">
                            <span class="lgp-slot">${members.length + i + 1}</span>
                            <span class="lgp-empty-label">Slot Open</span>
                        </div>
                    `).join('')}
                </div>
            </div>
        `;
    }).join('');
};

function updateLotterySpotlight(ballData, participant = null, slotLabel = '') {
    const ballSphere = document.getElementById('spotlight-ball-sphere');
    const numEl = document.getElementById('spc-ball-num');
    const nameEl = document.getElementById('spc-player-name');
    const clubEl = document.getElementById('spc-club-badge');
    const groupEl = document.getElementById('spc-group-assignment');
    const progressEl = document.getElementById('spotlight-progress-text');

    if (!ballData || !participant) {
        if (ballSphere) {
            ballSphere.textContent = '?';
            ballSphere.style.background = 'radial-gradient(circle at 30% 30%, #3B82F6, #1E3A8A)';
        }
        if (numEl) numEl.textContent = 'Ball #--';
        if (nameEl) nameEl.textContent = 'Ready to Draw...';
        if (clubEl) clubEl.textContent = '⚽ Glass Tumbler Armed';
        if (groupEl) groupEl.textContent = 'Tap "Spin & Draw Next Ball"';
        return;
    }

    if (ballSphere) {
        ballSphere.textContent = String(ballData.num);
        ballSphere.style.background = `radial-gradient(circle at 30% 30%, #FFFFFF, ${ballData.color} 40%, #020617 95%)`;
        ballSphere.classList.remove('pulse-reveal');
        void ballSphere.offsetWidth; // trigger reflow
        ballSphere.classList.add('pulse-reveal');
    }
    if (numEl) numEl.textContent = `Ball #${ballData.num}`;
    if (nameEl) nameEl.textContent = participant.customer_name;
    if (clubEl) clubEl.textContent = formatClubName(participant.chosen_club);
    if (groupEl) groupEl.textContent = slotLabel;

    const drawnCount = lotteryBalls.filter(b => b.isDrawn).length;
    if (progressEl) progressEl.textContent = `${drawnCount} / 32 Balls Drawn`;
}

window.drawNextLotteryBall = async function() {
    if (!currentTournamentData || !App.activeTournamentId) return;

    if (currentTournamentData.event?.draw_completed === 1) {
        showToast('Official Draw is already completed! Check Group Standings tab.', 'info');
        return;
    }

    const unassigned = (currentTournamentData.participants || []).filter(p => !p.group_letter || p.group_letter === 'UNASSIGNED');
    if (unassigned.length === 0) {
        showToast('All players have been grouped! Finalizing draw...', 'info');
        autoCompleteLotteryDraw();
        return;
    }

    // Spin tumbler vigorously for 1.1s
    lotterySpinning = true;
    const btn = document.getElementById('btn-draw-next-ball');
    if (btn) btn.disabled = true;

    setTimeout(async () => {
        lotterySpinning = false;
        if (btn) btn.disabled = false;

        // Pick next random undrawn ball from canvas
        const undrawnBalls = lotteryBalls.filter(b => !b.isDrawn);
        const ball = undrawnBalls.length > 0 ? undrawnBalls[Math.floor(Math.random() * undrawnBalls.length)] : { num: 1, color: '#3B82F6' };
        ball.isDrawn = true;

        // Pick next participant and assign to next group slot (A to H in order)
        const p = unassigned[0];
        const groupLetters = ['A', 'B', 'C', 'D', 'E', 'F', 'G', 'H'];
        const groups = currentTournamentData.groups || {};
        
        let targetLetter = 'A';
        for (let l of groupLetters) {
            if ((groups[l] || []).length < 4) {
                targetLetter = l;
                break;
            }
        }

        if (!groups[targetLetter]) groups[targetLetter] = [];
        p.group_letter = targetLetter;
        p.seed_number = groups[targetLetter].length + 1;
        groups[targetLetter].push(p);

        // Update UI
        updateLotterySpotlight(ball, p, `Assigned to Group ${targetLetter} (Slot #${p.seed_number})`);
        renderLotteryGroupsGrid(groups, p.id);

        showToast(`🎲 Ball #${ball.num}: ${p.customer_name} -> Group ${targetLetter}!`, 'success');

        // If that was the last participant, persist to backend
        const remaining = (currentTournamentData.participants || []).filter(item => !item.group_letter || item.group_letter === 'UNASSIGNED');
        if (remaining.length === 0) {
            await autoCompleteLotteryDraw();
        }
    }, 1100);
};

window.autoCompleteLotteryDraw = async function() {
    if (!App.activeTournamentId) return;
    try {
        showToast('⚡ Finalizing official lottery draw & generating 125 fixtures...', 'info');
        const res = await fetch(`/api/events/${App.activeTournamentId}/draw`, { method: 'POST' });
        const data = await res.json();
        if (data.success) {
            showToast('🎉 Official Champions League Draw Complete! 125 Fixtures Generated.', 'success');
            await fetchAndRenderArena(App.activeTournamentId, 'groups');
        } else {
            showToast(data.message || 'Draw execution failed', 'error');
        }
    } catch (e) {
        showToast('Error completing lottery draw', 'error');
    }
};

window.resetLotteryDraw = function() {
    initLotteryBallsCanvas();
    showToast('Lottery tumbler reset. Ready to draw.', 'info');
};

// ----------------------------------------------------------------------------
// 6. UEFA CHAMPIONS LEAGUE 2010 GROUP STANDINGS (8 Groups of 4)
// ----------------------------------------------------------------------------
function renderTournamentGroups(groups) {
    const grid = document.getElementById('tarena-groups-standings-grid');
    if (!grid) return;

    const groupLetters = ['A', 'B', 'C', 'D', 'E', 'F', 'G', 'H'];
    const hasAnyGroups = groupLetters.some(l => (groups[l] || []).length > 0);

    if (!hasAnyGroups) {
        grid.innerHTML = `
            <div style="grid-column: 1 / -1; text-align: center; padding: 48px 20px; background: rgba(15,23,42,0.6); border-radius: 16px; border: 1px dashed rgba(255,255,255,0.1);">
                <div style="font-size: 3rem; margin-bottom: 12px;">📊</div>
                <h3 style="color:var(--text-primary); margin-bottom: 6px;">Groups Not Yet Drawn</h3>
                <p style="color:var(--text-secondary); max-width: 440px; margin: 0 auto 20px; font-size: 0.9rem;">
                    Once the 32 gamers are locked, launch the <strong>Glass Tumbler Ball Draw</strong> to randomize teams into Groups A through H.
                </p>
                <button type="button" class="btn btn-gold" onclick="switchArenaTab('draw')">
                    🎲 Go to Live Ball Draw
                </button>
            </div>
        `;
        return;
    }

    grid.innerHTML = groupLetters.map(letter => {
        const teams = groups[letter] || [];
        return `
            <div class="champions-group-box">
                <div class="cgb-head">
                    <span class="cgb-title">GROUP ${letter}</span>
                    <span class="cgb-sub">Top 2 Qualify for Round of 16</span>
                </div>
                <div class="tourn-table-responsive">
                    <table class="tourn-standings-table">
                        <thead>
                            <tr>
                                <th style="width:26px;">#</th>
                                <th style="text-align:left;">Team / Gamer</th>
                                <th title="Matches Played">P</th>
                                <th title="Won">W</th>
                                <th title="Drawn">D</th>
                                <th title="Lost">L</th>
                                <th title="Goals For">GF</th>
                                <th title="Goals Against">GA</th>
                                <th title="Goal Difference" class="col-gd">GD</th>
                                <th title="Points" class="col-pts">PTS</th>
                            </tr>
                        </thead>
                        <tbody>
                            ${teams.map((t, idx) => {
                                const isTop2 = (idx < 2);
                                return `
                                    <tr class="${isTop2 ? 'qualified-row' : ''}">
                                        <td>
                                            <div style="display:flex; align-items:center; gap:3px; justify-content:center;">
                                                <span style="font-weight:700;">${idx + 1}</span>
                                                ${isTop2 ? '<span class="q-badge" title="Qualified for R16">Q</span>' : ''}
                                            </div>
                                        </td>
                                        <td style="text-align:left;">
                                            <div class="gamer-cell-info">
                                                <strong class="gamer-cell-name">${escapeHtml(t.customer_name)}</strong>
                                                <span class="gamer-cell-club">${formatClubName(t.chosen_club)}</span>
                                            </div>
                                        </td>
                                        <td>${t.matches_played || 0}</td>
                                        <td>${t.won || 0}</td>
                                        <td>${t.drawn || 0}</td>
                                        <td>${t.lost || 0}</td>
                                        <td>${t.goals_for || 0}</td>
                                        <td>${t.goals_against || 0}</td>
                                        <td class="col-gd" style="font-weight:700; color:${(t.goal_diff || 0) >= 0 ? 'var(--emerald)' : 'var(--rose)'};">
                                            ${(t.goal_diff || 0) > 0 ? '+' : ''}${t.goal_diff || 0}
                                        </td>
                                        <td class="col-pts" style="font-weight:900; font-size:0.95rem; color:var(--electric);">${t.points || 0}</td>
                                    </tr>
                                `;
                            }).join('')}
                        </tbody>
                    </table>
                </div>
            </div>
        `;
    }).join('');
}

// ----------------------------------------------------------------------------
// 7. FIXTURES, LIVE SCORE RECORDING & AGREED SCHEDULE LOCK
// ----------------------------------------------------------------------------
window.filterFixturesByStage = function(stage) {
    currentFixtureStage = stage;
    document.querySelectorAll('.ff-pill').forEach(btn => {
        btn.classList.toggle('active', btn.getAttribute('onclick')?.includes(stage));
    });
    if (currentTournamentData) {
        renderTournamentFixtures(currentTournamentData.matches || []);
    }
};

function renderTournamentFixtures(matches) {
    const container = document.getElementById('tarena-fixtures-list');
    if (!container) return;

    if (!matches || matches.length === 0) {
        container.innerHTML = `
            <div style="text-align: center; padding: 48px 20px; background: rgba(15,23,42,0.6); border-radius: 16px; border: 1px dashed rgba(255,255,255,0.1);">
                <div style="font-size: 3rem; margin-bottom: 12px;">⚔️</div>
                <h3 style="color:var(--text-primary); margin-bottom: 6px;">Fixtures Generated After Draw</h3>
                <p style="color:var(--text-secondary); max-width: 440px; margin: 0 auto; font-size: 0.9rem;">
                    Once the groups are drawn, all 125 official tournament fixtures will be scheduled here.
                </p>
            </div>
        `;
        return;
    }

    let filtered = matches;
    if (currentFixtureStage !== 'ALL') {
        filtered = matches.filter(m => m.stage === currentFixtureStage);
    }

    const isOwnerOrClerk = ['OWNER', 'CLERK'].includes((App.currentRole || '').toUpperCase());

    container.innerHTML = filtered.map(m => {
        const isCompleted = m.status === 'COMPLETED';
        const p1Score = isCompleted ? (m.score1 ?? '-') : '-';
        const p2Score = isCompleted ? (m.score2 ?? '-') : '-';

        let winnerBadge = '';
        if (isCompleted && m.winner_name) {
            winnerBadge = `<span class="badge badge-gold">Winner: ${escapeHtml(m.winner_name)}</span>`;
        }

        const schedDate = m.scheduled_date || 'Date TBD';
        const schedTime = m.scheduled_time || 'Time TBD';
        const tvName = `TV ${m.tv_station_id || 1}`;

        return `
            <div class="tourn-fixture-card ${isCompleted ? 'completed' : ''}">
                <div class="tfc-head">
                    <div class="tfc-head-tags">
                        <span class="tfc-stage-pill">${escapeHtml(m.round_name || m.stage)}</span>
                        ${m.group_letter ? `<span class="badge badge-cyan">Group ${m.group_letter}</span>` : ''}
                    </div>
                    <div class="tfc-head-status">
                        ${winnerBadge}
                        <span class="badge ${isCompleted ? 'badge-muted' : 'badge-live'}">
                            ${isCompleted ? '✓ Completed' : '⏳ Scheduled'}
                        </span>
                    </div>
                </div>

                <div class="tfc-matchup">
                    <!-- Player 1 -->
                    <div class="tfc-team tfc-left ${m.winner_id === m.player1_id && isCompleted ? 'winner' : ''}">
                        <div class="tfc-team-text">
                            <span class="tfc-team-name">${escapeHtml(m.player1_name || 'TBD')}</span>
                            <span class="tfc-team-club">${formatClubName(m.player1_club)}</span>
                        </div>
                        <span class="tfc-mobile-score-val">${p1Score}</span>
                    </div>

                    <!-- Score Center (Desktop VS) -->
                    <div class="tfc-score-box">
                        <span class="tfc-score-digit">${p1Score}</span>
                        <span class="tfc-vs-tag">VS</span>
                        <span class="tfc-score-digit">${p2Score}</span>
                    </div>

                    <!-- Player 2 -->
                    <div class="tfc-team tfc-right ${m.winner_id === m.player2_id && isCompleted ? 'winner' : ''}">
                        <div class="tfc-team-text">
                            <span class="tfc-team-name">${escapeHtml(m.player2_name || 'TBD')}</span>
                            <span class="tfc-team-club">${formatClubName(m.player2_club)}</span>
                        </div>
                        <span class="tfc-mobile-score-val">${p2Score}</span>
                    </div>
                </div>

                <div class="tfc-foot">
                    <div class="tfc-schedule-info">
                        <span>📅 ${escapeHtml(schedDate)} &bull; ${escapeHtml(schedTime)} &bull; 📺 ${tvName}</span>
                    </div>

                    <div class="tfc-actions">
                        ${isOwnerOrClerk ? `
                            <button type="button" class="btn btn-xs btn-secondary" onclick="openMatchScheduleModal(${m.id})" title="Lock in mutually agreed match schedule with players">
                                📅 Agreed Date
                            </button>
                            <button type="button" class="btn btn-xs btn-primary" onclick="openMatchScoreModal(${m.id})" title="Input match score">
                                ${isCompleted ? 'Edit Score' : '⚡ Enter Result'}
                            </button>
                        ` : ''}
                    </div>
                </div>

                ${isCompleted && m.loser_name ? `
                    <div class="tfc-loser-notice">
                        💰 Loser Fee Collected: <strong>25 ETB</strong> (${escapeHtml(m.loser_name)}) logged to tournament cash ledger.
                    </div>
                ` : ''}
            </div>
        `;
    }).join('');
}

window.openMatchScoreModal = function(matchId) {
    if (!currentTournamentData) return;
    const match = (currentTournamentData.matches || []).find(m => m.id === matchId);
    if (!match) return;

    const modal = document.getElementById('modal-match-score-entry');
    if (!modal) return;

    document.getElementById('ms-match-id').value = match.id;
    document.getElementById('ms-p1-name').textContent = match.player1_name || 'Player 1';
    document.getElementById('ms-p1-club').textContent = formatClubName(match.player1_club);
    document.getElementById('ms-p2-name').textContent = match.player2_name || 'Player 2';
    document.getElementById('ms-p2-club').textContent = formatClubName(match.player2_club);
    
    document.getElementById('ms-score1').value = match.score1 ?? 0;
    document.getElementById('ms-score2').value = match.score2 ?? 0;
    document.getElementById('ms-stage-meta').textContent = `${match.round_name || match.stage} • TV ${match.tv_station_id || 1}`;
    document.getElementById('ms-notes').value = match.notes || '';

    modal.classList.add('open');
};

window.closeMatchScoreModal = function() {
    const modal = document.getElementById('modal-match-score-entry');
    if (modal) modal.classList.remove('open');
};

window.handleSaveMatchScore = async function(e) {
    if (e) e.preventDefault();
    if (!App.activeTournamentId) return;

    const matchId = document.getElementById('ms-match-id')?.value;
    const score1 = parseInt(document.getElementById('ms-score1')?.value, 10);
    const score2 = parseInt(document.getElementById('ms-score2')?.value, 10);
    const notes = document.getElementById('ms-notes')?.value || '';

    if (isNaN(score1) || isNaN(score2)) {
        showToast('Please enter valid numeric scores', 'error');
        return;
    }

    try {
        const res = await fetch(`/api/events/${App.activeTournamentId}/matches/${matchId}/result`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ score1, score2, notes })
        });
        const data = await res.json();
        if (data.success) {
            showToast('✅ Match result confirmed! Standings & Loser fee logged.', 'success');
            closeMatchScoreModal();
            fetchAndRenderArena(App.activeTournamentId, 'fixtures');
        } else {
            showToast(data.message || 'Failed to record score', 'error');
        }
    } catch (err) {
        showToast('Error recording match result', 'error');
    }
};

window.openMatchScheduleModal = function(matchId) {
    if (!currentTournamentData) return;
    const match = (currentTournamentData.matches || []).find(m => m.id === matchId);
    if (!match) return;

    const modal = document.getElementById('modal-match-schedule-lock');
    if (!modal) return;

    document.getElementById('sched-match-id').value = match.id;
    document.getElementById('sched-match-players').textContent = `${match.player1_name || 'Player 1'} vs ${match.player2_name || 'Player 2'} (${match.round_name || match.stage})`;
    document.getElementById('sched-date').value = match.scheduled_date || 'Saturday, Oct 12';
    document.getElementById('sched-time').value = match.scheduled_time || '04:30 PM';
    document.getElementById('sched-station').value = String(match.tv_station_id || 1);

    modal.classList.add('open');
};

window.closeMatchScheduleModal = function() {
    const modal = document.getElementById('modal-match-schedule-lock');
    if (modal) modal.classList.remove('open');
};

window.handleSaveMatchSchedule = async function(e) {
    if (e) e.preventDefault();
    if (!App.activeTournamentId) return;

    const matchId = document.getElementById('sched-match-id')?.value;
    const schedDate = (document.getElementById('sched-date')?.value || '').trim();
    const schedTime = (document.getElementById('sched-time')?.value || '').trim();
    const tvId = parseInt(document.getElementById('sched-station')?.value, 10) || 1;

    try {
        const res = await fetch(`/api/events/${App.activeTournamentId}/matches/${matchId}/schedule`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ scheduled_date: schedDate, scheduled_time: schedTime, tv_station_id: tvId })
        });
        const data = await res.json();
        if (data.success) {
            showToast('🔒 Mutually agreed match schedule locked!', 'success');
            closeMatchScheduleModal();
            fetchAndRenderArena(App.activeTournamentId, 'fixtures');
        } else {
            showToast(data.message || 'Failed to lock schedule', 'error');
        }
    } catch (err) {
        showToast('Error locking match schedule', 'error');
    }
};

// ----------------------------------------------------------------------------
// 8. KNOCKOUT BRACKET TREE
// ----------------------------------------------------------------------------
function renderKnockoutTree(matches, winnerName) {
    const treeWrap = document.getElementById('tarena-knockout-tree');
    if (!treeWrap) return;

    const koMatches = (matches || []).filter(m => m.stage !== 'GROUPS');

    if (koMatches.length === 0) {
        treeWrap.innerHTML = `
            <div style="text-align: center; padding: 48px 20px; background: rgba(15,23,42,0.6); border-radius: 16px; border: 1px dashed rgba(255,255,255,0.1);">
                <div style="font-size: 3rem; margin-bottom: 12px;">🌳</div>
                <h3 style="color:var(--text-primary); margin-bottom: 6px;">Knockout Tree Unlocks After Group Stage</h3>
                <p style="color:var(--text-secondary); max-width: 440px; margin: 0 auto; font-size: 0.9rem;">
                    Top 2 teams from each of Groups A through H advance to the official Round of 16 bracket.
                </p>
            </div>
        `;
        return;
    }

    const r16 = koMatches.filter(m => m.stage === 'ROUND_OF_16');
    const qf = koMatches.filter(m => m.stage === 'QUARTER_FINAL');
    const sf = koMatches.filter(m => m.stage === 'SEMI_FINAL');
    const finalMatch = koMatches.find(m => m.stage === 'GRAND_FINAL');

    function renderBracketMatch(m) {
        if (!m) return `<div class="kb-match empty"><span class="kb-tbd">Awaiting Qualifier</span></div>`;
        const isDone = m.status === 'COMPLETED';
        return `
            <div class="kb-match ${isDone ? 'done' : ''}" onclick="openMatchScoreModal(${m.id})">
                <div class="kb-team ${isDone && m.winner_id === m.player1_id ? 'win' : ''}">
                    <span class="kb-name">${escapeHtml(m.player1_name || 'TBD')}</span>
                    <span class="kb-score">${isDone ? (m.score1 ?? '-') : '-'}</span>
                </div>
                <div class="kb-team ${isDone && m.winner_id === m.player2_id ? 'win' : ''}">
                    <span class="kb-name">${escapeHtml(m.player2_name || 'TBD')}</span>
                    <span class="kb-score">${isDone ? (m.score2 ?? '-') : '-'}</span>
                </div>
            </div>
        `;
    }

    treeWrap.innerHTML = `
        <div class="knockout-tree-columns">
            <!-- Round of 16 -->
            <div class="kt-col">
                <div class="kt-col-title">Round of 16 (16 Teams)</div>
                <div class="kt-col-matches">
                    ${r16.length > 0 ? r16.map(renderBracketMatch).join('') : '<p class="kb-tbd">Awaiting Group Winners</p>'}
                </div>
            </div>

            <!-- Quarterfinals -->
            <div class="kt-col">
                <div class="kt-col-title">Quarterfinals (8 Teams)</div>
                <div class="kt-col-matches">
                    ${qf.length > 0 ? qf.map(renderBracketMatch).join('') : '<p class="kb-tbd">Awaiting R16 Winners</p>'}
                </div>
            </div>

            <!-- Semifinals -->
            <div class="kt-col">
                <div class="kt-col-title">Semifinals (4 Teams)</div>
                <div class="kt-col-matches">
                    ${sf.length > 0 ? sf.map(renderBracketMatch).join('') : '<p class="kb-tbd">Awaiting QF Winners</p>'}
                </div>
            </div>

            <!-- Grand Final -->
            <div class="kt-col kt-col-final">
                <div class="kt-col-title">Grand Final 🏆</div>
                <div class="kt-col-matches">
                    ${renderBracketMatch(finalMatch)}
                    ${winnerName ? `
                        <div class="champion-podium-card">
                            <span class="podium-trophy">🏆</span>
                            <div class="podium-tag">CHAMPION</div>
                            <div class="podium-winner">${escapeHtml(winnerName)}</div>
                            <div class="podium-prize">2,000 ETB Cash Prize + Trophy</div>
                        </div>
                    ` : ''}
                </div>
            </div>
        </div>
    `;
}

// ----------------------------------------------------------------------------
// 9. OWNER BUSINESS ANALYTICS & PROFIT LEDGER (Owner-Only)
// ----------------------------------------------------------------------------
function renderTournamentAnalytics(analytics, event) {
    if (!analytics || !event) return;

    const isOwner = (App.currentRole || '').toUpperCase() === 'OWNER';
    if (!isOwner) return;

    // Top 5 KPI Summary Cards
    const elEntry = document.getElementById('tana-entry-rev');
    const elEntrySub = document.getElementById('tana-entry-sub');
    const elMatch = document.getElementById('tana-match-rev');
    const elMatchSub = document.getElementById('tana-match-sub');
    const elGross = document.getElementById('tana-gross-rev');
    const elGrossSub = document.getElementById('tana-gross-sub');
    const elPrize = document.getElementById('tana-prize-cost');
    const elNet = document.getElementById('tana-net-profit');
    const elMargin = document.getElementById('tana-net-margin');

    if (elEntry) elEntry.innerHTML = `${(analytics.entry_revenue_projected || 6400).toLocaleString()} <span class="tak-curr">ETB</span>`;
    if (elEntrySub) elEntrySub.textContent = `${analytics.max_players || 32} players × ${analytics.entry_fee_etb || 200} ETB`;

    if (elMatch) elMatch.innerHTML = `${(analytics.match_revenue_projected || 3125).toLocaleString()} <span class="tak-curr">ETB</span>`;
    if (elMatchSub) elMatchSub.textContent = `${analytics.total_matches_projected || 125} games × ${analytics.loser_match_fee_etb || 25} ETB (loser pays)`;

    if (elGross) elGross.innerHTML = `${(analytics.gross_revenue_projected || 9525).toLocaleString()} <span class="tak-curr">ETB</span>`;
    if (elGrossSub) elGrossSub.textContent = `Entrance + Match loser fees`;

    if (elPrize) elPrize.innerHTML = `${(analytics.prize_pool_expense || 2500).toLocaleString()} <span class="tak-curr">ETB</span>`;

    if (elNet) elNet.innerHTML = `${(analytics.net_owner_profit_projected || 7025).toLocaleString()} <span class="tak-curr">ETB</span>`;
    if (elMargin) elMargin.textContent = `${analytics.profit_margin_percent || 73.8}% Net Lounge Profit Margin`;

    // Detailed Ledger Table Breakdown
    const tbody = document.getElementById('t-ledger-tbody');
    if (!tbody) return;

    const loserFee = analytics.loser_match_fee_etb || 25;
    const groupMatchesCount = analytics.group_stage_games || 96;
    const koMatchesCount = analytics.knockout_stage_games || 29;

    const groupMatchRev = groupMatchesCount * loserFee;
    const koMatchRev = koMatchesCount * loserFee;

    const ledgerRows = [
        {
            item: '1. Player Registration Entrance Fees',
            rate: `${analytics.entry_fee_etb || 200} ETB / player`,
            volume: `${analytics.max_players || 32} Players`,
            proj: `${(analytics.entry_revenue_projected || 6400).toLocaleString()} ETB`,
            collected: `${(analytics.entry_revenue_collected || 0).toLocaleString()} ETB`,
            status: analytics.entry_revenue_collected >= analytics.entry_revenue_projected ? '✓ FULLY COLLECTED' : 'ACCUMULATING'
        },
        {
            item: '2. Champions League Group Stage Matches (Loser Pays)',
            rate: `${loserFee} ETB / match`,
            volume: `${groupMatchesCount} Games`,
            proj: `${groupMatchRev.toLocaleString()} ETB`,
            collected: `${Math.min(groupMatchRev, (analytics.match_revenue_collected || 0)).toLocaleString()} ETB`,
            status: 'PER-MATCH CASH'
        },
        {
            item: '3. Knockout Stage Matches (Loser Pays)',
            rate: `${loserFee} ETB / match`,
            volume: `${koMatchesCount} Games`,
            proj: `${koMatchRev.toLocaleString()} ETB`,
            collected: `${Math.max(0, (analytics.match_revenue_collected || 0) - groupMatchRev).toLocaleString()} ETB`,
            status: 'PER-MATCH CASH'
        },
        {
            item: '4. Gross Tournament Revenue Pool',
            rate: 'Entrance + Matches',
            volume: '125 Total Games',
            proj: `${(analytics.gross_revenue_projected || 9525).toLocaleString()} ETB`,
            collected: `${(analytics.gross_revenue_collected || 0).toLocaleString()} ETB`,
            status: 'GROSS CASH'
        },
        {
            item: '5. 1st Place Champion Cash Prize (Lounge Expense)',
            rate: 'Guaranteed 1st',
            volume: '1 Champion',
            proj: '-2,000 ETB',
            collected: '-2,000 ETB',
            status: 'PRIZE ESCROW'
        },
        {
            item: '6. 2nd Place Runner-Up Cash Prize (Lounge Expense)',
            rate: 'Guaranteed 2nd',
            volume: '1 Finalist',
            proj: '-500 ETB',
            collected: '-500 ETB',
            status: 'PRIZE ESCROW'
        },
        {
            item: '7. NET LOUNGE OWNER PROFIT POCKETED',
            rate: '~73.8% Margin',
            volume: 'Net Take-Home',
            proj: `+${(analytics.net_owner_profit_projected || 7025).toLocaleString()} ETB`,
            collected: `+${(analytics.net_owner_profit_collected || 0).toLocaleString()} ETB`,
            status: '★ OWNER POCKET'
        }
    ];

    tbody.innerHTML = ledgerRows.map((row, idx) => {
        const isHighlight = idx === 6;
        const isExpense = row.proj.startsWith('-');
        return `
            <tr style="${isHighlight ? 'background: rgba(16,185,129,0.12); font-weight:700;' : ''}">
                <td style="color:${isHighlight ? 'var(--emerald)' : 'var(--text-primary)'};">${escapeHtml(row.item)}</td>
                <td style="color:var(--text-secondary);">${escapeHtml(row.rate)}</td>
                <td style="color:var(--text-secondary);">${escapeHtml(row.volume)}</td>
                <td style="color:${isHighlight ? 'var(--emerald)' : (isExpense ? 'var(--rose)' : 'var(--electric)')}; font-weight:700;">${escapeHtml(row.proj)}</td>
                <td style="color:var(--text-primary); font-weight:600;">${escapeHtml(row.collected)}</td>
                <td>
                    <span class="badge ${isHighlight ? 'badge-gold' : (isExpense ? 'badge-rose' : 'badge-cyan')}">${escapeHtml(row.status)}</span>
                </td>
            </tr>
        `;
    }).join('');
}

// ----------------------------------------------------------------------------
// 10. DOM EVENT INITIALIZATION & MODAL BINDINGS
// ----------------------------------------------------------------------------
document.addEventListener('DOMContentLoaded', () => {
    // Custom club toggle
    const clubSelect = document.getElementById('reg-player-club');
    const customClubField = document.getElementById('reg-custom-club-field');
    if (clubSelect && customClubField) {
        clubSelect.addEventListener('change', () => {
            customClubField.style.display = clubSelect.value === 'Other / Custom' ? 'block' : 'none';
        });
    }

    // Close tournament modals on backdrop click
    const tourModals = [
        'modal-create-event',
        'modal-register-tourn-player',
        'modal-match-score-entry',
        'modal-match-schedule-lock'
    ];
    tourModals.forEach(id => {
        const modal = document.getElementById(id);
        if (modal) {
            modal.addEventListener('click', (e) => {
                if (e.target === modal) modal.classList.remove('open');
            });
        }
    });

    // Update calc on init
    try { updateTournModalCalc(); } catch (e) {}
});


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
