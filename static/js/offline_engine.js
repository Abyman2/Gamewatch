/**
 * GAMEWATCH™ STANDALONE OFFLINE-FIRST ENGINE (Solution 2)
 * ========================================================
 * Provides complete functionality during full internet blackouts:
 * 1. Client-Side Database (IndexedDB)
 * 2. Optimistic Local State Engine
 * 3. Offline Action Outbox (Queue)
 * 4. Automatic Cloud Reconciliation on Reconnect
 */

class GameWatchOfflineEngine {
    constructor() {
        this.dbName = 'GameWatch_Offline_DB';
        this.dbVersion = 1;
        this.db = null;
        this.isOnline = navigator.onLine;
        this.isSyncing = false;
        this.pendingCount = 0;
        this.init();
    }

    async init() {
        try {
            await this.openDB();
            this.updatePendingCount();
            this.attachNetworkListeners();
            console.log('[GameWatch Offline] Engine initialized with IndexedDB');
        } catch (e) {
            console.warn('[GameWatch Offline] IndexedDB init fallback:', e);
        }
    }

    openDB() {
        return new Promise((resolve, reject) => {
            if (!window.indexedDB) {
                return reject(new Error('IndexedDB not supported'));
            }
            const request = indexedDB.open(this.dbName, this.dbVersion);

            request.onupgradeneeded = (event) => {
                const db = event.target.result;
                if (!db.objectStoreNames.contains('keyval')) {
                    db.createObjectStore('keyval', { keyPath: 'key' });
                }
                if (!db.objectStoreNames.contains('outbox')) {
                    const outboxStore = db.createObjectStore('outbox', { keyPath: 'id', autoIncrement: true });
                    outboxStore.createIndex('timestamp', 'timestamp', { unique: false });
                }
            };

            request.onsuccess = (event) => {
                this.db = event.target.result;
                resolve(this.db);
            };

            request.onerror = (event) => {
                reject(event.target.error);
            };
        });
    }

    // --- KEYVAL STORE (STATE CACHE) ---
    async setCachedState(state) {
        if (!this.db) return;
        return new Promise((resolve) => {
            try {
                const tx = this.db.transaction('keyval', 'readwrite');
                const store = tx.objectStore('keyval');
                store.put({ key: 'latest_state', value: state, timestamp: Date.now() });
                tx.oncomplete = () => resolve(true);
                tx.onerror = () => resolve(false);
            } catch (e) { resolve(false); }
        });
    }

    async getCachedState() {
        if (!this.db) return null;
        return new Promise((resolve) => {
            try {
                const tx = this.db.transaction('keyval', 'readonly');
                const store = tx.objectStore('keyval');
                const req = store.get('latest_state');
                req.onsuccess = () => resolve(req.result ? req.result.value : null);
                req.onerror = () => resolve(null);
            } catch (e) { resolve(null); }
        });
    }

    // --- OUTBOX STORE (ACTION QUEUE) ---
    async queueMutation(endpoint, payload, actionDescription) {
        if (!this.db) return;
        return new Promise((resolve, reject) => {
            try {
                const tx = this.db.transaction('outbox', 'readwrite');
                const store = tx.objectStore('outbox');
                const entry = {
                    endpoint,
                    method: 'POST',
                    payload,
                    actionDescription,
                    timestamp: Date.now(),
                    retries: 0
                };
                const req = store.add(entry);
                tx.oncomplete = () => {
                    this.updatePendingCount();
                    resolve(true);
                };
                tx.onerror = () => reject(tx.error);
            } catch (e) { reject(e); }
        });
    }

    async getOutboxItems() {
        if (!this.db) return [];
        return new Promise((resolve) => {
            try {
                const tx = this.db.transaction('outbox', 'readonly');
                const store = tx.objectStore('outbox');
                const req = store.getAll();
                req.onsuccess = () => resolve(req.result || []);
                req.onerror = () => resolve([]);
            } catch (e) { resolve([]); }
        });
    }

    async removeOutboxItem(id) {
        if (!this.db) return;
        return new Promise((resolve) => {
            try {
                const tx = this.db.transaction('outbox', 'readwrite');
                const store = tx.objectStore('outbox');
                store.delete(id);
                tx.oncomplete = () => {
                    this.updatePendingCount();
                    resolve(true);
                };
                tx.onerror = () => resolve(false);
            } catch (e) { resolve(false); }
        });
    }

    async updatePendingCount() {
        const items = await this.getOutboxItems();
        this.pendingCount = items.length;
        this.renderStatusBadge();
    }

    // --- NETWORK LISTENERS & AUTO REPLAY ---
    attachNetworkListeners() {
        window.addEventListener('online', () => {
            this.isOnline = true;
            this.renderStatusBadge();
            if (window.showToast) window.showToast('📶 Internet reconnected! Synchronizing queued transactions...');
            this.syncOutbox();
        });

        window.addEventListener('offline', () => {
            this.isOnline = false;
            this.renderStatusBadge();
            if (window.showToast) window.showToast('⚡ Operating in Offline-First mode. Actions saved to device.', 'warning');
        });

        // Periodic outbox synchronization check
        setInterval(() => {
            if (navigator.onLine && this.pendingCount > 0 && !this.isSyncing) {
                this.syncOutbox();
            }
        }, 6000);
    }

