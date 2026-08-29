/*
 * sar-store.js
 * ============
 * Shared SAR change-detection result store for the GeoPulse frontend suite.
 *
 * Design goals (see Explorer integration brief):
 *   1. sessionStorage holds ONLY compact, JSON-safe metadata — never base64 imagery.
 *   2. Full-resolution base64 previews live in JS memory for the current page.
 *   3. Previews that must survive navigation (Studio / Analytics / Telemetry) go
 *      into IndexedDB, which has a far larger quota than Web Storage.
 *   4. Persistence must NEVER turn a successful inference into a failure. Every
 *      write path is wrapped and degrades gracefully:
 *        - sessionStorage throws (quota/unavailable)  -> caller keeps live result
 *        - IndexedDB unavailable / write fails         -> in-memory previews remain
 *
 * This module is intentionally page-agnostic so other suite pages can include it
 * with a single <script src="assets/sar-store.js"></script> and read the shared
 * result without duplicating logic.
 */
(function (global) {
    'use strict';

    var SS_KEY = 'sar_results';       // compact metadata only
    var IDB_NAME = 'sar_intel';       // IndexedDB database
    var IDB_STORE = 'previews';       // object store for full-res previews
    var IDB_VERSION = 1;
    var PREVIEW_ID = 'latest';        // single-slot key for the most recent run

    // Full-resolution previews for the CURRENT page only. Lost on reload/navigation
    // unless IndexedDB persisted them successfully.
    var memoryPreviews = null;

    /**
     * Build a compact, JSON-safe metadata object from a raw API response.
     * Deliberately whitelists small scalar/array fields so base64 imagery can
     * never leak into sessionStorage.
     */
    function extractMetadata(data) {
        data = data || {};
        var regions = Array.isArray(data.regions) ? data.regions : [];
        var clusters = (typeof data.num_change_clusters === 'number')
            ? data.num_change_clusters
            : regions.length;

        return {
            version: 1,
            status: data.status || 'success',
            model: data.model_used != null ? data.model_used : null,
            threshold: data.threshold != null ? data.threshold : null,
            execution_time_sec: data.execution_time_sec != null ? data.execution_time_sec : null,
            total_pixels: data.total_pixels != null ? data.total_pixels : null,
            valid_pixels: data.valid_pixels != null ? data.valid_pixels : null,
            changed_pixels: data.changed_pixels != null ? data.changed_pixels : null,
            change_percentage: data.change_percentage != null ? data.change_percentage : null,
            num_change_clusters: clusters,
            total_changed_area_sq_km: data.total_changed_area_sq_km != null ? data.total_changed_area_sq_km : null,
            // Cluster / region metadata is small and useful cross-page.
            regions: regions,
            // Flags telling other pages which previews IndexedDB should hold.
            previews_available: {
                t1: !!data.t1_preview_base64,
                t2: !!data.t2_preview_base64,
                grayscale: !!data.t2_grayscale_base64,
                falsecolor: !!data.t2_false_color_base64,
                optical: !!data.optical_base64,
                boxes: !!(data.change_boxes_base64 || data.optical_boxes_base64),
                mask: !!data.change_mask_base64,
                heatmap: !!data.confidence_heatmap_base64,
                overlay: !!data.overlay_base64
            },
            saved_at: Date.now()
        };
    }

    /* ---------------------------- IndexedDB layer ---------------------------- */

    function openDB() {
        return new Promise(function (resolve, reject) {
            if (!global.indexedDB) {
                reject(new Error('IndexedDB unavailable'));
                return;
            }
            var req = global.indexedDB.open(IDB_NAME, IDB_VERSION);
            req.onupgradeneeded = function () {
                var db = req.result;
                if (!db.objectStoreNames.contains(IDB_STORE)) {
                    db.createObjectStore(IDB_STORE);
                }
            };
            req.onsuccess = function () { resolve(req.result); };
            req.onerror = function () { reject(req.error || new Error('IndexedDB open failed')); };
        });
    }

    function idbPut(previews) {
        return openDB().then(function (db) {
            return new Promise(function (resolve, reject) {
                var tx = db.transaction(IDB_STORE, 'readwrite');
                tx.objectStore(IDB_STORE).put(previews, PREVIEW_ID);
                tx.oncomplete = function () { db.close(); resolve(true); };
                tx.onerror = function () { db.close(); reject(tx.error || new Error('IndexedDB write failed')); };
                tx.onabort = function () { db.close(); reject(tx.error || new Error('IndexedDB write aborted')); };
            });
        });
    }

    function idbGet() {
        return openDB().then(function (db) {
            return new Promise(function (resolve, reject) {
                var tx = db.transaction(IDB_STORE, 'readonly');
                var r = tx.objectStore(IDB_STORE).get(PREVIEW_ID);
                r.onsuccess = function () { db.close(); resolve(r.result || null); };
                r.onerror = function () { db.close(); reject(r.error || new Error('IndexedDB read failed')); };
            });
        });
    }

    function idbDelete() {
        return openDB().then(function (db) {
            return new Promise(function (resolve) {
                var tx = db.transaction(IDB_STORE, 'readwrite');
                tx.objectStore(IDB_STORE).delete(PREVIEW_ID);
                tx.oncomplete = function () { db.close(); resolve(); };
                tx.onerror = function () { db.close(); resolve(); };
            });
        });
    }

    /* --------------------------- API base configuration ---------------------- */
    // Single source of truth for the backend origin used by all suite pages.
    // Priority:  1) ?api= query param   2) localStorage['nrsc_api_base']   3) default
    var API_BASE_KEY = 'nrsc_api_base';
    var API_BASE_DEFAULT = global.location.protocol + '//' + global.location.hostname + ':8000';

    function getApiBase() {
        try {
            var q = new URLSearchParams(global.location.search).get('api');
            if (q) return q.replace(/\/+$/, '');
        } catch (e) { /* ignore */ }
        try {
            var stored = global.localStorage.getItem(API_BASE_KEY);
            if (stored) return stored.replace(/\/+$/, '');
        } catch (e) { /* ignore */ }
        return API_BASE_DEFAULT;
    }

    /* ------------------------------ Public API ------------------------------ */

    var SARStore = {
        /** Resolve the backend origin (see API base configuration above). */
        getApiBase: getApiBase,

        /**
         * Persist COMPACT metadata to sessionStorage. Synchronous and may throw
         * (quota / storage disabled) — callers MUST wrap this in try/catch and
         * treat failure as non-fatal. Returns the metadata object on success.
         */
        saveMetadata: function (data) {
            var meta = extractMetadata(data);
            // Guard: metadata is a whitelist of small fields, so JSON.stringify
            // here never serializes large image data.
            sessionStorage.setItem(SS_KEY, JSON.stringify(meta));
            return meta;
        },

        /** Read compact metadata back. Never throws — returns null on any issue. */
        loadMetadata: function () {
            try {
                var raw = sessionStorage.getItem(SS_KEY);
                return raw ? JSON.parse(raw) : null;
            } catch (e) {
                return null;
            }
        },

        /** Cache full-res previews in memory for the current page. */
        setMemoryPreviews: function (previews) { memoryPreviews = previews; },

        /** Synchronous accessor for the current page's in-memory previews. */
        getMemoryPreviews: function () { return memoryPreviews; },

        /**
         * Persist full-res previews to IndexedDB for cross-page use. Returns a
         * promise; callers should attach .catch() and treat rejection as
         * non-fatal (in-memory previews still serve the current page).
         */
        savePreviews: function (previews) {
            return idbPut(previews);
        },

        /**
         * Resolve previews for consumption: in-memory first (fast, current page),
         * falling back to IndexedDB (cross-page). Returns a promise resolving to
         * the previews object or null.
         */
        loadPreviews: function () {
            if (memoryPreviews) return Promise.resolve(memoryPreviews);
            return idbGet().catch(function () { return null; });
        },

        /** Clear all persisted result state. Best-effort, never throws. */
        clear: function () {
            try { sessionStorage.removeItem(SS_KEY); } catch (e) { /* ignore */ }
            memoryPreviews = null;
            return idbDelete().catch(function () { /* ignore */ });
        }
    };

    global.SARStore = SARStore;
})(window);
