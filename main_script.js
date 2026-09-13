
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
                
                if (!metadata || !metadata.regions) {
                    document.getElementById('no-inference-overlay').classList.remove('hidden');
                    document.getElementById('analytics-content').style.opacity = '0.3';
                    document.getElementById('analytics-content').style.pointerEvents = 'none';
                    return;
                }

            // Populate Cards
            const fmtNum = (n) => (typeof n === 'number' && isFinite(n)) ? n.toLocaleString() : '--';
            
            const totalAreaSqFt = metadata.total_pixels ? metadata.total_pixels * 1076.39104 : 0;
            const changedAreaSqFt = metadata.changed_pixels ? metadata.changed_pixels * 1076.39104 : 0;
            
            document.getElementById('total-area-val').innerHTML = `${fmtNum(Math.round(totalAreaSqFt))} <span class="text-sm font-normal text-on-surface-variant font-['Inter']">sq ft</span>`;
            document.getElementById('changed-area-val').innerHTML = isSeries ? `<span class="text-on-surface-variant text-sm">-- (Series)</span>` : `${fmtNum(Math.round(changedAreaSqFt))} <span class="text-sm font-normal text-primary/80 font-['Inter']">sq ft</span> <span class="ml-2 text-sm font-normal text-primary/90 font-['Inter']">(${metadata.change_percentage}%)</span>`;
            document.getElementById('clusters-detected-val').innerHTML = `${fmtNum(metadata.num_change_clusters)} <span class="text-sm font-normal text-on-surface-variant font-['Inter']">clusters</span>`;
            document.getElementById('inference-time-val').innerHTML = `${metadata.execution_time_sec} <span class="text-sm font-normal text-on-surface-variant font-['Inter']">s</span>`;

            // Table Generation
            const tbody = document.querySelector('tbody');
            const scanline = document.getElementById('scanline');
            const tableContainer = document.getElementById('table-container');
            
            let allRegions = metadata.regions;
            
            // Recalculate severity dynamically based on updated logic to override cached data
            allRegions.forEach(r => {
                if (r.area_px >= 800) r.severity = 'High';
                else if (r.area_px >= 300) r.severity = 'Medium';
                else r.severity = 'Low';
            });
            
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
                    tr.className = 'hover:bg-primary/5 transition-colors group cursor-pointer';
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
                        <td class="py-3 px-6 text-on-surface font-semibold group-hover:text-primary font-['JetBrains_Mono']">CL-${r.region_id}${timeContext}</td>
                        <td class="py-3 px-6 font-['JetBrains_Mono']">
                            <div class="inline-flex items-center gap-1.5 px-2 py-0.5 border ${sevColor} text-[10px] uppercase tracking-widest font-bold">
                                <div class="w-1.5 h-1.5 rounded-full ${sevDot}"></div> ${r.severity}
                            </div>
                        </td>
                        <td class="py-3 px-6 text-right text-on-surface font-['JetBrains_Mono']">${formattedAreaSqFt}</td>
                        <td class="py-3 px-6 text-right text-on-surface font-['JetBrains_Mono']">${r.mean_change_prob.toFixed(2)}</td>
                        <td class="py-3 px-6 text-on-surface-variant text-xs font-['JetBrains_Mono']">${coordStr}</td>
                        <td class="py-3 px-6"><span class="text-primary hover:underline text-xs">Studio →</span></td>
                    `;
                    tbody.appendChild(tr);
                });
                bindRowClicks();
                
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

            // Zero Detection Simulator (UI Only)
            const zeroToggle = document.getElementById('zero-toggle');
            const zeroState = document.getElementById('zero-state');
            const clusterVal = document.getElementById('clusters-detected-val');
            let isZero = false;
            
            zeroToggle.addEventListener('click', () => {
                isZero = !isZero;
                if (isZero) {
                    zeroToggle.classList.add('bg-primary/20', 'text-primary', 'border-primary/50');
                    zeroState.classList.remove('hidden');
                    tbody.style.opacity = '0';
                    clusterVal.innerHTML = '0 <span class="text-sm font-normal text-on-surface-variant font-[\'Inter\']">clusters</span>';
                    zeroToggle.innerText = 'Disable Zero-Detection (Debug)';
                } else {
                    zeroToggle.classList.remove('bg-primary/20', 'text-primary', 'border-primary/50');
                    zeroState.classList.add('hidden');
                    tbody.style.opacity = '1';
                    clusterVal.innerHTML = `${fmtNum(metadata.num_change_clusters)} <span class="text-sm font-normal text-on-surface-variant font-[\'Inter\']">clusters</span>`;
                    zeroToggle.innerText = 'Simulate Zero-Detection (Debug)';
                }
            });

            // Fly-to animation logic
            const mapCanvas = document.getElementById('map-canvas');
            const coordReadout = document.getElementById('coord-readout');
            const zoomReadout = document.getElementById('zoom-readout');
            const imageSize = metadata.total_pixels ? Math.sqrt(metadata.total_pixels) : 512; // Approximate width/height

            function bindRowClicks() {
                document.querySelectorAll('tbody tr').forEach(row => {
                    row.addEventListener('click', function(e) {
                        if (this.dataset.regionId) {
                            sessionStorage.setItem('target_cluster', this.dataset.regionId);
                            if (this.dataset.pairId) sessionStorage.setItem('target_pair', this.dataset.pairId);
                            window.location.href = 'studio.html';
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
    