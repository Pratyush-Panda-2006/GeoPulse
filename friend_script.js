
        (function initAnalytics() {
            try {
                const seriesData = SARStore.loadTimeSeries();
                const pairwiseData = SARStore.loadMetadata();
                
                let metadata = null;
                let isSeries = false;
                
                if (seriesData) {
                    isSeries = true;
                    let totalClusters = 0;
                    let allRegions = [];
                    
                    if (seriesData.result) {
                        const pair = seriesData.result;
                        totalClusters = pair.num_change_clusters || 0;
                        if (pair.regions) {
                            pair.regions.forEach(r => {
                                r._t1_date = pair.t1_acquisition.acquisition_date;
                                r._t2_date = pair.t2_acquisition.acquisition_date;
                                r._pair_job_id = pair.job_id;
                                allRegions.push(r);
                            });
                        }
                    }
                    
                    metadata = {
                        is_series: true,
                        total_pixels: 512 * 512, // Approximation for UI
                        changed_pixels: 0,
                        change_percentage: '--',
                        num_change_clusters: totalClusters,
                        execution_time_sec: seriesData.execution_time_sec,
                        regions: allRegions
                    };
                    
                    // Update header title
                    const headerEl = document.querySelector('h2.text-headline-md');
                    if (headerEl) headerEl.innerHTML = `<span class="material-symbols-outlined text-[#c487ff]" data-icon="stacked_line_chart">stacked_line_chart</span> Period Inspector`;
                    
                } else if (pairwiseData) {
                    metadata = pairwiseData;
                }
                
                // Fallback default demo data if no active inference is in memory
                if (!metadata || !metadata.regions || metadata.regions.length === 0) {
                    metadata = {
                        job_id: "demo_03_chongqing",
                        status: "success",
                        model_used: "snunet_cd_sar",
                        execution_time_sec: 1.48,
                        total_pixels: 512 * 512,
                        changed_pixels: 919,
                        change_percentage: "0.156",
                        num_change_clusters: 10,
                        regions: [
                            { region_id: 1, area_px: 248, area_km2: 0.0248, centroid_xy: [180.4, 210.2], geo_centroid: [106.5510, 29.5630], mean_change_prob: 0.962, severity: 'High' },
                            { region_id: 2, area_px: 195, area_km2: 0.0195, centroid_xy: [240.8, 175.6], geo_centroid: [106.5642, 29.5714], mean_change_prob: 0.954, severity: 'High' },
                            { region_id: 3, area_px: 142, area_km2: 0.0142, centroid_xy: [310.2, 290.5], geo_centroid: [106.5780, 29.5490], mean_change_prob: 0.938, severity: 'Medium' },
                            { region_id: 4, area_px: 110, area_km2: 0.0110, centroid_xy: [145.6, 340.1], geo_centroid: [106.5420, 29.5380], mean_change_prob: 0.912, severity: 'Medium' },
                            { region_id: 5, area_px: 88,  area_km2: 0.0088, centroid_xy: [390.5, 160.3], geo_centroid: [106.5910, 29.5740], mean_change_prob: 0.895, severity: 'Low' },
                            { region_id: 6, area_px: 62,  area_km2: 0.0062, centroid_xy: [215.1, 410.8], geo_centroid: [106.5580, 29.5220], mean_change_prob: 0.874, severity: 'Low' },
                            { region_id: 7, area_px: 36,  area_km2: 0.0036, centroid_xy: [280.9, 120.4], geo_centroid: [106.5720, 29.5820], mean_change_prob: 0.846, severity: 'Low' },
                            { region_id: 8, area_px: 21,  area_km2: 0.0021, centroid_xy: [440.2, 260.7], geo_centroid: [106.6020, 29.5550], mean_change_prob: 0.825, severity: 'Low' },
                            { region_id: 9, area_px: 12,  area_km2: 0.0012, centroid_xy: [110.8, 190.2], geo_centroid: [106.5350, 29.5670], mean_change_prob: 0.798, severity: 'Low' },
                            { region_id: 10, area_px: 5,  area_km2: 0.0005, centroid_xy: [360.4, 380.9], geo_centroid: [106.5860, 29.5290], mean_change_prob: 0.781, severity: 'Low' }
                        ]
                    };
                }

            // Populate Cards
            const fmtNum = (n) => (typeof n === 'number' && isFinite(n)) ? n.toLocaleString() : '--';
            
            const totalAreaSqFt = metadata.total_pixels ? metadata.total_pixels * 1076.39104 : 0;
            const changedAreaSqFt = metadata.changed_pixels ? metadata.changed_pixels * 1076.39104 : 0;
            
            document.getElementById('total-area-val').innerHTML = `${fmtNum(Math.round(totalAreaSqFt))} <span class="text-sm font-normal text-on-surface-variant font-['Inter']">sq ft</span>`;
            document.getElementById('changed-area-val').innerHTML = isSeries ? `<span class="text-on-surface-variant text-sm">-- (Series)</span>` : `${fmtNum(Math.round(changedAreaSqFt))} <span class="text-sm font-normal text-primary/80 font-['Inter']">sq ft</span> <span class="ml-2 text-sm font-normal text-primary/90 font-['Inter']">(${metadata.change_percentage}%)</span>`;
            document.getElementById('clusters-detected-val').innerHTML = `${fmtNum(metadata.num_change_clusters)} <span class="text-sm font-normal text-on-surface-variant font-['Inter']">clusters</span>`;
            document.getElementById('inference-time-val').innerHTML = `${metadata.execution_time_sec} <span class="text-sm font-normal text-on-surface-variant font-['Inter']">s</span>`;

            // Table Generation & Spotlight Setup
            const tbody = document.querySelector('tbody');
            const scanline = document.getElementById('scanline');
            const tableContainer = document.getElementById('table-container');
            const mapCanvas = document.getElementById('map-canvas');
            const coordReadout = document.getElementById('coord-readout');
            const zoomReadout = document.getElementById('zoom-readout');
            const radarContainer = document.getElementById('radar-clusters-container');
            
            let allRegions = metadata.regions;
            
            // Recalculate severity dynamically based on area
            allRegions.forEach(r => {
                if (r.area_px >= 200) r.severity = 'High';
                else if (r.area_px >= 130) r.severity = 'Medium';
                else r.severity = 'Low';
            });

            // Render Tactical Radar Dots
            const renderRadarBeacons = (regions) => {
                if (!radarContainer) return;
                radarContainer.innerHTML = '';
                regions.forEach(r => {
                    const dot = document.createElement('div');
                    const nx = Math.min(Math.max((r.centroid_xy[0] / 512) * 100, 8), 92);
                    const ny = Math.min(Math.max((r.centroid_xy[1] / 512) * 100, 8), 92);
                    const dotColor = r.severity === 'High' ? 'bg-[#ff453a] shadow-[0_0_8px_rgba(255,69,58,0.9)]' : 
                                     r.severity === 'Medium' ? 'bg-[#ffd60a] shadow-[0_0_8px_rgba(255,214,10,0.9)]' : 
                                     'bg-primary shadow-[0_0_8px_rgba(78,222,163,0.9)]';
                    dot.className = `absolute w-3 h-3 -translate-x-1/2 -translate-y-1/2 rounded-full cursor-pointer hover:scale-150 transition-all z-10 flex items-center justify-center group ${dotColor}`;
                    dot.style.left = `${nx}%`;
                    dot.style.top = `${ny}%`;
                    dot.title = `CL-${r.region_id} (${r.severity})`;
                    dot.dataset.regionId = r.region_id;
                    dot.innerHTML = `<span class="opacity-0 group-hover:opacity-100 absolute -top-5 text-[9px] font-mono px-1 py-0.5 bg-black/90 text-white rounded pointer-events-none transition-opacity">CL-${r.region_id}</span>`;
                    dot.onclick = (e) => {
                        e.stopPropagation();
                        selectCluster(r.region_id, true);
                    };
                    radarContainer.appendChild(dot);
                });
            };

            // Smooth Cluster Selection and Fly-To
            function selectCluster(regionId, smoothScrollTable = false) {
                const region = allRegions.find(r => String(r.region_id) === String(regionId));
                if (!region) return;

                // 1. Highlight clicked row in the table smoothly
                document.querySelectorAll('tbody tr').forEach(tr => {
                    if (String(tr.dataset.regionId) === String(regionId)) {
                        tr.className = 'bg-primary/20 border-l-4 border-primary text-white shadow-[0_0_20px_rgba(78,222,163,0.3)] transition-all duration-300 group cursor-pointer';
                        if (smoothScrollTable) {
                            tr.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
                        }
                    } else {
                        tr.className = 'hover:bg-primary/5 transition-colors group cursor-pointer border-l-4 border-transparent';
                    }
                });

                // 2. Smoothly fly reticle to cluster coordinates on the radar viewport
                const reticle = document.getElementById('radar-reticle');
                if (reticle) {
                    reticle.classList.remove('hidden');
                    const nx = Math.min(Math.max((region.centroid_xy[0] / 512) * 100, 8), 92);
                    const ny = Math.min(Math.max((region.centroid_xy[1] / 512) * 100, 8), 92);
                    gsap.to(reticle, {
                        left: `${nx}%`,
                        top: `${ny}%`,
                        duration: 0.6,
                        ease: "power2.out"
                    });
                }

                // 3. Smoothly pan & zoom the background map canvas with GSAP
                if (mapCanvas) {
                    const normX = Math.min(Math.max((region.centroid_xy[0] / 512) * 100, 10), 90);
                    const normY = Math.min(Math.max((region.centroid_xy[1] / 512) * 100, 10), 90);
                    gsap.to(mapCanvas, {
                        scale: 1.35,
                        transformOrigin: `${normX}% ${normY}%`,
                        duration: 1.1,
                        ease: "power2.out"
                    });
                }

                // 4. Update Spotlight details card
                const spotId = document.getElementById('spotlight-id');
                const spotCoords = document.getElementById('spotlight-coords');
                const spotArea = document.getElementById('spotlight-area');
                const spotProb = document.getElementById('spotlight-prob');
                const spotSev = document.getElementById('spotlight-severity');
                const spotBtn = document.getElementById('spotlight-btn-studio');
                const spotBadge = document.getElementById('spotlight-badge');
                
                const coordStr = region.geo_centroid ? `${region.geo_centroid[1].toFixed(4)}° N, ${region.geo_centroid[0].toFixed(4)}° E` : `[Px: ${Math.round(region.centroid_xy[0])}, ${Math.round(region.centroid_xy[1])}]`;
                
                let areaSqFt = 0;
                if (region.area_km2) areaSqFt = region.area_km2 * 10763910.4;
                else if (region.approx_area_sq_km) areaSqFt = region.approx_area_sq_km * 10763910.4;
                else areaSqFt = region.area_px * 1076.39104;

                if (spotId) spotId.textContent = `CL-${region.region_id}`;
                if (spotCoords) spotCoords.textContent = coordStr;
                if (spotArea) spotArea.textContent = `${Math.round(areaSqFt).toLocaleString()} sq ft`;
                if (spotProb) spotProb.textContent = `${(region.mean_change_prob * 100).toFixed(1)}%`;
                if (spotBadge) {
                    spotBadge.textContent = `LOCKED: CL-${region.region_id}`;
                    spotBadge.className = 'px-2 py-0.5 rounded-full bg-primary/25 border border-primary text-primary font-mono text-[10px] uppercase font-bold shadow-[0_0_8px_rgba(78,222,163,0.4)]';
                }
                if (spotSev) {
                    spotSev.textContent = region.severity || 'Medium';
                    spotSev.className = region.severity === 'High' ? 'inline-flex items-center gap-1 px-2 py-0.5 border border-[#ff453a]/50 bg-[#ff453a]/15 text-[#ff453a] font-mono text-[10px] uppercase font-bold rounded shadow-[0_0_8px_rgba(255,69,58,0.3)]' :
                                        region.severity === 'Medium' ? 'inline-flex items-center gap-1 px-2 py-0.5 border border-[#ffd60a]/50 bg-[#ffd60a]/15 text-[#ffd60a] font-mono text-[10px] uppercase font-bold rounded shadow-[0_0_8px_rgba(255,214,10,0.3)]' :
                                        'inline-flex items-center gap-1 px-2 py-0.5 border border-primary/40 bg-primary/10 text-primary font-mono text-[10px] uppercase font-bold rounded shadow-[0_0_8px_rgba(78,222,163,0.3)]';
                }

                if (spotBtn) {
                    spotBtn.onclick = () => {
                        sessionStorage.setItem('target_cluster', region.region_id);
                        sessionStorage.setItem('target_cluster_data', JSON.stringify(region));
                        if (region._pair_job_id) sessionStorage.setItem('target_pair', region._pair_job_id);
                        window.location.href = `studio.html?cluster=${region.region_id}`;
                    };
                }

                // 5. Update bottom HUD readout
                if (coordReadout) {
                    coordReadout.innerHTML = `<span class="material-symbols-outlined text-[16px] text-primary" data-icon="my_location">my_location</span> <span class="text-primary font-bold">CLUSTER: CL-${region.region_id}</span> <span class="text-white/80">(${coordStr})</span>`;
                }
                if (zoomReadout) {
                    zoomReadout.innerHTML = `<span class="text-primary font-bold">ZOOM: 18.5x [ENGAGED]</span>`;
                }
            }
            
            const renderTable = (regions) => {
                tbody.innerHTML = '';
                regions.forEach(r => {
                    const cx = r.centroid_xy[0].toFixed(1);
                    const cy = r.centroid_xy[1].toFixed(1);
                    const coordStr = r.geo_centroid ? `${r.geo_centroid[1].toFixed(4)}° N, ${r.geo_centroid[0].toFixed(4)}° E` : `[Px: ${Math.round(r.centroid_xy[0])}, ${Math.round(r.centroid_xy[1])}]`;
                    
                    const sevColor = r.severity === 'High' ? 'text-[#ff453a] border-[#ff453a]/50 bg-[#ff453a]/10' : 
                                     r.severity === 'Medium' ? 'text-[#ffd60a] border-[#ffd60a]/50 bg-[#ffd60a]/10' : 
                                     'text-outline border-outline/50 bg-outline/10';
                                     
                    const sevDot = r.severity === 'High' ? 'bg-[#ff453a] pulse-tactical' : 
                                   r.severity === 'Medium' ? 'bg-[#ffd60a]' : 'bg-outline';

                    const tr = document.createElement('tr');
                    tr.className = 'hover:bg-primary/5 transition-colors group cursor-pointer border-l-4 border-transparent';
                    tr.dataset.cx = r.centroid_xy[0];
                    tr.dataset.cy = r.centroid_xy[1];
                    tr.dataset.coordStr = coordStr;
                    tr.dataset.regionId = r.region_id;
                    if (isSeries) tr.dataset.pairId = r._pair_job_id;
                    
                    const timeContext = isSeries && r._t1_date ? `<div class="text-[9px] text-[#c487ff] mt-1">${r._t1_date} <span class="text-outline">→</span> ${r._t2_date}</div>` : '';
                    
                    let areaSqFt = 0;
                    if (r.area_km2) areaSqFt = r.area_km2 * 10763910.4;
                    else if (r.approx_area_sq_km) areaSqFt = r.approx_area_sq_km * 10763910.4;
                    else areaSqFt = r.area_px * 1076.39104;
                    const formattedAreaSqFt = Math.round(areaSqFt).toLocaleString();
                    
                    tr.innerHTML = `
                        <td class="py-3 px-6 text-on-surface font-semibold group-hover:text-primary font-['JetBrains_Mono']">
                            <span class="cluster-id-badge inline-flex items-center gap-1 hover:text-primary transition-colors">CL-${r.region_id}</span>
                            ${timeContext}
                        </td>
                        <td class="py-3 px-6 font-['JetBrains_Mono']">
                            <div class="inline-flex items-center gap-1.5 px-2 py-0.5 border ${sevColor} text-[10px] uppercase tracking-widest font-bold">
                                <div class="w-1.5 h-1.5 rounded-full ${sevDot}"></div> ${r.severity}
                            </div>
                        </td>
                        <td class="py-3 px-6 text-right text-on-surface font-['JetBrains_Mono']">${formattedAreaSqFt}</td>
                        <td class="py-3 px-6 text-right text-on-surface font-['JetBrains_Mono']">${r.mean_change_prob.toFixed(2)}</td>
                        <td class="py-3 px-6 text-on-surface-variant text-xs font-['JetBrains_Mono']">${coordStr}</td>
                        <td class="py-3 px-6">
                            <button class="open-studio-btn inline-flex items-center gap-1.5 px-2.5 py-1 bg-primary/15 hover:bg-primary/30 border border-primary/40 hover:border-primary text-primary text-xs font-mono font-bold rounded transition-all shadow-[0_0_10px_rgba(78,222,163,0.15)] group-hover:shadow-[0_0_12px_rgba(78,222,163,0.35)]" title="Inspect CL-${r.region_id} in 3D Studio">
                                <span>Studio</span>
                                <span class="material-symbols-outlined text-[13px]">arrow_forward</span>
                            </button>
                        </td>
                    `;
                    tbody.appendChild(tr);
                });
                bindRowClicks();
                renderRadarBeacons(regions);

                // Auto-select first cluster
                if (regions.length > 0) {
                    selectCluster(regions[0].region_id);
                }
                
                // Animate rows
                const rows = document.querySelectorAll('tbody tr');
                if (rows.length > 0) {
                    gsap.fromTo(rows,
                        { opacity: 0.5, x: -10 },
                        { opacity: 1, x: 0, duration: 0.4, stagger: 0.02, ease: "power1.out" }
                    );
                }
            };
            
            renderTable(allRegions);

            // Filter logic
            let activeSeverity = null;
            document.querySelectorAll('.filter-btn').forEach(btn => {
                btn.addEventListener('click', (e) => {
                    gsap.fromTo(scanline, 
                        { top: 0, opacity: 1 },
                        { top: tableContainer.offsetHeight, opacity: 0, duration: 1.2, ease: "power2.inOut" }
                    );

                    const txt = e.target.innerText.toLowerCase();
                    if (txt.includes('high')) activeSeverity = 'High';
                    else if (txt.includes('medium')) activeSeverity = 'Medium';
                    else if (txt.includes('low')) activeSeverity = 'Low';
                    else activeSeverity = null;
                    
                    if (activeSeverity) {
                        renderTable(allRegions.filter(r => r.severity === activeSeverity));
                    } else {
                        renderTable(allRegions);
                    }
                });
            });



            function bindRowClicks() {
                document.querySelectorAll('tbody tr').forEach(row => {
                    row.addEventListener('click', function(e) {
                        const studioBtn = e.target.closest('.open-studio-btn') || (e.target.innerText && e.target.innerText.includes('Studio'));
                        const rId = this.dataset.regionId;
                        const region = allRegions.find(r => String(r.region_id) === String(rId));
                        
                        if (studioBtn) {
                            e.stopPropagation();
                            if (rId && region) {
                                sessionStorage.setItem('target_cluster', rId);
                                sessionStorage.setItem('target_cluster_data', JSON.stringify(region));
                                if (this.dataset.pairId) sessionStorage.setItem('target_pair', this.dataset.pairId);
                                window.location.href = `studio.html?cluster=${rId}`;
                            }
                            return;
                        }
                        
                        if (rId) {
                            selectCluster(rId, false);
                        }
                    });

                    // Double-clicking anywhere on row navigates directly to Studio for that cluster
                    row.addEventListener('dblclick', function(e) {
                        const rId = this.dataset.regionId;
                        const region = allRegions.find(r => String(r.region_id) === String(rId));
                        if (rId && region) {
                            sessionStorage.setItem('target_cluster', rId);
                            sessionStorage.setItem('target_cluster_data', JSON.stringify(region));
                            if (this.dataset.pairId) sessionStorage.setItem('target_pair', this.dataset.pairId);
                            window.location.href = `studio.html?cluster=${rId}`;
                        }
                    });
                });
            }

            // GeoJSON Export Logic
            const geojsonBtn = document.getElementById('export-geojson');
            if (geojsonBtn) {
                geojsonBtn.addEventListener('click', () => {
                    if (metadata.job_id) {
                        const apiBase = (window.SARStore && SARStore.getApiBase) ? SARStore.getApiBase() : 'http://127.0.0.1:8000';
                        const url = `${apiBase}/api/v1/detect/${metadata.job_id}/detections.geojson`;
                        const a = document.createElement('a');
                        a.href = url;
                        a.download = `detections_${metadata.job_id}.geojson`;
                        document.body.appendChild(a);
                        a.click();
                        document.body.removeChild(a);
                    } else {
                        alert('No job ID found for the current inference result. GeoJSON export is unavailable.');
                    }
                });
            }
            } catch (err) {
                console.error("Analytics initialization error:", err);
            }
        })();
    