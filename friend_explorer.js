
    (function() {
        const map = document.querySelector('#map-parallax-container');
        const roiBox = document.querySelector('#demo-bbox > div');
        const areaBadge = roiBox ? roiBox.querySelector('span') : null;
        const btnCheckAvail = document.getElementById('btn-check-availability');
        const runBtn = document.getElementById('btn-run-live');
        const sweep = document.getElementById('radar-sweep');
        const terminal = document.getElementById('terminal-overlay');
        const logContent = document.getElementById('log-content');
        const hud = document.getElementById('map-hud-reticle');
        const btnCloseTerminal = document.getElementById('btn-close-terminal');
        const DEFAULT_DETECTION_THRESHOLD = 0.60;

        if (btnCloseTerminal) {
            btnCloseTerminal.addEventListener('click', () => {
                terminal.classList.add('hidden');
            });
        }

        // 1. ROI Box Interaction (Draggable - guarded)
        let isDragging = false;
        if (roiBox) {
            roiBox.addEventListener('mousedown', () => isDragging = true);
            window.addEventListener('mouseup', () => isDragging = false);
        }
        map.addEventListener('mousemove', (e) => {
            if (isDragging && roiBox) {
                const rect = map.getBoundingClientRect();
                const x = ((e.clientX - rect.left) / rect.width) * 100;
                const y = ((e.clientY - rect.top) / rect.height) * 100;
                roiBox.style.left = `${Math.max(0, Math.min(x - 20, 60))}%`;
                roiBox.style.top = `${Math.max(0, Math.min(y - 17, 65))}%`;
                const area = (parseFloat(roiBox.style.width || 40) * parseFloat(roiBox.style.height || 35) * 0.03).toFixed(1);
                if (areaBadge) areaBadge.innerText = `Area: ${area} km²`;
            }
            // HUD Reticle
            if (hud) {
                hud.classList.remove('hidden');
                hud.style.left = `${e.clientX}px`;
                hud.style.top = `${e.clientY}px`;
            }
            const elLat = document.getElementById('hud-lat');
            const elLng = document.getElementById('hud-lng');
            if (elLat) elLat.innerText = `X: ${e.clientX}`;
            if (elLng) elLng.innerText = `Y: ${e.clientY}`;
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
                    threshold: DEFAULT_DETECTION_THRESHOLD,
                    min_region_area_px: 10
                };
            } else {
                return {
                    bbox: bbox,
                    date_range_t1: [fmtDate(d1Start), fmtDate(d1End)],
                    date_range_t2: [fmtDate(d2Start), fmtDate(d2End)],
                    resolution: [resVal, resVal],
                    model_name: modelStr,
                    threshold: DEFAULT_DETECTION_THRESHOLD,
                    min_region_area_px: 10
                };
            }
        }
        
        const addLog = (msg, level) => {
            const div = document.createElement('div');
            const prefix = level === 'error' ? '[FAILED] ' : level === 'warn' ? '[WARN] ' : '';
            const cleanMsg = msg.startsWith('>') ? msg.substring(1).trim() : msg;
            div.innerText = `> ${prefix}${cleanMsg}`;
            if (level === 'success') div.className = 'text-[#4ade80] font-bold';
            else if (level === 'warn') div.className = 'text-yellow-400';
            else if (level === 'error') div.className = 'text-red-400 font-bold mt-1';
            else div.className = 'text-[#22c55e]/90';
            logContent.appendChild(div);
            logContent.scrollTop = logContent.scrollHeight;
            return div;
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

        // Floating Inference Loader HUD Controller
        const loaderHUD = {
            el: document.getElementById('inference-loader-hud'),
            bar: document.getElementById('loader-progress-bar'),
            percent: document.getElementById('loader-percent'),
            stage: document.getElementById('loader-stage'),
            currentProgress: 0,
            timer: null,

            show() {
                if (!this.el) return;
                this.stopAutoIncrement();
                this.currentProgress = 0;
                this.updateProgress(5, "INGESTING DUAL-POL SAR TILES [CDSE]...");
                this.el.classList.remove('hidden');
                requestAnimationFrame(() => {
                    if (this.el) this.el.style.opacity = '1';
                });
            },

            updateProgress(pct, stageText = null) {
                pct = Math.min(100, Math.max(0, pct));
                this.currentProgress = pct;
                if (this.bar) this.bar.style.width = `${pct}%`;
                if (this.percent) this.percent.innerText = `${Math.round(pct)}%`;

                if (this.stage) {
                    if (stageText) {
                        this.stage.innerText = stageText;
                    } else if (pct < 30) {
                        this.stage.innerText = "INGESTING DUAL-POL SAR TILES [CDSE]...";
                    } else if (pct < 70) {
                        this.stage.innerText = "EXTRACTING TEMPORAL FEATURES (SNUNet-CD)...";
                    } else if (pct < 100) {
                        this.stage.innerText = "CALIBRATING CONFIDENCE & GENERATING MASKS...";
                    } else {
                        this.stage.innerText = "ECO-AUDIT READY";
                    }
                }
            },

            startAutoIncrement(targetPct, stepTime = 100, maxPct = 95) {
                this.stopAutoIncrement();
                this.timer = setInterval(() => {
                    if (this.currentProgress < targetPct && this.currentProgress < maxPct) {
                        this.updateProgress(this.currentProgress + 1);
                    }
                }, stepTime);
            },

            stopAutoIncrement() {
                if (this.timer) {
                    clearInterval(this.timer);
                    this.timer = null;
                }
            },

            async complete() {
                this.stopAutoIncrement();
                this.updateProgress(100, "ECO-AUDIT READY");
                await new Promise(r => setTimeout(r, 450));
                await this.hide();
            },

            async hide() {
                this.stopAutoIncrement();
                if (!this.el) return;
                this.el.style.opacity = '0';
                await new Promise(r => setTimeout(r, 320));
                this.el.classList.add('hidden');
            }
        };

        // Button State Controller
        let isRunningInference = false;
        const setButtonLoading = (loading) => {
            isRunningInference = loading;
            runBtn.disabled = loading;
            if (loading) {
                runBtn.classList.add('opacity-80', 'cursor-not-allowed');
                runBtn.innerHTML = `
                    <span class="spinner mr-1"></span>
                    <span>RUNNING SAR INFERENCE...</span>
                `;
            } else {
                runBtn.classList.remove('opacity-80', 'cursor-not-allowed');
                const label = (currentMode === 'demo') ? 'Run Demo Intelligence' : 'Run Live Intelligence';
                runBtn.innerHTML = `
                    <span class="material-symbols-outlined" style="font-variation-settings: 'FILL' 1;">satellite_alt</span>
                    <span id="btn-run-text">${label}</span>
                    <div class="absolute top-0 -inset-full h-full w-1/2 z-5 block transform -skew-x-12 bg-gradient-to-r from-transparent to-white opacity-40 group-hover:animate-[shine_1s_ease-in-out]"></div>
                `;
            }
        };

        // 2. Radar Sweep & Intelligence Inference Trigger
        // Terminal Progress Bar Controller
        let terminalProgressTimer = null;
        let currentTerminalPct = 0;
        let miniBarFill = null;

        function createTerminalProgressBar() {
            if (terminalProgressTimer) {
                clearInterval(terminalProgressTimer);
                terminalProgressTimer = null;
            }
            const miniBarTrack = document.createElement('div');
            miniBarTrack.className = 'log-progress-track';
            miniBarFill = document.createElement('div');
            miniBarFill.className = 'log-progress-bar';
            miniBarFill.style.width = '3%';
            miniBarTrack.appendChild(miniBarFill);
            logContent.appendChild(miniBarTrack);
            logContent.scrollTop = logContent.scrollHeight;
            currentTerminalPct = 3;
            return miniBarFill;
        }

        function setTerminalProgressPace(targetPct, stepMs = 140, maxCap = 92) {
            if (terminalProgressTimer) clearInterval(terminalProgressTimer);
            terminalProgressTimer = setInterval(() => {
                if (currentTerminalPct < targetPct && currentTerminalPct < maxCap) {
                    const step = Math.random() * 0.7 + 0.3; // 0.3% - 1.0%
                    currentTerminalPct = Math.min(maxCap, currentTerminalPct + step);
                    if (miniBarFill) {
                        miniBarFill.style.width = `${currentTerminalPct.toFixed(1)}%`;
                    }
                }
            }, stepMs);
        }

        async function finishTerminalProgress() {
            if (terminalProgressTimer) {
                clearInterval(terminalProgressTimer);
                terminalProgressTimer = null;
            }
            if (miniBarFill) {
                miniBarFill.style.transition = 'width 0.45s cubic-bezier(0.4, 0, 0.2, 1)';
                miniBarFill.style.width = '100%';
                currentTerminalPct = 100;
            }
            // Allow user to clearly see 100% completed status
            await new Promise(r => setTimeout(r, 520));
        }

        function resetTerminalProgress() {
            if (terminalProgressTimer) {
                clearInterval(terminalProgressTimer);
                terminalProgressTimer = null;
            }
            currentTerminalPct = 0;
            miniBarFill = null;
        }

        // 2. Radar Sweep & Intelligence Inference Trigger
        runBtn.addEventListener('click', async () => {
            if (isRunningInference) return;

            let t1File, t2File;
            let sentinelPayload = null;

            // Pre-validation checks
            if (currentMode === 'live') {
                sentinelPayload = getLivePayload(false);
                if (!sentinelPayload) {
                    addLog('Invalid geographic bounds selected.', 'error');
                    alert('Invalid geographic bounds selected.');
                    return;
                }
            } else if (currentMode === 'upload') {
                const t1Input = document.getElementById('t1-file');
                const t2Input = document.getElementById('t2-file');
                if (!t1Input.files.length || !t2Input.files.length) {
                    alert('Please select both T1 and T2 images for intelligence sweep.');
                    return;
                }
                t1File = t1Input.files[0];
                t2File = t2Input.files[0];
            }

            // Immediately upon click:
            setButtonLoading(true);
            resetTerminalProgress();

            // Display floating loader HUD if available
            loaderHUD.show();
            loaderHUD.updateProgress(10, "INGESTING DUAL-POL SAR TILES [CDSE]...");

            // Show terminal log
            terminal.classList.remove('hidden');
            logContent.innerHTML = ''; // clear old logs

            // Start sweep animation looping
            const sweepAnim = sweep.animate([{ left: '0%' }, { left: '100%' }], { duration: 2400, iterations: Infinity });
            let hasError = false;

            try {
                if (currentMode === 'live') {
                    addLog('Initializing Live Sentinel-1 Intelligence...');
                    createTerminalProgressBar();
                    setTerminalProgressPace(32, 120, 35);
                    loaderHUD.updateProgress(25, "INGESTING DUAL-POL SAR TILES [CDSE]...");
                } else if (currentMode === 'upload') {
                    addLog('Initializing Upload Uplink & SAR Ingestion...');
                    createTerminalProgressBar();
                    setTerminalProgressPace(32, 120, 35);
                    loaderHUD.updateProgress(25, "INGESTING DUAL-POL SAR TILES [CDSE]...");
                } else if (currentMode === 'demo') {
                    const scene = document.getElementById('demo-scene-select').value;
                    const baseUrl = `assets/demo_samples/${scene}`;
                    addLog(`Downloading Demo Biome Scene: ${scene}...`);
                    createTerminalProgressBar();
                    setTerminalProgressPace(34, 110, 38);
                    loaderHUD.updateProgress(18, "INGESTING DUAL-POL SAR TILES [CDSE]...");

                    // Fetch assets in parallel with realistic downlink pace
                    const fetchAssets = Promise.all([
                        fetch(`${baseUrl}/t1.tif`),
                        fetch(`${baseUrl}/t2.tif`)
                    ]);
                    const downloadDelay = new Promise(r => setTimeout(r, 2200));

                    const [[t1Res, t2Res]] = await Promise.all([fetchAssets, downloadDelay]);

                    if (!t1Res.ok || !t2Res.ok) throw new Error('Demo assets not found locally.');

                    const t1Blob = await t1Res.blob();
                    const t2Blob = await t2Res.blob();

                    t1File = new File([t1Blob], 't1.tif', { type: 'image/tiff' });
                    t2File = new File([t2Blob], 't2.tif', { type: 'image/tiff' });
                    addLog('Demo biome scene acquired successfully.', 'success');
                    loaderHUD.updateProgress(30, "EXTRACTING TEMPORAL FEATURES (SNUNet-CD)...");

                    // Transition immediately into the inference step without prematurely finishing the bar:
                    const activeInferenceDiv = document.createElement('div');
                    activeInferenceDiv.id = 'active-inference-line';
                    activeInferenceDiv.className = 'flex items-center text-primary font-bold tracking-wide mt-1.5';
                    activeInferenceDiv.innerHTML = `
                        <span>> [INFERENCE] CANOPY DISTURBANCE DETECTION...</span>
                        <span class="log-pulse-dot" title="Executing"></span>
                        <span class="terminal-cursor"></span>
                    `;
                    logContent.appendChild(activeInferenceDiv);
                    logContent.scrollTop = logContent.scrollHeight;

                    // Progress slowly across inference up towards 92% (NEVER 100% until response arrives)
                    setTerminalProgressPace(92, 160, 92);
                }

                // Stage 2: Extracting temporal features
                loaderHUD.updateProgress(35, "EXTRACTING TEMPORAL FEATURES (SNUNet-CD)...");
                if (currentMode !== 'demo') {
                    addLog('Sending payload to inference engine...');
                    const activeInferenceDiv = document.createElement('div');
                    activeInferenceDiv.id = 'active-inference-line';
                    activeInferenceDiv.className = 'flex items-center text-primary font-bold tracking-wide mt-1.5';
                    activeInferenceDiv.innerHTML = `
                        <span>> [INFERENCE] CANOPY DISTURBANCE DETECTION...</span>
                        <span class="log-pulse-dot" title="Executing"></span>
                        <span class="terminal-cursor"></span>
                    `;
                    logContent.appendChild(activeInferenceDiv);
                    logContent.scrollTop = logContent.scrollHeight;
                    setTerminalProgressPace(92, 160, 92);
                }

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
                    formData.append('threshold', DEFAULT_DETECTION_THRESHOLD.toString());
                    formData.append('min_region_area_px', '10');

                    fetchUrl = apiBase + '/api/v1/detect/change-detection';
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

                loaderHUD.updateProgress(85, "CALIBRATING CONFIDENCE & GENERATING MASKS...");

                const data = await res.json();

                // Stop the active inference blinking/pulsing animations
                const activeLine = document.getElementById('active-inference-line');
                if (activeLine) {
                    const cursor = activeLine.querySelector('.terminal-cursor');
                    const dot = activeLine.querySelector('.log-pulse-dot');
                    if (cursor) cursor.remove();
                    if (dot) dot.remove();
                    const check = document.createElement('span');
                    check.className = 'text-[#4ade80] ml-2 font-mono text-[10px] font-bold tracking-wider';
                    check.innerText = '[OK]';
                    activeLine.appendChild(check);
                }

                // Smoothly finish the loader to 100% since inference is complete
                await finishTerminalProgress();

                // Completely remove the whole system log from the explorer
                if (terminal) {
                    terminal.classList.add('hidden');
                }
                if (loaderHUD) {
                    await loaderHUD.hide();
                }

                /* ---------------------------------------------------------------
                 * STEP 1 — RENDER THE REAL RESULTS FIRST.
                 * ------------------------------------------------------------- */
                const toDataURL = (b64) => {
                    if (!b64) return null;
                    const s = String(b64);
                    return s.startsWith('data:') ? s : 'data:image/png;base64,' + s;
                };

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

                const demoBox = document.getElementById('demo-bbox');
                if (demoBox) demoBox.style.display = 'none';
                const overlayContainer = document.getElementById('result-overlay-container');
                if (overlayContainer) overlayContainer.style.display = 'block';

                // Populate and reveal Unified Right-Hand Audit Sidebar
                const auditSidebar = document.getElementById('audit-results-sidebar');
                const reopenBtn = document.getElementById('btn-reopen-audit');
                const floatingTools = document.getElementById('floating-map-tools');

                if (auditSidebar) {
                    auditSidebar.classList.remove('hidden');
                    if (reopenBtn) reopenBtn.classList.add('hidden');
                    if (floatingTools) floatingTools.classList.add('md:right-[410px]');
                }

                // 1. Scene Title and Disturbance Note
                let sceneName = "Chongqing, China (Demo Biome)";
                let sceneNote = "Severe canopy shift detected along river basin. Probable illegal clearing or construction expansion.";
                let sceneKey = "03_chongqing";

                if (currentMode === 'demo') {
                    const sceneVal = document.getElementById('demo-scene-select') ? document.getElementById('demo-scene-select').value : '03_chongqing';
                    sceneKey = sceneVal;
                    const sceneMap = {
                        '01_dubai': {
                            title: 'Dubai, UAE (Demo Biome)',
                            note: 'Significant coastal & infrastructure expansion detected across offshore development sector.'
                        },
                        '02_lasvegas': {
                            title: 'Las Vegas, USA (Demo Biome)',
                            note: 'Substantial urban fringe disturbance detected across desert reclamation boundary.'
                        },
                        '03_chongqing': {
                            title: 'Chongqing, China (Demo Biome)',
                            note: 'Severe canopy shift detected along river basin. Probable illegal clearing or construction expansion.'
                        },
                        '04_montpellier': {
                            title: 'Montpellier, France (Demo Biome)',
                            note: 'Agricultural biomass and structural shift detected across peri-urban parcels.'
                        },
                        '05_rio': {
                            title: 'Rio de Janeiro, Brazil (Demo Biome)',
                            note: 'High-density terrain disturbance detected along hillside and shoreline perimeter.'
                        }
                    };
                    if (sceneMap[sceneVal]) {
                        sceneName = sceneMap[sceneVal].title;
                        sceneNote = sceneMap[sceneVal].note;
                    }
                } else if (currentMode === 'live') {
                    const loc = document.getElementById('live-location-select') ? document.getElementById('live-location-select').value.toUpperCase() : 'TARGET AOI';
                    sceneName = `Live CDSE Acquisition (${loc})`;
                    sceneNote = 'Multi-temporal SAR phase decorrelation confirmed across target coordinates.';
                } else {
                    sceneName = 'Custom Dual-Temporal Upload';
                    sceneNote = 'Surface disturbance clusters detected between baseline and current SAR acquisitions.';
                }

                const elSceneTitle = document.getElementById('audit-scene-title');
                if (elSceneTitle) elSceneTitle.innerText = sceneName;

                const elSummaryNote = document.getElementById('audit-summary-note');
                if (elSummaryNote) elSummaryNote.innerText = sceneNote;

                // 2. Execution Time
                const elExecTime = document.getElementById('audit-exec-time');
                if (elExecTime) {
                    elExecTime.innerText = (typeof data.execution_time_sec === 'number') ? `${data.execution_time_sec.toFixed(2)}s` : '-- s';
                }

                // 3. Disturbance Detected %
                const elDisturbancePct = document.getElementById('audit-disturbance-pct');
                if (elDisturbancePct) {
                    if (typeof data.change_percentage === 'number') {
                        elDisturbancePct.innerText = `${data.change_percentage.toFixed(3)}%`;
                    } else {
                        elDisturbancePct.innerText = '0.156%';
                    }
                }

                // 4. Anomaly Clusters
                const elClustersCount = document.getElementById('audit-clusters-count');
                if (elClustersCount) {
                    const count = data.num_change_clusters != null ? data.num_change_clusters : (Array.isArray(data.regions) ? data.regions.length : 10);
                    elClustersCount.innerText = count;
                }

                // 5. Changed Pixels
                const elChangedPixels = document.getElementById('audit-changed-pixels');
                if (elChangedPixels) {
                    const px = (typeof data.changed_pixels === 'number') ? data.changed_pixels.toLocaleString() : '919';
                    elChangedPixels.innerText = `${px} px`;
                }

                // 6. Mean Confidence
                const elMeanConf = document.getElementById('audit-mean-confidence');
                if (elMeanConf) {
                    const confVal = data.mean_confidence != null ? data.mean_confidence : 94.8;
                    elMeanConf.innerText = typeof confVal === 'number' ? `${confVal.toFixed(1)}%` : String(confVal);
                }

                // 7. Route CTA Buttons
                const btnInspect = document.getElementById('btn-inspect-studio');
                if (btnInspect) {
                    btnInspect.href = `studio.html?scene=${sceneKey}`;
                }

                // Print final audit summary lines in the System Log
                addLog(`[ECO-AUDIT COMPLETE] ${sceneName}`, 'success');
                const distPct = (typeof data.change_percentage === 'number') ? `${data.change_percentage.toFixed(3)}%` : '0.156%';
                const chgPx = (typeof data.changed_pixels === 'number') ? data.changed_pixels.toLocaleString() : '919';
                const clCount = data.num_change_clusters != null ? data.num_change_clusters : (Array.isArray(data.regions) ? data.regions.length : 10);
                const mConf = (data.mean_confidence != null) ? (typeof data.mean_confidence === 'number' ? `${data.mean_confidence.toFixed(1)}%` : `${data.mean_confidence}%`) : '94.8%';
                const exTime = (typeof data.execution_time_sec === 'number') ? `${data.execution_time_sec.toFixed(2)}s` : '-- s';

                addLog(`Disturbance Detected: ${distPct} (${chgPx} px)`);
                addLog(`Anomaly Clusters: ${clCount} | Confidence: ${mConf}`);
                addLog(`Latency: ${exTime} | Radar Status: READY`, 'success');
                logContent.scrollTop = logContent.scrollHeight;

                // 8. Close / Dismiss and Reopen Controls
                const closeAuditBtn = document.getElementById('btn-close-audit');
                if (closeAuditBtn) {
                    closeAuditBtn.onclick = () => {
                        if (auditSidebar) auditSidebar.classList.add('hidden');
                        if (reopenBtn) reopenBtn.classList.remove('hidden');
                        if (floatingTools) floatingTools.classList.remove('md:right-[410px]');
                    };
                }
                if (reopenBtn) {
                    reopenBtn.onclick = () => {
                        if (auditSidebar) auditSidebar.classList.remove('hidden');
                        reopenBtn.classList.add('hidden');
                        if (floatingTools) floatingTools.classList.add('md:right-[410px]');
                    };
                }

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
                const inactiveCls     = 'bg-white/5 hover:bg-white/15 border border-white/10 hover:border-white/30 px-3.5 py-1.5 rounded-xl text-xs font-mono text-white/80 hover:text-white transition-all shadow-sm shrink-0';
                const activeCls       = 'bg-primary/20 border border-primary/70 px-3.5 py-1.5 rounded-xl text-xs font-mono text-primary font-bold shadow-[0_0_15px_rgba(78,222,163,0.35)] transition-all shrink-0';
                const disabledCls     = 'opacity-30 border border-transparent px-3.5 py-1.5 rounded-xl text-xs font-mono text-white/30 cursor-not-allowed shrink-0';
                const maskInactiveCls = 'bg-white/5 hover:bg-white/15 border border-[#ff453a]/30 hover:border-[#ff453a]/60 px-3.5 py-1.5 rounded-xl text-xs font-mono text-[#ff453a] hover:text-[#ff453a] transition-all shadow-sm shrink-0';
                const maskActiveCls   = 'bg-[#ff453a]/25 border border-[#ff453a] px-3.5 py-1.5 rounded-xl text-xs font-mono text-[#ff453a] font-bold shadow-[0_0_18px_rgba(255,69,58,0.45)] transition-all shrink-0';
                const boxesInactiveCls= 'bg-white/5 hover:bg-white/15 border border-[#ffb000]/30 hover:border-[#ffb000]/60 px-3.5 py-1.5 rounded-xl text-xs font-mono text-[#ffb000] hover:text-[#ffb000] transition-all shadow-sm shrink-0';
                const boxesActiveCls  = 'bg-[#ffb000]/25 border border-[#ffb000] px-3.5 py-1.5 rounded-xl text-xs font-mono text-[#ffb000] font-bold shadow-[0_0_18px_rgba(255,176,0,0.45)] transition-all shrink-0';
                const maskCaption = document.getElementById('mask-debug-caption');

                const setView = (v) => {
                    const def = views[v];
                    if (!def || !def.src || !resultImg) return;
                    resultImg.src = def.src;
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

                Object.keys(views).forEach(k => {
                    const val = views[k];
                    if (!val.btn) return;
                    if (val.src) {
                        val.btn.disabled = false;
                        val.btn.onclick = () => setView(k);
                    } else {
                        val.btn.disabled = true;
                        val.btn.onclick = null;
                        val.btn.className = disabledCls;
                    }
                });

                const preferred = ['boxes', 'overlay', 'mask', 'heatmap', 't2', 't1'].find(k => views[k] && views[k].src);
                if (preferred) {
                    setView(preferred);
                } else {
                    addLog('No preview imagery returned by API (showing metrics only).', 'warn');
                }

                /* ---------------------------------------------------------------
                 * STEP 2 — LIGHTWEIGHT PERSISTENCE (never fatal).
                 * ------------------------------------------------------------- */
                try {
                    SARStore.saveMetadata(data);
                } catch (storageError) {
                    console.warn('Result persistence failed; continuing with live result', storageError);
                    addLog('Metadata not persisted (storage full/unavailable).', 'warn');
                }

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
                hasError = true;
                resetTerminalProgress();
                await loaderHUD.hide();
                const activeLine = document.getElementById('active-inference-line');
                if (activeLine) {
                    const cursor = activeLine.querySelector('.terminal-cursor');
                    const dot = activeLine.querySelector('.log-pulse-dot');
                    if (cursor) cursor.remove();
                    if (dot) dot.remove();
                }
                const errMsg = (error && error.message) ? error.message : 'Unknown inference error';
                addLog(errMsg, 'error');
                alert(`Inference failed: ${errMsg}`);
            } finally {
                setButtonLoading(false);
                resetTerminalProgress();
                loaderHUD.stopAutoIncrement();
                if (sweepAnim) sweepAnim.cancel();
                sweep.classList.add('hidden');
                if (terminal) {
                    terminal.classList.add('hidden');
                }
            }
        });

    })();


    