    async syncOutbox() {
        if (this.isSyncing) return;
        const items = await this.getOutboxItems();
        if (items.length === 0) return;

        this.isSyncing = true;
        this.renderStatusBadge();

        console.log(`[GameWatch Sync] Replaying ${items.length} queued action(s)...`);

        let successCount = 0;
        for (const item of items) {
            try {
                const res = await fetch(item.endpoint, {
                    method: item.method || 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(item.payload)
                });
                if (res.ok || res.status === 200 || res.status === 201) {
                    await this.removeOutboxItem(item.id);
                    successCount++;
                } else if (res.status === 400 || res.status === 404) {
                    // Fatal client error, discard to prevent blocking
                    await this.removeOutboxItem(item.id);
                } else {
                    // Server or network issue, stop and retry later
                    break;
                }
            } catch (e) {
                // Network still failing
                break;
            }
        }

        this.isSyncing = false;
        this.updatePendingCount();

        if (successCount > 0) {
            if (window.showToast) window.showToast(`✨ Successfully synced ${successCount} offline action(s) to cloud!`);
            if (window.fetchState) window.fetchState();
            if (window.fetchShiftStatus) window.fetchShiftStatus();
        }
    }

    // --- OPTIMISTIC LOCAL MUTATION ENGINES ---
    optimisticAddGame(tvId, reason) {
        if (!window.App || !App.state || !App.state.tvs) return;
        const tv = App.state.tvs.find(t => t.id === tvId);
        if (tv) {
            tv.completed_games = (tv.completed_games || 0) + 1;
            const rate = App.state.price_per_game || 25;
            tv.bill_etb = tv.completed_games * rate;
            if (window.renderTvList) window.renderTvList(App.state.tvs);
            this.setCachedState(App.state);
        }
    }

    optimisticDeductGame(tvId) {
        if (!window.App || !App.state || !App.state.tvs) return;
        const tv = App.state.tvs.find(t => t.id === tvId);
        if (tv) {
            tv.completed_games = Math.max(0, (tv.completed_games || 0) - 1);
            const rate = App.state.price_per_game || 25;
            tv.bill_etb = tv.completed_games * rate;
            if (window.renderTvList) window.renderTvList(App.state.tvs);
            this.setCachedState(App.state);
        }
    }

    optimisticResetMatch(tvId) {
        if (!window.App || !App.state || !App.state.tvs) return;
        const tv = App.state.tvs.find(t => t.id === tvId);
        if (tv) {
            tv.clock = '00:00';
            tv.score = '0-0';
            tv.state = 'WAITING';
            if (window.renderTvList) window.renderTvList(App.state.tvs);
            this.setCachedState(App.state);
        }
    }

    optimisticCheckout(tvId, paymentMethod, amountReceived) {
        if (!window.App || !App.state || !App.state.tvs) return;
        const tv = App.state.tvs.find(t => t.id === tvId);
        if (tv) {
            tv.completed_games = 0;
            tv.bill_etb = 0;
            tv.clock = '00:00';
            tv.score = '0-0';
            tv.customer_name = 'Available Station';
            tv.state = 'WAITING';
            if (window.renderTvList) window.renderTvList(App.state.tvs);
            this.setCachedState(App.state);
        }
    }

    // --- VISUAL TELEMETRY BADGE ---
    renderStatusBadge() {
        let badge = document.getElementById('offline-engine-badge');
        if (!badge) {
            const container = document.querySelector('.header-right') || document.querySelector('.nav-right');
            if (container) {
                badge = document.createElement('div');
                badge.id = 'offline-engine-badge';
                badge.className = 'offline-badge-pill';
                container.prepend(badge);
            }
        }
        if (!badge) return;

        if (this.isSyncing) {
            badge.className = 'offline-badge-pill syncing';
            badge.innerHTML = `<span>🔄</span> <span>Syncing (${this.pendingCount})...</span>`;
        } else if (!navigator.onLine || !this.isOnline) {
            badge.className = 'offline-badge-pill offline';
            badge.innerHTML = `<span>⚡</span> <span>Offline Mode (${this.pendingCount} queued)</span>`;
        } else if (this.pendingCount > 0) {
            badge.className = 'offline-badge-pill pending';
            badge.innerHTML = `<span>⏳</span> <span>Pending Sync (${this.pendingCount})</span>`;
        } else {
            badge.className = 'offline-badge-pill online';
            badge.innerHTML = `<span>☁</span> <span>Cloud Connected</span>`;
        }
    }
}

// Global Singleton Instance
window.offlineEngine = new GameWatchOfflineEngine();
