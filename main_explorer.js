
    (function() {
        const map = document.querySelector('#map-parallax-container');
        const roiBox = document.querySelector('#demo-bbox > div');
        const areaBadge = roiBox.querySelector('span');
        const btnCheckAvail = document.getElementById('btn-check-availability');
        const runBtn = document.getElementById('btn-run-live');
        const sweep = document.getElementById('radar-sweep');
        const thresholdInput = document.getElementById('processing-threshold');
        const thresholdVal = document.getElementById('threshold-val');

        if (thresholdInput && thresholdVal) {
            thresholdInput.addEventListener('input', (e) => {
                thresholdVal.innerText = parseFloat(e.target.value).toFixed(2);
            });
        }

        const modelSelect = document.getElementById('processing-model');
        if (modelSelect && thresholdInput && thresholdVal) {
            modelSelect.addEventListener('change', (e) => {
                const model = e.target.value;
                const newThreshold = model === 'changeformer_v6' ? '0.50' : '0.85';
                thresholdInput.value = newThreshold;
                thresholdVal.innerText = newThreshold;
            });
        }

        const terminal = document.getElementById('terminal-overlay');
        const logContent = document.getElementById('log-content');
        const hud = document.getElementById('map-hud-reticle');
        const DEFAULT_DETECTION_THRESHOLD = 0.60;

        // 1. ROI Box Interaction (Draggable)
        let isDragging = false;
        roiBox.addEventListener('mousedown', () => isDragging = true);
        window.addEventListener('mouseup', () => isDragging = false);
        map.addEventListener('mousemove', (e) => {
            if (isDragging) {
                const rect = map.getBoundingClientRect();
                const x = ((e.clientX - rect.left) / rect.width) * 100;
                const y = ((e.clientY - rect.top) / rect.height) * 100;
                roiBox.style.left = `${Math.max(0, Math.min(x - 20, 60))}%`;
                roiBox.style.top = `${Math.max(0, Math.min(y - 17, 65))}%`;
                const area = (parseFloat(roiBox.style.width || 40) * parseFloat(roiBox.style.height || 35) * 0.03).toFixed(1);
                if (areaBadge) areaBadge.innerText = `Area: ${area} km²`;
            }
            // HUD Reticle
            hud.classList.remove('hidden');
            hud.style.left = `${e.clientX}px`;
            hud.style.top = `${e.clientY}px`;
            document.getElementById('hud-lat').innerText = `X: ${e.clientX}`;
            document.getElementById('hud-lng').innerText = `Y: ${e.clientY}`;
        });

        // Mode Toggle
        const modeLive = document.getElementById('mode-live');
        const modeUpload = document.getElementById('mode-upload');
        const modeDemo = document.getElementById('mode-demo');
        const liveInputs = document.getElementById('live-inputs');
        const uploadInputs = document.getElementById('upload-inputs');
        const demoInputs = document.getElementById('demo-inputs');
        let currentMode = 'live';

        modeLive.addEventListener('click', () => {
            currentMode = 'live';
            modeLive.className = 'text-[10px] font-mono text-primary border border-primary px-2 py-1 bg-primary/10';
            modeUpload.className = 'text-[10px] font-mono text-outline border border-outline px-2 py-1 hover:text-primary hover:border-primary';
            modeDemo.className = 'text-[10px] font-mono text-outline border border-outline px-2 py-1 hover:text-primary hover:border-primary';
            liveInputs.classList.remove('hidden');
            uploadInputs.classList.add('hidden');
            demoInputs.classList.add('hidden');
            if (currentSubMode === 'series') {
                btnCheckAvail.classList.remove('hidden');
                runBtn.classList.add('hidden');
                document.getElementById('btn-run-series').classList.add('hidden');
            }
        });

        modeUpload.addEventListener('click', () => {
            currentMode = 'upload';
            modeUpload.className = 'text-[10px] font-mono text-primary border border-primary px-2 py-1 bg-primary/10';
            modeLive.className = 'text-[10px] font-mono text-outline border border-outline px-2 py-1 hover:text-primary hover:border-primary';
            modeDemo.className = 'text-[10px] font-mono text-outline border border-outline px-2 py-1 hover:text-primary hover:border-primary';
            uploadInputs.classList.remove('hidden');
            liveInputs.classList.add('hidden');
            demoInputs.classList.add('hidden');
            document.getElementById('btn-run-series').classList.add('hidden');
        });

        modeDemo.addEventListener('click', () => {
            currentMode = 'demo';
            modeDemo.className = 'text-[10px] font-mono text-primary border border-primary px-2 py-1 bg-primary/10';
            modeLive.className = 'text-[10px] font-mono text-outline border border-outline px-2 py-1 hover:text-primary hover:border-primary';
            modeUpload.className = 'text-[10px] font-mono text-outline border border-outline px-2 py-1 hover:text-primary hover:border-primary';
            demoInputs.classList.remove('hidden');
            liveInputs.classList.add('hidden');
            uploadInputs.classList.add('hidden');
            
            btnCheckAvail.classList.add('hidden');
            runBtn.classList.remove('hidden');
            document.getElementById('btn-run-series').classList.add('hidden');
            document.getElementById('btn-run-text').innerText = "Run Demo Intelligence";
        });
        
        modeLive.addEventListener('click', () => {
            currentMode = 'live';
            modeLive.className = 'text-[10px] font-mono text-primary border border-primary px-2 py-1 bg-primary/10';
            modeUpload.className = 'text-[10px] font-mono text-outline border border-outline px-2 py-1 hover:text-primary hover:border-primary';
            modeDemo.className = 'text-[10px] font-mono text-outline border border-outline px-2 py-1 hover:text-primary hover:border-primary';
            liveInputs.classList.remove('hidden');
            uploadInputs.classList.add('hidden');
            demoInputs.classList.add('hidden');
            
            btnCheckAvail.classList.remove('hidden');
            runBtn.classList.add('hidden');
            document.getElementById('btn-run-series').classList.add('hidden');
            document.getElementById('btn-run-text').innerText = "Run Live Intelligence";
        });

        // Sub-Mode Logic (Pairwise vs Series)
        let currentSubMode = 'pairwise';
        let lastInferenceResult = null;
        const submodePairwise = document.getElementById('submode-pairwise');
        const submodeSeries = document.getElementById('submode-series');
        const livePairwiseInputs = document.getElementById('live-pairwise-inputs');
        const liveSeriesInputs = document.getElementById('live-series-inputs');
        const availPairwiseInfo = document.getElementById('avail-pairwise-info');
        const availSeriesInfo = document.getElementById('avail-series-info');
        
        if (submodePairwise && submodeSeries) {
            submodePairwise.addEventListener('click', () => {
                currentSubMode = 'pairwise';
                submodePairwise.className = 'flex-1 text-[10px] font-mono text-primary border border-primary px-2 py-1 bg-primary/10';
                submodeSeries.className = 'flex-1 text-[10px] font-mono text-outline border border-outline px-2 py-1 hover:text-primary hover:border-primary';
                livePairwiseInputs.classList.remove('hidden');
                liveSeriesInputs.classList.add('hidden');
                availPairwiseInfo.classList.remove('hidden');
                availSeriesInfo.classList.add('hidden');
                document.getElementById('btn-run-series').classList.add('hidden');
                document.getElementById('availability-results').classList.add('hidden');
                btnCheckAvail.classList.remove('hidden');
                runBtn.classList.add('hidden');
            });
            
            submodeSeries.addEventListener('click', () => {
                currentSubMode = 'series';
                submodeSeries.className = 'flex-1 text-[10px] font-mono text-primary border border-primary px-2 py-1 bg-primary/10';
                submodePairwise.className = 'flex-1 text-[10px] font-mono text-outline border border-outline px-2 py-1 hover:text-primary hover:border-primary';
                liveSeriesInputs.classList.remove('hidden');
                livePairwiseInputs.classList.add('hidden');
                availSeriesInfo.classList.remove('hidden');
                availPairwiseInfo.classList.add('hidden');
                runBtn.classList.add('hidden');
                document.getElementById('btn-run-series').classList.add('hidden');
                document.getElementById('availability-results').classList.add('hidden');
                btnCheckAvail.classList.remove('hidden');
            });
        }

        // Location Presets
        const LOCATION_PRESETS = {
            'india': { bbox: [77.10, 28.50, 77.30, 28.70] },
            'uk': { bbox: [-0.20, 51.40, 0.0, 51.60] },
            'us': { bbox: [-122.50, 37.70, -122.30, 37.85] },
            'japan': { bbox: [139.60, 35.60, 139.80, 35.80] },
            'australia': { bbox: [151.10, -33.95, 151.30, -33.80] }
        };

        const locSelect = document.getElementById('live-location-select');
        const customAoiUI = document.getElementById('live-custom-aoi');
        const cMinLon = document.getElementById('custom-min-lon');
        const cMaxLon = document.getElementById('custom-max-lon');
        const cMinLat = document.getElementById('custom-min-lat');
        const cMaxLat = document.getElementById('custom-max-lat');
        const customAoiError = document.getElementById('custom-aoi-error');

        if (locSelect) {
            locSelect.addEventListener('change', () => {
                if (locSelect.value === 'custom') {
                    customAoiUI.classList.remove('hidden');
                } else {
                    customAoiUI.classList.add('hidden');
                }
            });
        }
        
        function getLiveBBox() {
            if (locSelect.value === 'custom') {
                const minLon = parseFloat(cMinLon.value);
                const maxLon = parseFloat(cMaxLon.value);
                const minLat = parseFloat(cMinLat.value);
                const maxLat = parseFloat(cMaxLat.value);
                
                if (isNaN(minLon) || isNaN(maxLon) || isNaN(minLat) || isNaN(maxLat)) return null;
                if (minLon < -180 || maxLon > 180 || minLat < -90 || maxLat > 90) return null;
                if (minLon >= maxLon || minLat >= maxLat) return null;
                
                return { min_lon: minLon, min_lat: minLat, max_lon: maxLon, max_lat: maxLat };
            } else {
                const arr = LOCATION_PRESETS[locSelect.value].bbox;
                return { min_lon: arr[0], min_lat: arr[1], max_lon: arr[2], max_lat: arr[3] };
            }
        }
        
        function getLivePayload(isAvailability = false) {
            const bbox = getLiveBBox();
            if (!bbox) {
                if (customAoiError) {
                    customAoiError.classList.remove('hidden');
                    setTimeout(() => customAoiError.classList.add('hidden'), 3000);
                }
                return null;
            }
            
            const t1Input = document.getElementById('live-t1-date');
            const t2Input = document.getElementById('live-t2-date');
            const t1DateStr = t1Input ? t1Input.value : '2024-01-20';
            const t2DateStr = t2Input ? t2Input.value : '2024-06-20';
            
            // 14-day search window centered around the selected date
            const d1Center = new Date(t1DateStr);
            const d1Start = new Date(d1Center); d1Start.setDate(d1Center.getDate() - 7);
            const d1End = new Date(d1Center); d1End.setDate(d1Center.getDate() + 7);
            
            const d2Center = new Date(t2DateStr);
            const d2Start = new Date(d2Center); d2Start.setDate(d2Center.getDate() - 7);
            const d2End = new Date(d2Center); d2End.setDate(d2Center.getDate() + 7);
            
            const fmtDate = (d) => d.toISOString().split('T')[0];
            
            const resSelect = document.getElementById('processing-resolution');
            const modSelect = document.getElementById('processing-model');
            const resVal = resSelect ? parseInt(resSelect.value) : 512;
            let modelStr = modSelect ? modSelect.value : 'snunet';
            if (modelStr === 'snunet') modelStr = 'snunet_cd_sar';
            const threshVal = thresholdInput ? parseFloat(thresholdInput.value) : DEFAULT_DETECTION_THRESHOLD;
            
            if (currentSubMode === 'series') {
                const sStart = document.getElementById('live-series-start') ? document.getElementById('live-series-start').value : '2024-01-01';
                const sEnd = document.getElementById('live-series-end') ? document.getElementById('live-series-end').value : '2024-06-30';
                const sMax = document.getElementById('live-series-max') ? parseInt(document.getElementById('live-series-max').value) : 6;
                return {
                    bbox: bbox,
                    date_range: [sStart, sEnd],
                    resolution: [resVal, resVal],
                    max_scenes: sMax,
                    model_name: modelStr,
                    threshold: threshVal,
                    min_region_area_px: 10
                };
            } else {
                return {
                    bbox: bbox,
                    date_range_t1: [fmtDate(d1Start), fmtDate(d1End)],
                    date_range_t2: [fmtDate(d2Start), fmtDate(d2End)],
                    resolution: [resVal, resVal],
                    model_name: modelStr,
                    threshold: threshVal,
                    min_region_area_px: 10
                };
            }
        }
        
        const addLog = (msg, level) => {
            const div = document.createElement('div');
            const prefix = level === 'error' ? '[FAILED] ' : level === 'warn' ? '[WARN] ' : '';
            div.innerText = `> ${prefix}${msg}`;
            if (level === 'success') div.className = 'text-primary font-bold';
            else if (level === 'warn') div.className = 'text-yellow-400';
            else if (level === 'error') div.className = 'text-red-400 font-bold mt-2';
            else div.className = 'text-primary/80';
            logContent.appendChild(div);
            logContent.scrollTop = logContent.scrollHeight;
        };

        if (btnCheckAvail) {
            btnCheckAvail.addEventListener('click', async () => {
                const payload = getLivePayload(true);
                if (!payload) return;
                
                btnCheckAvail.disabled = true;
                btnCheckAvail.classList.add('opacity-50');
                
                const availResults = document.getElementById('availability-results');
                const availMsg = document.getElementById('availability-msg');
                availResults.classList.remove('hidden');
                availMsg.innerText = "Checking CDSE for acquisitions...";
                availMsg.className = "font-mono text-[10px] uppercase tracking-widest text-outline";
                document.getElementById('avail-t1-date').innerText = "...";
                document.getElementById('avail-t2-date').innerText = "...";
                document.getElementById('avail-scenes-count').innerText = "...";
                runBtn.classList.add('hidden');
                document.getElementById('btn-run-series').classList.add('hidden');
                
                try {
                    const apiBase = (window.SARStore && SARStore.getApiBase) ? SARStore.getApiBase() : 'http://127.0.0.1:8000';
                    const endpoint = currentSubMode === 'series' ? '/api/v1/detect/timeseries-availability' : '/api/v1/detect/availability';
                    const res = await fetch(apiBase + endpoint, {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify(payload)
                    });
                    
                    if (!res.ok) {
                        const err = await res.json().catch(() => ({}));
                        throw new Error(err.detail || "No Sentinel-1 acquisition found for this area/date window.");
                    }
                    
                    const data = await res.json();
                    availMsg.innerText = "SATELLITE SCENES FOUND";
                    availMsg.className = "font-mono text-[10px] uppercase tracking-widest text-primary";
                    
                    if (currentSubMode === 'series') {
                        document.getElementById('avail-scenes-count').innerText = `${data.acquisitions_found} scenes`;
                        document.getElementById('btn-run-series').classList.remove('hidden');
                    } else {
                        document.getElementById('avail-t1-date').innerText = data.t1_scene.acquisition_date;
                        document.getElementById('avail-t2-date').innerText = data.t2_scene.acquisition_date;
                        runBtn.classList.remove('hidden');
                    }
                    
                } catch (e) {
                    availMsg.innerText = e.message;
                    availMsg.className = "font-mono text-[10px] uppercase tracking-widest text-[#ff453a]";
                    document.getElementById('avail-t1-date').innerText = "--";
                    document.getElementById('avail-t2-date').innerText = "--";
                    document.getElementById('avail-scenes-count').innerText = "--";
                } finally {
                    btnCheckAvail.disabled = false;
                    btnCheckAvail.classList.remove('opacity-50');
                }
            });
        }

        // Drag and Drop Logic
        const setupDropzone = (dropzoneId, inputId, labelId) => {
            const dropzone = document.getElementById(dropzoneId);
            const input = document.getElementById(inputId);
            const label = document.getElementById(labelId);

            dropzone.addEventListener('click', () => input.click());
            
            input.addEventListener('change', () => {
                if (input.files.length > 0) {
                    label.innerText = input.files[0].name;
                    dropzone.classList.add('border-primary');
                    dropzone.classList.replace('bg-surface-container-low/30', 'bg-primary/5');
                }
            });

            dropzone.addEventListener('dragover', (e) => {
                e.preventDefault();
                dropzone.classList.add('border-primary', 'bg-primary/10');
            });

            dropzone.addEventListener('dragleave', () => {
                dropzone.classList.remove('border-primary', 'bg-primary/10');
            });

            dropzone.addEventListener('drop', (e) => {
                e.preventDefault();
                dropzone.classList.remove('border-primary', 'bg-primary/10');
                if (e.dataTransfer.files.length > 0) {
                    input.files = e.dataTransfer.files;
                    label.innerText = input.files[0].name;
                    dropzone.classList.add('border-primary');
                    dropzone.classList.replace('bg-surface-container-low/30', 'bg-primary/5');
                }
            });
        };

        setupDropzone('dropzone-t1', 't1-file', 't1-filename');
        setupDropzone('dropzone-t2', 't2-file', 't2-filename');
        
        const runSeriesBtn = document.getElementById('btn-run-series');
        if (runSeriesBtn) {
            runSeriesBtn.addEventListener('click', async () => {
                let sentinelPayload = getLivePayload(false);
                if (!sentinelPayload) {
                    addLog('Invalid geographic bounds selected.', 'error');
                    terminal.classList.add('hidden');
                    return;
                }
                
                terminal.classList.remove('hidden');
                logContent.innerHTML = '';
                addLog('Initializing Time-Series SAR Intelligence...');
                addLog(`Date Range: ${sentinelPayload.date_range[0]} to ${sentinelPayload.date_range[1]}`);
                addLog(`Max Scenes: ${sentinelPayload.max_scenes}`);
                
                const sweepAnim = sweep.animate([{ left: '0%' }, { left: '100%' }], { duration: 2400, iterations: Infinity });
                try {
                    const apiBase = (window.SARStore && SARStore.getApiBase) ? SARStore.getApiBase() : 'http://127.0.0.1:8000';
                    const fetchUrl = apiBase + '/api/v1/detect/timeseries';
                    
                    // We need a long timeout for time series because it can take minutes
                    addLog('Awaiting CDSE catalog fetch and PyTorch inference (this may take a while)...');
                    
                    const res = await fetch(fetchUrl, {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify(sentinelPayload)
                    });
                    
                    if (!res.ok) {
                        const err = await res.json().catch(() => ({}));
                        throw new Error(err.detail || `Server error: ${res.status}`);
                    }
                    const data = await res.json();
                    addLog('Time-Series Inference Complete.', 'success');
                    
                    // Save to SARStore
                    if (window.SARStore) {
                        try {
                            SARStore.saveTimeSeries(data);
                        } catch (storageError) {
                            console.warn('Result persistence failed', storageError);
                        }
                    }
                    
                    // Redirect to analytics page
                    window.location.href = 'analytics.html';
                } catch (e) {
                    addLog(e.message, 'error');
                } finally {
                    if (sweepAnim) sweepAnim.cancel();
                }
            });
        }

        // 2. Radar Sweep Trigger
        runBtn.addEventListener('click', async () => {
            let t1File, t2File;
            let sentinelPayload = null;

            // Show terminal log early
            terminal.classList.remove('hidden');
            logContent.innerHTML = ''; // clear old logs

            // terminal UI cleanup is handled by addLog which is now in higher scope

            if (currentMode === 'live') {
                addLog('Initializing Live Sentinel-1 Intelligence...');
                sentinelPayload = getLivePayload(false);
                if (!sentinelPayload) {
                    addLog('Invalid geographic bounds selected.', 'error');
                    terminal.classList.add('hidden');
                    return;
                }
            } else if (currentMode === 'upload') {
                const t1Input = document.getElementById('t1-file');
                const t2Input = document.getElementById('t2-file');
                
                if (!t1Input.files.length || !t2Input.files.length) {
                    alert('Please select both T1 and T2 images for intelligence sweep.');
                    terminal.classList.add('hidden');
                    return;
                }
                
                t1File = t1Input.files[0];
                t2File = t2Input.files[0];
                
                addLog('Initializing Upload Uplink...');
            } else if (currentMode === 'demo') {
                const scene = document.getElementById('demo-scene-select').value;
                // We assume demo_samples folder is hosted at /assets/demo_samples/
                const baseUrl = `assets/demo_samples/${scene}`;
                const isOptical = scene.startsWith('sample_');
                const ext = isOptical ? 'png' : 'tif';
                const mime = isOptical ? 'image/png' : 'image/tiff';
                
                addLog(`Downloading Demo Scene: ${scene}...`);
                try {
                    // Try exact case first (T1.png/T2.png), fallback to lowercase (t1.tif/t2.tif)
                    let t1Res = await fetch(`${baseUrl}/T1.${ext}`);
                    let t2Res = await fetch(`${baseUrl}/T2.${ext}`);
                    
                    if (!t1Res.ok || !t2Res.ok) {
                        t1Res = await fetch(`${baseUrl}/t1.${ext}`);
                        t2Res = await fetch(`${baseUrl}/t2.${ext}`);
                    }
                    
                    if (!t1Res.ok || !t2Res.ok) throw new Error('Demo assets not found locally.');
                    
                    const t1Blob = await t1Res.blob();
                    const t2Blob = await t2Res.blob();
                    
                    t1File = new File([t1Blob], `t1.${ext}`, { type: mime });
                    t2File = new File([t2Blob], `t2.${ext}`, { type: mime });
                    addLog('Demo scene acquired successfully.', 'success');
                } catch (e) {
                    addLog(e.message, 'error');
                    return;
                }
            }

            addLog('Sending payload to inference engine...');
            
            // Start sweep animation looping
            const sweepAnim = sweep.animate([{ left: '0%' }, { left: '100%' }], { duration: 2400, iterations: Infinity });
            let hasError = false;

            try {
                const apiBase = (window.SARStore && SARStore.getApiBase) ? SARStore.getApiBase() : 'http://127.0.0.1:8000';
                
                let fetchUrl, fetchOpts;
                if (currentMode === 'live') {
                    fetchUrl = apiBase + '/api/v1/detect/sentinel';
                    fetchOpts = {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify(sentinelPayload)
                    };
                } else {
                    const formData = new FormData();
                    formData.append('image_t1', t1File);
                    formData.append('image_t2', t2File);
                    const thresh = document.getElementById('processing-threshold')?.value || "0.95";
                    formData.append('threshold', thresh.toString());
                    formData.append('min_region_area_px', '100');

                    const pModel = document.getElementById('processing-model');
                    if (pModel && pModel.value === 'changeformer_v6') {
                        formData.append('model_name', 'changeformer_v6');
                        fetchUrl = apiBase + '/api/v1/detect/upload';
                    } else {
                        fetchUrl = apiBase + '/api/v1/detect/change-detection';
                    }

                    fetchOpts = {
                        method: 'POST',
                        body: formData
                    };
                }
                
                const res = await fetch(fetchUrl, fetchOpts);
                
                if (!res.ok) {
                    const err = await res.json().catch(() => ({}));
                    throw new Error(err.detail || `Server error: ${res.status}`);
                }
                
                const data = await res.json();
                lastInferenceResult = data;

                // Successful API + inference -> success (green) state.
                addLog('Inference Complete.', 'success');
                addLog(`Detected ${data.num_change_clusters != null ? data.num_change_clusters : (Array.isArray(data.regions) ? data.regions.length : 0)} clusters.`, 'success');

                /* ---------------------------------------------------------------
                 * STEP 1 — RENDER THE REAL RESULTS FIRST.
                 * This runs BEFORE and INDEPENDENTLY of any persistence, so a
                 * storage failure can never prevent the live result from showing.
                 * ------------------------------------------------------------- */

                // Normalize base64 (or already-prefixed data URL) into a src, or null.
                const toDataURL = (b64) => {
                    if (!b64) return null;
                    const s = String(b64);
                    return s.startsWith('data:') ? s : 'data:image/png;base64,' + s;
                };

                // Full-resolution previews held in JS memory for the current page.
                const livePreviews = {
                    t1: toDataURL(data.t1_preview_base64),
                    t2: toDataURL(data.t2_preview_base64),
                    grayscaleT1: toDataURL(data.t1_grayscale_base64),
                    grayscaleT2: toDataURL(data.t2_grayscale_base64),
                    falseColorT1: toDataURL(data.t1_false_color_base64),
                    falseColorT2: toDataURL(data.t2_false_color_base64),
                    optical: toDataURL(data.optical_base64),
                    opticalBoxes: toDataURL(data.optical_boxes_base64),
                    boxes: toDataURL(data.change_boxes_base64),
                    mask: toDataURL(data.change_mask_base64),
                    heatmap: toDataURL(data.confidence_heatmap_base64),
                    overlay: toDataURL(data.overlay_base64)
                };

                // Remove the fake demo bounding box; reveal the real result panels.
                const demoBox = document.getElementById('demo-bbox');
                if (demoBox) demoBox.style.display = 'none';
                const overlayContainer = document.getElementById('result-overlay-container');
                if (overlayContainer) overlayContainer.style.display = 'block';
                const resultsPanel = document.getElementById('results-panel');
                if (resultsPanel) resultsPanel.classList.remove('hidden');

                // Metrics (defensive: never crash on a missing/oddly-typed field).
                const setText = (id, val) => { const el = document.getElementById(id); if (el) el.innerText = val; };
                const fmtInt = (n) => (typeof n === 'number' && isFinite(n)) ? n.toLocaleString() : '--';
                setText('metric-time', (typeof data.execution_time_sec === 'number') ? `${data.execution_time_sec.toFixed(2)} s` : '-- s');
                setText('metric-total', fmtInt(data.total_pixels));
                setText('metric-changed', fmtInt(data.changed_pixels));
                setText('metric-percent', (typeof data.change_percentage === 'number') ? `${data.change_percentage}%` : '--');
                setText('metric-clusters', (data.num_change_clusters != null) ? data.num_change_clusters
                    : (Array.isArray(data.regions) ? data.regions.length : '--'));

                // TEMPORARY DEBUG readout — Model 3 binary change mask.
                // All values come straight from the API response; the threshold shown
                // is the exact one inference ran with (never recomputed/modified here).
                const dbgPanel = document.getElementById('mask-debug-panel');
                if (dbgPanel) dbgPanel.classList.remove('hidden');
                setText('dbg-changed', fmtInt(data.changed_pixels));
                setText('dbg-valid', fmtInt(data.valid_pixels != null ? data.valid_pixels : data.total_pixels));
                setText('dbg-change', (typeof data.change_percentage === 'number') ? `${data.change_percentage}%` : '--');
                setText('dbg-threshold', (data.threshold != null) ? data.threshold : '--');
                setText('dbg-clusters', (data.num_change_clusters != null) ? data.num_change_clusters
                    : (Array.isArray(data.regions) ? data.regions.length : '--'));

                // Image viewer — only wire the views that actually have a preview.
                const resultImg = document.getElementById('result-img');
                const views = {
                    't1':         { src: livePreviews.t1,           btn: document.getElementById('view-t1') },
                    't2':         { src: livePreviews.t2,           btn: document.getElementById('view-t2') },
                    'optical':    { src: livePreviews.optical,      btn: document.getElementById('view-optical') },
                    'falsecolor': { src: livePreviews.falseColorT2, btn: document.getElementById('view-falsecolor') },
                    'heatmap':    { src: livePreviews.heatmap,      btn: document.getElementById('view-heatmap') },
                    'mask':       { src: livePreviews.mask,         btn: document.getElementById('view-mask') },
                    'overlay':    { src: livePreviews.overlay,      btn: document.getElementById('view-overlay') },
                    'boxes':      { src: livePreviews.opticalBoxes || livePreviews.boxes, btn: document.getElementById('view-boxes') }
                };
                const inactiveCls = 'bg-[#0a0a0a]/80 backdrop-blur-md border border-outline/30 px-3 py-1 text-xs font-mono text-outline hover:text-primary hover:border-primary/50';
                const activeCls   = 'bg-[#0a0a0a]/80 backdrop-blur-md border border-primary/50 px-3 py-1 text-xs font-mono text-primary';
                const disabledCls = 'bg-[#0a0a0a]/40 backdrop-blur-md border border-outline/20 px-3 py-1 text-xs font-mono text-outline/40 cursor-not-allowed';
                // The Binary Mask toggle keeps a distinct coral identity (matches the mask color).
                const maskInactiveCls = 'bg-[#0a0a0a]/80 backdrop-blur-md border border-[#ff453a]/50 px-3 py-1 text-xs font-mono text-[#ff453a] hover:border-[#ff453a]';
                const maskActiveCls   = 'bg-[#0a0a0a]/80 backdrop-blur-md border border-[#ff453a] px-3 py-1 text-xs font-mono text-[#ff453a] font-bold';
                // The Highlight (boxes) toggle keeps a distinct amber identity.
                const boxesInactiveCls = 'bg-[#0a0a0a]/80 backdrop-blur-md border border-[#ffb000]/50 px-3 py-1 text-xs font-mono text-[#ffb000] hover:border-[#ffb000]';
                const boxesActiveCls   = 'bg-[#0a0a0a]/80 backdrop-blur-md border border-[#ffb000] px-3 py-1 text-xs font-mono text-[#ffb000] font-bold';
                const maskCaption = document.getElementById('mask-debug-caption');

                const setView = (v) => {
                    const def = views[v];
                    if (!def || !def.src || !resultImg) return;
                    resultImg.src = def.src;
                    // DEBUG: when showing the exact backend binary mask, keep the
                    // sparse changed pixels crisp (no smoothing) and label it clearly.
                    if (v === 'mask') {
                        resultImg.style.imageRendering = 'pixelated';
                        if (maskCaption) maskCaption.classList.remove('hidden');
                    } else {
                        resultImg.style.imageRendering = 'auto';
                        if (maskCaption) maskCaption.classList.add('hidden');
                    }
                    Object.keys(views).forEach(k => {
                        const val = views[k];
                        if (!val.btn) return;
                        if (!val.src) { val.btn.className = disabledCls; return; }
                        if (k === 'mask') {
                            val.btn.className = (k === v) ? maskActiveCls : maskInactiveCls;
                        } else if (k === 'boxes') {
                            val.btn.className = (k === v) ? boxesActiveCls : boxesInactiveCls;
                        } else {
                            val.btn.className = (k === v) ? activeCls : inactiveCls;
                        }
                    });
                };

                // Generate bounding boxes overlay for ChangeFormerV6 using existing regions
                if (data.model_used === 'changeformer_v6' && Array.isArray(data.regions) && data.regions.length > 0) {
                    const baseSrc = livePreviews.overlay || livePreviews.mask || livePreviews.t2;
                    if (baseSrc) {
                        try {
                            const boxesDataUrl = await new Promise((resolve, reject) => {
                                const img = new Image();
                                img.crossOrigin = "Anonymous";
                                img.onload = () => {
                                    const canvas = document.createElement('canvas');
                                    canvas.width = img.width;
                                    canvas.height = img.height;
                                    const ctx = canvas.getContext('2d');
                                    ctx.drawImage(img, 0, 0);
                                    
                                    ctx.strokeStyle = '#ffb000'; // Amber highlight
                                    ctx.lineWidth = Math.max(2, Math.floor(img.width / 400));
                                    
                                    data.regions.forEach(r => {
                                        if (r.bbox_xy) {
                                            const [min_y, min_x, max_y, max_x] = r.bbox_xy;
                                            const w = max_x - min_x;
                                            const h = max_y - min_y;
                                            const pad = 4;
                                            ctx.strokeRect(min_x - pad, min_y - pad, w + 2*pad, h + 2*pad);
                                        }
                                    });
                                    resolve(canvas.toDataURL('image/png'));
                                };
                                img.onerror = reject;
                                img.src = baseSrc;
                            });
                            livePreviews.boxes = boxesDataUrl;
                            views['boxes'].src = boxesDataUrl;
                        } catch (e) {
                            console.warn("Failed to generate ChangeFormerV6 bounding boxes", e);
                        }
                    }
                }

                Object.keys(views).forEach(k => {
                    const val = views[k];
                    if (!val.btn) return;
                    if (val.src) {
                        val.btn.disabled = false;
                        val.btn.onclick = () => setView(k);
                    } else {
                        // Missing preview: disable the toggle instead of showing a broken image.
                        val.btn.disabled = true;
                        val.btn.onclick = null;
                        val.btn.className = disabledCls;
                    }
                });

                // Default to the highlighted changes; fall back to overlay, then any available preview.
                const preferred = ['boxes', 'overlay', 'mask', 'heatmap', 't2', 't1'].find(k => views[k] && views[k].src);
                if (preferred) {
                    setView(preferred);
                } else {
                    addLog('No preview imagery returned by API (showing metrics only).', 'warn');
                }

                /* ---------------------------------------------------------------
                 * STEP 2 — LIGHTWEIGHT PERSISTENCE (never fatal).
                 * The live result is already on screen; storage is best-effort.
                 * ------------------------------------------------------------- */

                // 2a. Compact metadata -> sessionStorage (no base64 imagery).
                try {
                    SARStore.saveMetadata(data);
                } catch (storageError) {
                    console.warn('Result persistence failed; continuing with live result', storageError);
                    addLog('Metadata not persisted (storage full/unavailable).', 'warn');
                }

                // 2b. Full-res previews -> memory now + IndexedDB for cross-page use.
                try {
                    SARStore.setMemoryPreviews(livePreviews);
                    SARStore.savePreviews(livePreviews).catch((idbError) => {
                        console.warn('Preview persistence failed; continuing with live result', idbError);
                        addLog('Preview cache skipped (IndexedDB unavailable).', 'warn');
                    });
                } catch (storageError) {
                    console.warn('Preview persistence failed; continuing with live result', storageError);
                }

            } catch (error) {
                // Only reached on actual API / inference failure.
                hasError = true;
                addLog(error && error.message ? error.message : 'Unknown inference error', 'error');
            } finally {
                sweepAnim.cancel();
                sweep.classList.add('hidden');
                if (!hasError) {
                    setTimeout(() => terminal.classList.add('hidden'), 5000);
                }
            }
        });

        const btnInterpret = document.getElementById('btn-interpret');
        const aiPanel = document.getElementById('ai-interpretations-panel');
        if (btnInterpret) {
            btnInterpret.addEventListener('click', async () => {
                if (!lastInferenceResult || !lastInferenceResult.regions || lastInferenceResult.regions.length === 0) {
                    addLog("No regions to analyze.", "warn");
                    return;
                }
                
                const apiBase = (window.SARStore && SARStore.getApiBase) ? SARStore.getApiBase() : 'http://127.0.0.1:8000';
                
                // Only analyze regions with high confidence
                const highConfRegions = lastInferenceResult.regions.filter(r => r.mean_change_prob >= 0.7);
                if (highConfRegions.length === 0) {
                    addLog("No high-confidence regions found for analysis.", "warn");
                    return;
                }
                
                const payload = {
                    t1_base64: lastInferenceResult.t1_preview_base64,
                    t2_base64: lastInferenceResult.t2_preview_base64,
                    regions: highConfRegions
                };
                
                btnInterpret.disabled = true;
                btnInterpret.innerHTML = '<span class="material-symbols-outlined text-[14px] animate-spin">refresh</span><span>Analyzing...</span>';
                aiPanel.classList.remove('hidden');
                aiPanel.innerHTML = '<div class="text-white/60 font-mono text-[10px] p-2 text-center">NVIDIA Nemotron is analyzing the scene...</div>';
                
                if (terminal) terminal.classList.remove('hidden');
                addLog(`Requesting semantic interpretation for ${highConfRegions.length} regions...`, 'info');
                
                try {
                    const res = await fetch(apiBase + '/api/v1/detect/interpret', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify(payload)
                    });
                    
                    if (!res.ok) {
                        const err = await res.json().catch(() => ({}));
                        throw new Error(err.detail || `Server error: ${res.status}`);
                    }
                    
                    const data = await res.json();
                    const interpretations = data.interpretations;
                    
                    aiPanel.innerHTML = '';
                    if (Object.keys(interpretations).length === 0) {
                        aiPanel.innerHTML = '<div class="text-white/60 font-mono text-[10px] p-2 text-center">No conclusive interpretations.</div>';
                        addLog('AI returned no conclusive interpretations.', 'warn');
                    } else {
                        let html = '';
                        Object.keys(interpretations).forEach(regId => {
                            const val = interpretations[regId];
                            
                            if (val.status === 'unavailable') {
                                html += `
                                <div class="bg-red-500/10 border border-red-500/30 p-2 rounded-lg">
                                    <div class="text-red-400 font-mono text-[10px] mb-1 font-bold">Region ${val.region_id}</div>
                                    <div class="text-white/60 text-[10px] font-sans">NVIDIA Nemotron Unavailable</div>
                                </div>`;
                                return;
                            }
                            
                            if (val.status === 'skipped_small_crop') {
                                html += `
                                <div class="bg-gray-500/10 border border-gray-500/30 p-2 rounded-lg">
                                    <div class="text-gray-400 font-mono text-[10px] mb-1 font-bold">Region ${val.region_id}</div>
                                    <div class="text-white/60 text-[10px] font-sans">Crop too small for analysis</div>
                                </div>`;
                                return;
                            }
                            
                            if (val.status === 'error' || val.status === 'malformed_response') {
                                html += `
                                <div class="bg-orange-500/10 border border-orange-500/30 p-2 rounded-lg">
                                    <div class="text-orange-400 font-mono text-[10px] mb-1 font-bold">Region ${val.region_id}</div>
                                    <div class="text-white/60 text-[10px] font-sans">Analysis failed</div>
                                </div>`;
                                return;
                            }

                            html += `
                            <div class="bg-purple-500/10 border border-purple-500/30 p-2 rounded-lg">
                                <div class="text-purple-400 font-mono text-[10px] mb-1 font-bold">Region ${val.region_id}</div>
                                <div class="text-white/90 text-[10px] font-sans">
                                    <div><span class="text-white/60">CHANGE:</span> ${val.category || "Unknown"}</div>
                                    <div><span class="text-white/60">CONFIDENCE:</span> ${val.visual_confidence || "Unknown"}</div>
                                    <div class="mt-1"><span class="text-white/60">EVIDENCE:</span><br/>${val.short_summary || "No description provided."}</div>
                                </div>
                            </div>
                            `;
                        });
                        if (!html) {
                            html = '<div class="text-white/60 font-mono text-[10px] p-2 text-center">All regions marked as uncertain.</div>';
                        }
                        aiPanel.innerHTML = html;
                        addLog('Nemotron analysis complete.', 'success');
                    }
                } catch (e) {
                    addLog(e.message, 'error');
                    aiPanel.innerHTML = `<div class="text-red-400 font-mono text-[10px] p-2">Failed: ${e.message}</div>`;
                } finally {
                    btnInterpret.disabled = false;
                    btnInterpret.innerHTML = '<span class="material-symbols-outlined text-[14px]">psychology</span><span>Analyze Changes with AI</span>';
                    setTimeout(() => { if(terminal) terminal.classList.add('hidden'); }, 3000);
                }
            });
        }

    })();


    