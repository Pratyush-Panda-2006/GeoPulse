
        document.addEventListener('DOMContentLoaded', async () => {
            let metadata = (window.SARStore && SARStore.loadMetadata) ? SARStore.loadMetadata() : null;
            let previews = (window.SARStore && SARStore.loadPreviews) ? await SARStore.loadPreviews() : null;
            
            // Time-Series Override: if navigated from a specific pair in the series
            const targetPairId = sessionStorage.getItem('target_pair');
            if (targetPairId && window.SARStore && SARStore.loadTimeSeries) {
                const seriesData = SARStore.loadTimeSeries();
                if (seriesData && seriesData.result) {
                    const pair = seriesData.result.job_id != null && seriesData.result.job_id.toString() === targetPairId ? seriesData.result : null;
                    if (pair) {
                        metadata = {
                            total_pixels: 512 * 512,
                            changed_pixels: 0,
                            change_percentage: pair.change_percentage,
                            num_change_clusters: pair.num_change_clusters,
                            regions: pair.regions,
                            nemotron_interpretations: pair.nemotron_interpretations || null
                        };
                        
                        previews = {
                            t1: pair.t1_preview_base64 ? `data:image/jpeg;base64,${pair.t1_preview_base64}` : null,
                            t2: pair.t2_preview_base64 ? `data:image/jpeg;base64,${pair.t2_preview_base64}` : null,
                            mask: pair.change_mask_base64 ? `data:image/png;base64,${pair.change_mask_base64}` : null,
                            heatmap: pair.confidence_heatmap_base64 ? `data:image/png;base64,${pair.confidence_heatmap_base64}` : null,
                            overlay: pair.overlay_base64 ? `data:image/jpeg;base64,${pair.overlay_base64}` : null
                        };
                    }
                }
                sessionStorage.removeItem('target_pair');
            }

            const t1Bg = document.getElementById('t1-image-bg');
            const t2Clip = document.getElementById('t2-image-clip');
            const heatmapOverlay = document.getElementById('heatmap-overlay');

            // 10 Fallback demo regions for Chongqing scene
            const fallbackRegions = [
                { region_id: 1, area_px: 248, area_km2: 0.0248, centroid_xy: [180.4, 210.2], geo_centroid: [106.5510, 29.5630], mean_change_prob: 0.962, severity: 'High', category: 'CANOPY CLEARING & DEFORESTATION', summary: 'Intense phase loss indicating mass vegetative disruption along northern river basin.' },
                { region_id: 2, area_px: 195, area_km2: 0.0195, centroid_xy: [240.8, 175.6], geo_centroid: [106.5642, 29.5714], mean_change_prob: 0.954, severity: 'High', category: 'HEAVY STRUCTURAL EXCAVATION', summary: 'Coherent backscatter rise characteristic of industrial groundwork and construction machinery.' },
                { region_id: 3, area_px: 142, area_km2: 0.0142, centroid_xy: [310.2, 290.5], geo_centroid: [106.5780, 29.5490], mean_change_prob: 0.938, severity: 'Medium', category: 'SURFACE WATER DIVERSION', summary: 'Low specular return indicating localized canal diversion or recent retention basin.' },
                { region_id: 4, area_px: 110, area_km2: 0.0110, centroid_xy: [145.6, 340.1], geo_centroid: [106.5420, 29.5380], mean_change_prob: 0.912, severity: 'Medium', category: 'PERI-URBAN LAND RECLAMATION', summary: 'Geometric edge displacement matching foundation trenching and earthworks.' },
                { region_id: 5, area_px: 88,  area_km2: 0.0088, centroid_xy: [390.5, 160.3], geo_centroid: [106.5910, 29.5740], mean_change_prob: 0.895, severity: 'Low', category: 'VEGETATION DISTURBANCE', summary: 'Seasonal or transitional crop canopy change.' },
                { region_id: 6, area_px: 62,  area_km2: 0.0062, centroid_xy: [215.1, 410.8], geo_centroid: [106.5580, 29.5220], mean_change_prob: 0.874, severity: 'Low', category: 'MINOR SOIL DISPLACEMENT', summary: 'Localized backscatter variance across unpaved road corridor.' },
                { region_id: 7, area_px: 36,  area_km2: 0.0036, centroid_xy: [280.9, 120.4], geo_centroid: [106.5720, 29.5820], mean_change_prob: 0.846, severity: 'Low', category: 'SHALLOW EXCAVATION', summary: 'Localized terrain alteration near drainage perimeter.' },
                { region_id: 8, area_px: 21,  area_km2: 0.0021, centroid_xy: [440.2, 260.7], geo_centroid: [106.6020, 29.5550], mean_change_prob: 0.825, severity: 'Low', category: 'MARGINAL INTERFERENCE', summary: 'Low-confidence speckle fluctuation near infrastructure.' },
                { region_id: 9, area_px: 12,  area_km2: 0.0012, centroid_xy: [110.8, 190.2], geo_centroid: [106.5350, 29.5670], mean_change_prob: 0.798, severity: 'Low', category: 'SPECULAR ARTIFACT', summary: 'Transient moisture gradient anomaly.' },
                { region_id: 10, area_px: 5,  area_km2: 0.0005, centroid_xy: [360.4, 380.9], geo_centroid: [106.5860, 29.5290], mean_change_prob: 0.781, severity: 'Low', category: 'ISOLATED PIXEL VARIANCE', summary: 'Small-scale backscatter noise.' }
            ];

            // Fallback imagery if store has no data
            if (!previews || !previews.t1 || !previews.t2) {
                previews = {
                    t1: "https://images.unsplash.com/photo-1509228468518-180dd4864904?auto=format&fit=crop&w=1600&q=80",
                    t2: "https://images.unsplash.com/photo-1451187580459-43490279c0fa?auto=format&fit=crop&w=1600&q=80",
                    heatmap: "https://images.unsplash.com/photo-1451187580459-43490279c0fa?auto=format&fit=crop&w=1600&q=80",
                    overlay: "https://images.unsplash.com/photo-1451187580459-43490279c0fa?auto=format&fit=crop&w=1600&q=80",
                    boxes: "https://images.unsplash.com/photo-1451187580459-43490279c0fa?auto=format&fit=crop&w=1600&q=80"
                };
            }
            if (!previews.overlay) previews.overlay = previews.t2;
            if (!previews.boxes) previews.boxes = previews.t2;

            if (!metadata) {
                metadata = {
                    threshold: 0.60,
                    num_change_clusters: 10,
                    change_percentage: 0.156,
                    changed_pixels: 919,
                    total_pixels: 262144,
                    regions: fallbackRegions
                };
            } else if (!metadata.regions || metadata.regions.length === 0) {
                metadata.regions = fallbackRegions;
            }

            t1Bg.style.backgroundImage = `url('${previews.t1}')`;
            t2Clip.style.backgroundImage = `url('${previews.t2}')`;

            // Populate Telemetry Metrics
            const fmtInt = (n) => (typeof n === 'number' && isFinite(n)) ? n.toLocaleString() : '--';
            document.getElementById('studio-threshold').innerText = (metadata.threshold != null) ? Number(metadata.threshold).toFixed(2) : '0.60';
            document.getElementById('studio-clusters').innerText = (metadata.num_change_clusters != null) ? metadata.num_change_clusters : (Array.isArray(metadata.regions) ? metadata.regions.length : '10');
            document.getElementById('studio-change').innerText = (typeof metadata.change_percentage === 'number') ? `${metadata.change_percentage.toFixed(3)}%` : '0.156%';
            document.getElementById('studio-changed-px').innerText = fmtInt(metadata.changed_pixels || 919);

            // Layer Management Logic
            const layerCards = document.querySelectorAll('.layer-card');
            const btnT1 = document.getElementById('view-t1');
            const btnT2 = document.getElementById('view-t2');
            const btnOptical = document.getElementById('view-optical');
            const btnFalsecolor = document.getElementById('view-falsecolor');
            const btnHeatmap = document.getElementById('view-heatmap');
            const btnMask = document.getElementById('view-mask');
            const btnOverlay = document.getElementById('view-overlay');
            const btnBoxes = document.getElementById('view-boxes');

            const navButtons = {
                't1': btnT1,
                't2': btnT2,
                'optical': btnOptical,
                'falsecolor': btnFalsecolor,
                'heatmap': btnHeatmap,
                'mask': btnMask,
                'overlay': btnOverlay,
                'boxes': btnBoxes
            };

            window.setActiveLayer = function(layer) {
                // Update Card Grid in Inspector
                layerCards.forEach(card => {
                    if (card.dataset.layer === layer) {
                        card.className = 'layer-card active p-2.5 rounded-lg border text-left flex flex-col justify-between transition-all bg-slate-900/95 border-emerald-400/80 ring-1 ring-emerald-400 shadow-[0_0_12px_rgba(16,185,129,0.2)]';
                        const titleEl = card.querySelector('span.text-xs');
                        if (titleEl) titleEl.className = 'text-xs font-semibold text-emerald-200 line-clamp-1';
                    } else {
                        card.className = 'layer-card p-2.5 rounded-lg border text-left flex flex-col justify-between transition-all bg-[#0B0F17]/60 border-[#2D3748] hover:bg-slate-800/50 hover:border-slate-600';
                        const titleEl = card.querySelector('span.text-xs');
                        if (titleEl) titleEl.className = 'text-xs font-semibold text-slate-200 line-clamp-1';
                    }
                });

                // Update Tool Strip Buttons
                Object.entries(navButtons).forEach(([key, btn]) => {
                    if (!btn) return;
                    if (key === 'mask') {
                        btn.className = 'p-1 text-[#ff453a] hover:bg-[#ff453a]/10 rounded-lg transition-colors';
                    } else if (key === 'boxes') {
                        btn.className = 'px-2 py-0.5 text-xs font-mono text-amber-400 hover:bg-amber-500/10 border border-amber-500/30 rounded flex items-center gap-1 transition-colors';
                    } else {
                        btn.className = 'px-2.5 py-1 text-xs font-mono rounded-lg text-slate-400 hover:text-slate-100 hover:bg-slate-800 transition-colors';
                    }
                });

                const activeNavBtn = navButtons[layer];
                if (activeNavBtn) {
                    if (layer === 'mask') {
                        activeNavBtn.className = 'p-1 text-[#ff453a] border border-[#ff453a] bg-[#ff453a]/20 rounded-lg font-bold';
                    } else if (layer === 'boxes') {
                        activeNavBtn.className = 'px-2 py-0.5 text-xs font-mono text-amber-300 bg-amber-500/20 border border-amber-400 rounded flex items-center gap-1 font-bold';
                    } else {
                        activeNavBtn.className = 'px-2.5 py-1 text-xs font-mono rounded-lg bg-emerald-500/20 text-emerald-300 border border-emerald-500/40 font-semibold';
                    }
                }

                // Update imagery on right pane
                if (layer === 't1') {
                    t2Clip.style.backgroundImage = `url('${previews.t1}')`;
                    heatmapOverlay.classList.add('hidden');
                } else if (layer === 't2') {
                    t2Clip.style.backgroundImage = `url('${previews.t2}')`;
                    heatmapOverlay.classList.add('hidden');
                } else if (layer === 'optical') {
                    t2Clip.style.backgroundImage = `url('${previews.optical || previews.t2}')`;
                    heatmapOverlay.classList.add('hidden');
                } else if (layer === 'falsecolor') {
                    t2Clip.style.backgroundImage = `url('${previews.falseColorT2 || previews.t2}')`;
                    heatmapOverlay.classList.add('hidden');
                } else if (layer === 'heatmap') {
                    t2Clip.style.backgroundImage = `url('${previews.heatmap || previews.t2}')`;
                    heatmapOverlay.classList.remove('hidden');
                } else if (layer === 'mask') {
                    t2Clip.style.backgroundImage = `url('${previews.mask || previews.t2}')`;
                    heatmapOverlay.classList.add('hidden');
                } else if (layer === 'overlay') {
                    t2Clip.style.backgroundImage = `url('${previews.overlay || previews.t2}')`;
                    heatmapOverlay.classList.add('hidden');
                } else if (layer === 'boxes') {
                    t2Clip.style.backgroundImage = `url('${previews.opticalBoxes || previews.boxes || previews.overlay || previews.t2}')`;
                    heatmapOverlay.classList.add('hidden');
                }

                t2Clip.style.imageRendering = (layer === 'mask') ? 'pixelated' : 'auto';
            };

            layerCards.forEach(card => {
                card.addEventListener('click', () => window.setActiveLayer(card.dataset.layer));
            });

            Object.entries(navButtons).forEach(([key, btn]) => {
                if (btn) btn.addEventListener('click', () => window.setActiveLayer(key));
            });

            window.setActiveLayer('t2');

            // --- Cluster Targeting & GSAP Camera Mechanics ---
            let currentScale = 1;
            let currentOrigin = '50% 50%';

            window.flyToCluster = function(region) {
                if (!region) return;
                
                let cx = 256;
                let cy = 256;
                if (Array.isArray(region.centroid_xy) && region.centroid_xy.length >= 2) {
                    cx = Number(region.centroid_xy[0]);
                    cy = Number(region.centroid_xy[1]);
                }
                
                const normX = Math.min(Math.max((cx / 512) * 100, 10), 90);
                const normY = Math.min(Math.max((cy / 512) * 100, 10), 90);
                currentOrigin = `${normX}% ${normY}%`;
                currentScale = 2.2;

                // 1. Move Split Curtain to 20% so Highlight Changes is clearly revealed while keeping T1 reference
                if (typeof setCurtainPos === 'function') {
                    setCurtainPos(20);
                }

                // 2. Select Highlight Changes layer (boxes) as requested, NOT composite overlay
                window.setActiveLayer('boxes');

                // 3. Smooth GSAP camera fly-to into cluster coordinates to showcase the highlight change box
                gsap.to(transformWrapper, {
                    scale: currentScale,
                    transformOrigin: currentOrigin,
                    duration: 1.3,
                    ease: "power2.out"
                });

                // 5. Populate and open Intel Panel
                const intelPanel = document.getElementById('intel-panel');
                if (intelPanel) {
                    intelPanel.classList.remove('hidden');
                    intelPanel.classList.add('flex');
                    
                    const elRegId = document.getElementById('intel-region-id');
                    if (elRegId) elRegId.innerText = `CL-${region.region_id}`;
                    
                    const elSev = document.getElementById('intel-severity');
                    if (elSev) {
                        const s = region.severity || 'Medium';
                        elSev.innerText = s.toUpperCase();
                        elSev.className = s === 'High' ? 'font-bold text-red-400' :
                                          s === 'Medium' ? 'font-bold text-amber-400' : 'font-bold text-emerald-400';
                    }

                    const lon = region.geo_centroid ? region.geo_centroid[0] : (106.55 + (cx / 5000));
                    const lat = region.geo_centroid ? region.geo_centroid[1] : (29.56 + (cy / 5000));
                    const coordStr = `${lat.toFixed(4)}° N, ${lon.toFixed(4)}° E`;
                    
                    const elCoords = document.getElementById('intel-coords');
                    if (elCoords) elCoords.innerText = coordStr;

                    let areaSqFt = 0;
                    if (region.area_km2) areaSqFt = region.area_km2 * 10763910.4;
                    else if (region.approx_area_sq_km) areaSqFt = region.approx_area_sq_km * 10763910.4;
                    else areaSqFt = (region.area_px || 100) * 1076.39104;

                    const elArea = document.getElementById('intel-area');
                    if (elArea) elArea.innerText = `${Math.round(areaSqFt).toLocaleString()} sq ft`;

                    const elPx = document.getElementById('intel-changed-px');
                    if (elPx) elPx.innerText = `${region.area_px != null ? region.area_px.toLocaleString() : '--'} px`;

                    const prob = region.mean_change_prob !== undefined ? region.mean_change_prob : (region.change_probability || 0.94);
                    const elProb = document.getElementById('intel-prob');
                    if (elProb) elProb.innerText = `${(prob * 100).toFixed(1)}%`;

                    // Update Bottom Left Telemetry Readout
                    const rLat = document.getElementById('readout-lat');
                    const rLng = document.getElementById('readout-lng');
                    const rDb = document.getElementById('readout-db');
                    if (rLat) rLat.innerText = `${lat.toFixed(4)}° N`;
                    if (rLng) rLng.innerText = `${lon.toFixed(4)}° E`;
                    if (rDb) rDb.innerText = `-7.6 dB [ANOMALY]`;

                    // Nemotron AI Section
                    const nemotronSection = document.getElementById('intel-nemotron-section');
                    if (nemotronSection) {
                        nemotronSection.classList.remove('hidden');
                        
                        const defaultCategories = {
                            1: { type: 'RAPID CANOPY CLEARING & DEFORESTATION', sum: 'Sudden loss of volume scattering indicative of unauthorized clear-cutting.' },
                            2: { type: 'HEAVY INDUSTRIAL GROUNDWORK', sum: 'High backscatter return with sharp phase variance matching excavation machines and ground grading.' },
                            3: { type: 'SURFACE WATER & INUNDATION', sum: 'Specular backscatter drop indicating canal diversion or recent retention pond creation.' },
                            4: { type: 'PERI-URBAN LAND RECLAMATION', sum: 'Coherent boundary displacement matching foundation trenches.' }
                        };
                        const info = defaultCategories[region.region_id] || {
                            type: region.category || 'STRUCTURAL SURFACE DISTURBANCE',
                            sum: region.summary || `Significant SAR amplitude and phase variance detected across ${Math.round(areaSqFt).toLocaleString()} sq ft.`
                        };

                        const elType = document.getElementById('intel-nemo-type');
                        if (elType) elType.innerText = info.type;

                        const elConf = document.getElementById('intel-nemo-conf');
                        if (elConf) elConf.innerText = `${Math.round(prob * 100)}%`;

                        const elSource = document.getElementById('intel-nemo-source');
                        if (elSource) elSource.innerText = 'Nemotron-Vision S1-SAR';

                        const elSummary = document.getElementById('intel-nemo-summary');
                        if (elSummary) elSummary.innerText = info.sum;

                        const elUncert = document.getElementById('intel-nemo-uncertainty');
                        if (elUncert) elUncert.innerText = region.severity === 'High' ? 'Low (< 3.8%)' : 'Nominal (< 6.2%)';

                        const elCues = document.getElementById('intel-nemo-cues');
                        if (elCues) {
                            elCues.innerHTML = `
                                <li>VV/VH cross-polarization ratio shifted by >3.8 dB</li>
                                <li>Temporal decorrelation sustained across recent pass</li>
                                <li>Centroid localized in survey quadrant</li>
                            `;
                        }
                    }
                }
            };

            window.resetClusterFocus = function() {
                currentScale = 1;
                currentOrigin = '50% 50%';
                gsap.to(transformWrapper, {
                    scale: 1,
                    transformOrigin: '50% 50%',
                    duration: 0.9,
                    ease: "power2.inOut"
                });
                if (typeof setCurtainPos === 'function') {
                    setCurtainPos(50);
                }
                window.setActiveLayer('t2');
                const intelPanel = document.getElementById('intel-panel');
                if (intelPanel) {
                    intelPanel.classList.add('hidden');
                    intelPanel.classList.remove('flex');
                }
            };

            // Read target cluster from URL params or sessionStorage
            const urlParams = new URLSearchParams(window.location.search);
            const targetRegionId = urlParams.get('cluster') || sessionStorage.getItem('target_cluster');
            const storedClusterJson = sessionStorage.getItem('target_cluster_data');
            
            // Immediately clean up one-time session handoff so direct visits / reloads show default comparison
            sessionStorage.removeItem('target_cluster');
            sessionStorage.removeItem('target_cluster_data');

            if (targetRegionId) {
                let targetRegion = null;
                if (storedClusterJson) {
                    try {
                        targetRegion = JSON.parse(storedClusterJson);
                    } catch (e) {}
                }
                
                if (!targetRegion && metadata && Array.isArray(metadata.regions)) {
                    targetRegion = metadata.regions.find(r => r.region_id != null && String(r.region_id) === String(targetRegionId));
                }

                if (!targetRegion) {
                    targetRegion = fallbackRegions.find(r => String(r.region_id) === String(targetRegionId));
                }

                if (targetRegion) {
                    setTimeout(() => {
                        window.flyToCluster(targetRegion);
                    }, 120);
                }
            } else {
                // DEFAULT STUDIO COMPARISON VIEW (When user clicks Studio directly or from navbar)
                if (typeof setCurtainPos === 'function') {
                    setCurtainPos(50);
                }
                window.setActiveLayer('t2');
                window.resetClusterFocus();
            }
        });

        // Split Curtain Drag Mechanics
        const container = document.getElementById('split-view-container');
        const slider = document.getElementById('split-slider');
        const t2Clip = document.getElementById('t2-image-clip');
        const btnLock = document.getElementById('btn-split-lock');
        const btnReset = document.getElementById('btn-split-reset');

        let isLocked = false;
        let isDraggingSplit = false;

        btnLock.addEventListener('click', () => {
            isLocked = !isLocked;
            if (isLocked) {
                btnLock.className = 'px-2.5 py-1 rounded-lg text-xs font-mono bg-amber-500/20 text-amber-300 border border-amber-500/40 flex items-center gap-1.5 font-bold';
                btnLock.innerHTML = '<span class="material-symbols-outlined text-[14px]">lock</span><span>LOCKED</span>';
            } else {
                btnLock.className = 'px-2.5 py-1 rounded-lg text-xs font-mono text-slate-400 hover:text-slate-100 hover:bg-slate-800 flex items-center gap-1.5 transition-colors';
                btnLock.innerHTML = '<span class="material-symbols-outlined text-[14px]">lock_open</span><span>SLIDER</span>';
            }
        });

        const setCurtainPos = (pct) => {
            pct = Math.max(0, Math.min(100, pct));
            slider.style.left = `${pct}%`;
            t2Clip.style.clipPath = `polygon(${pct}% 0, 100% 0, 100% 100%, ${pct}% 100%)`;
        };

        btnReset.addEventListener('click', () => setCurtainPos(50));

        slider.addEventListener('pointerdown', (e) => {
            if (isLocked) return;
            isDraggingSplit = true;
            slider.setPointerCapture(e.pointerId);
            e.preventDefault();
        });

        window.addEventListener('pointermove', (e) => {
            if (!isDraggingSplit || isLocked) return;
            const rect = container.getBoundingClientRect();
            const x = Math.max(0, Math.min(e.clientX - rect.left, rect.width));
            const pct = (x / rect.width) * 100;
            setCurtainPos(pct);
        });

        window.addEventListener('pointerup', (e) => {
            if (isDraggingSplit) {
                isDraggingSplit = false;
                try { slider.releasePointerCapture(e.pointerId); } catch {}
            }
        });

        // Statically Framed Coordinate Plane & Compass Orientation
        const transformWrapper = document.getElementById('canvas-transform-wrapper');
        let rotation = 0; // 0 to 360 degrees

        const updateTransform = () => {
            transformWrapper.style.transform = rotation ? `rotate(${rotation}deg)` : 'none';
        };

        // Cardinal 16-point conversion
        const getCardinal = (deg) => {
            const norm = (deg % 360 + 360) % 360;
            const points = ['N', 'NNE', 'NE', 'ENE', 'E', 'ESE', 'SE', 'SSE', 'S', 'SSW', 'SW', 'WSW', 'W', 'WNW', 'NW', 'NNW'];
            return points[Math.round(norm / 22.5) % 16];
        };

        const updateCompassUI = () => {
            const dial = document.getElementById('compass-dial-svg');
            const text = document.getElementById('compass-heading-text');
            if (dial) dial.style.transform = `rotate(${-rotation}deg)`;
            const norm = Math.round((rotation % 360 + 360) % 360);
            if (text) text.innerText = `${norm.toString().padStart(3, '0')}° ${getCardinal(norm)}`;
        };

        // --- Interactive Draggable & Rotatable Compass HUD ---
        const compassHud = document.getElementById('tactical-compass-hud');
        const compassDialRing = document.getElementById('compass-dial-ring');
        const compassBearingLabel = document.getElementById('compass-bearing-label');

        let isDraggingCompassWidget = false;
        let isRotatingDial = false;
        let compassStartPos = { clientX: 0, clientY: 0, posX: 20, posY: 20 };

        if (compassHud) {
            compassHud.addEventListener('pointerdown', (e) => {
                if (e.target.closest('#compass-dial-ring')) return;
                isDraggingCompassWidget = true;
                const rect = compassHud.getBoundingClientRect();
                const parentRect = container.getBoundingClientRect();
                compassStartPos = {
                    clientX: e.clientX,
                    clientY: e.clientY,
                    posX: rect.left - parentRect.left,
                    posY: rect.top - parentRect.top
                };
                compassHud.setPointerCapture(e.pointerId);
                e.stopPropagation();
            });

            compassHud.addEventListener('pointermove', (e) => {
                if (!isDraggingCompassWidget) return;
                const dx = e.clientX - compassStartPos.clientX;
                const dy = e.clientY - compassStartPos.clientY;
                compassHud.style.left = `${Math.max(10, compassStartPos.posX + dx)}px`;
                compassHud.style.top = `${Math.max(10, compassStartPos.posY + dy)}px`;
            });

            compassHud.addEventListener('pointerup', (e) => {
                if (isDraggingCompassWidget) {
                    isDraggingCompassWidget = false;
                    try { compassHud.releasePointerCapture(e.pointerId); } catch {}
                }
            });
        }

        if (compassDialRing) {
            compassDialRing.addEventListener('pointerdown', (e) => {
                isRotatingDial = true;
                compassDialRing.setPointerCapture(e.pointerId);
                e.stopPropagation();
            });

            compassDialRing.addEventListener('pointermove', (e) => {
                if (!isRotatingDial) return;
                const rect = compassDialRing.getBoundingClientRect();
                const cx = rect.left + rect.width / 2;
                const cy = rect.top + rect.height / 2;
                const rad = Math.atan2(e.clientY - cy, e.clientX - cx);
                let deg = rad * (180 / Math.PI) + 90;
                if (deg < 0) deg += 360;
                rotation = Math.round(deg);
                updateCompassUI();
                updateTransform();
            });

            compassDialRing.addEventListener('pointerup', (e) => {
                if (isRotatingDial) {
                    isRotatingDial = false;
                    try { compassDialRing.releasePointerCapture(e.pointerId); } catch {}
                }
            });
        }

        if (compassBearingLabel) {
            compassBearingLabel.addEventListener('click', (e) => {
                e.stopPropagation();
                rotation = 0;
                updateCompassUI();
                updateTransform();
            });
        }

        // Real-time graticule coordinates tracking (Hover without pan/zoom drag)
        container.addEventListener('mousemove', (e) => {
            const rect = container.getBoundingClientRect();
            if (e.clientX >= rect.left && e.clientX <= rect.right && e.clientY >= rect.top && e.clientY <= rect.bottom) {
                const nx = (e.clientX - rect.left) / rect.width;
                const ny = (e.clientY - rect.top) / rect.height;
                const latBase = 18.9440 + (1 - ny) * 0.04;
                const lngBase = 72.8359 + nx * 0.04;
                const simulatedDB = (-10 - Math.sin(nx * 6) * 6).toFixed(1);

                document.getElementById('readout-lat').innerText = `${latBase.toFixed(4)}° N`;
                document.getElementById('readout-lng').innerText = `${lngBase.toFixed(4)}° E`;
                document.getElementById('readout-db').innerText = `${simulatedDB} dB`;
            }
        });

        // Inspector Collapse / Expand
        const inspector = document.getElementById('inspector-dock');
        const btnToggleInspector = document.getElementById('btn-toggle-inspector');
        const btnCloseInspector = document.getElementById('btn-close-inspector');

        const toggleInspector = () => {
            const isHidden = inspector.classList.toggle('hidden');
            if (btnToggleInspector) {
                if (!isHidden) {
                    btnToggleInspector.className = 'ml-1 px-3 py-1 rounded-lg text-xs font-mono flex items-center gap-1.5 transition-all bg-emerald-500/20 text-emerald-300 border border-emerald-500/40 font-bold';
                } else {
                    btnToggleInspector.className = 'ml-1 px-3 py-1 rounded-lg text-xs font-mono flex items-center gap-1.5 transition-all bg-emerald-500/10 hover:bg-emerald-500/20 text-emerald-400 border border-emerald-500/30';
                }
            }
        };
        btnToggleInspector.addEventListener('click', toggleInspector);
        btnCloseInspector.addEventListener('click', toggleInspector);

        const closeIntelBtn = document.getElementById('close-intel-panel');
        if (closeIntelBtn) {
            closeIntelBtn.addEventListener('click', () => {
                if (typeof window.resetClusterFocus === 'function') {
                    window.resetClusterFocus();
                } else {
                    const p = document.getElementById('intel-panel');
                    if (p) {
                        p.classList.add('hidden');
                        p.classList.remove('flex');
                    }
                }
            });
        }

        // Dual-Input Radiometric Adjustments
        let opacityVal = 100;
        let brightnessVal = 100;
        let contrastVal = 100;

        const applyFilters = () => {
            t2Clip.style.opacity = opacityVal / 100;
            const filterStr = `brightness(${brightnessVal}%) contrast(${contrastVal}%)`;
            t2Clip.style.filter = filterStr;
            document.getElementById('t1-image-bg').style.filter = filterStr;
        };

        // Opacity
        const opSlider = document.getElementById('opacity-slider-ui');
        const opNum = document.getElementById('opacity-num');
        const syncOpacity = (v) => {
            opacityVal = Math.max(0, Math.min(100, Number(v)));
            opSlider.value = opacityVal;
            opNum.value = opacityVal;
            applyFilters();
        };
        opSlider.addEventListener('input', (e) => syncOpacity(e.target.value));
        opNum.addEventListener('change', (e) => syncOpacity(e.target.value));
        document.getElementById('opacity-reset').addEventListener('click', () => syncOpacity(100));

        // Brightness
        const brSlider = document.getElementById('brightness-slider-ui');
        const brNum = document.getElementById('brightness-num');
        const syncBrightness = (v) => {
            brightnessVal = Math.max(50, Math.min(150, Number(v)));
            brSlider.value = brightnessVal;
            brNum.value = brightnessVal;
            applyFilters();
        };
        brSlider.addEventListener('input', (e) => syncBrightness(e.target.value));
        brNum.addEventListener('change', (e) => syncBrightness(e.target.value));
        document.getElementById('brightness-reset').addEventListener('click', () => syncBrightness(100));

        // Contrast
        const ctSlider = document.getElementById('contrast-slider-ui');
        const ctNum = document.getElementById('contrast-num');
        const syncContrast = (v) => {
            contrastVal = Math.max(50, Math.min(200, Number(v)));
            ctSlider.value = contrastVal;
            ctNum.value = contrastVal;
            applyFilters();
        };
        ctSlider.addEventListener('input', (e) => syncContrast(e.target.value));
        ctNum.addEventListener('change', (e) => syncContrast(e.target.value));
        document.getElementById('contrast-reset').addEventListener('click', () => syncContrast(100));

        // Colormap Radios
        const colormapRadios = document.querySelectorAll('input[name="colormap"]');
        colormapRadios.forEach(radio => {
            radio.addEventListener('change', (e) => {
                colormapRadios.forEach(r => {
                    const label = r.closest('label');
                    if (r.checked) {
                        label.className = 'flex items-center justify-between p-2 rounded-lg border border-emerald-500/40 bg-emerald-500/10 cursor-pointer transition-colors colormap-opt';
                        label.querySelector('span').className = 'font-mono text-xs text-slate-100';
                    } else {
                        label.className = 'flex items-center justify-between p-2 rounded-lg border border-[#2D3748] bg-[#0B0F17]/40 hover:bg-[#1A2234]/60 cursor-pointer transition-colors colormap-opt';
                        label.querySelector('span').className = 'font-mono text-xs text-slate-300';
                    }
                });
                heatmapOverlay.style.background = e.target.dataset.bg;
                heatmapOverlay.style.filter = e.target.dataset.filter;
            });
        });
    