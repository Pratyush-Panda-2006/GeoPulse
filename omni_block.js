        const btnInterpret = document.getElementById('btn-interpret');
        const aiPanel = document.getElementById('ai-interpretations-panel');
        if (btnInterpret) {
            btnInterpret.addEventListener('click', async () => {
                if (!lastInferenceResult || !lastInferenceResult.regions || lastInferenceResult.regions.length === 0) {
                    addLog("No regions to analyze.", "warn");
----------------
Match at 2119:
@@ -1295,6 +1400,117 @@
             }
         });

        const btnInterpret = document.getElementById('btn-interpret');
        const aiPanel = document.getElementById('ai-interpretations-panel');
        if (btnInterpret) {
            btnInterpret.addEventListener('click', async () => {
                if (!lastInferenceResult || !lastInferenceResult.regions || lastInferenceResult.regions.length === 0) {
                    addLog("No regions to analyze.", "warn");
                    return;
----------------
Match at 2120:
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
----------------
Match at 2121:
         });

        const btnInterpret = document.getElementById('btn-interpret');
        const aiPanel = document.getElementById('ai-interpretations-panel');
        if (btnInterpret) {
            btnInterpret.addEventListener('click', async () => {
                if (!lastInferenceResult || !lastInferenceResult.regions || lastInferenceResult.regions.length === 0) {
                    addLog("No regions to analyze.", "warn");
                    return;
                }

----------------
Match at 2142:
                    t1_base64: lastInferenceResult.t1_preview_base64,
                    t2_base64: lastInferenceResult.t2_preview_base64,
                    regions: highConfRegions
                };

                btnInterpret.disabled = true;
                btnInterpret.innerHTML = '<span class="material-symbols-outlined text-[14px] animate-spin">refresh</span><span>Analyzing...</span>';
                aiPanel.classList.remove('hidden');
                aiPanel.innerHTML = '<div class="text-white/60 font-mono text-[10px] p-2 text-center">NVIDIA Nemotron is analyzing the scene...</div>';

                if (terminal) terminal.classList.remove('hidden');
----------------
Match at 2143:
                    t2_base64: lastInferenceResult.t2_preview_base64,
                    regions: highConfRegions
                };

                btnInterpret.disabled = true;
                btnInterpret.innerHTML = '<span class="material-symbols-outlined text-[14px] animate-spin">refresh</span><span>Analyzing...</span>';
                aiPanel.classList.remove('hidden');
                aiPanel.innerHTML = '<div class="text-white/60 font-mono text-[10px] p-2 text-center">NVIDIA Nemotron is analyzing the scene...</div>';

                if (terminal) terminal.classList.remove('hidden');
                addLog(`Requesting semantic interpretation for ${highConfRegions.length} regions...`, 'info');
----------------
Match at 2145:
                };

                btnInterpret.disabled = true;
                btnInterpret.innerHTML = '<span class="material-symbols-outlined text-[14px] animate-spin">refresh</span><span>Analyzing...</span>';
                aiPanel.classList.remove('hidden');
                aiPanel.innerHTML = '<div class="text-white/60 font-mono text-[10px] p-2 text-center">NVIDIA Nemotron is analyzing the scene...</div>';

                if (terminal) terminal.classList.remove('hidden');
                addLog(`Requesting semantic interpretation for ${highConfRegions.length} regions...`, 'info');

                try {
----------------
Match at 2148:
                btnInterpret.innerHTML = '<span class="material-symbols-outlined text-[14px] animate-spin">refresh</span><span>Analyzing...</span>';
                aiPanel.classList.remove('hidden');
                aiPanel.innerHTML = '<div class="text-white/60 font-mono text-[10px] p-2 text-center">NVIDIA Nemotron is analyzing the scene...</div>';

                if (terminal) terminal.classList.remove('hidden');
                addLog(`Requesting semantic interpretation for ${highConfRegions.length} regions...`, 'info');

                try {
                    const res = await fetch(apiBase + '/api/v1/detect/interpret', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
----------------
Match at 2151:

                if (terminal) terminal.classList.remove('hidden');
                addLog(`Requesting semantic interpretation for ${highConfRegions.length} regions...`, 'info');

                try {
                    const res = await fetch(apiBase + '/api/v1/detect/interpret', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify(payload)
                    });

----------------
Match at 2163:
                        const err = await res.json().catch(() => ({}));
                        throw new Error(err.detail || `Server error: ${res.status}`);
                    }

                    const data = await res.json();
                    const interpretations = data.interpretations;

                    aiPanel.innerHTML = '';
                    if (Object.keys(interpretations).length === 0) {
                        aiPanel.innerHTML = '<div class="text-white/60 font-mono text-[10px] p-2 text-center">No conclusive interpretations.</div>';
                        addLog('AI returned no conclusive interpretations.', 'warn');
----------------
Match at 2166:

                    const data = await res.json();
                    const interpretations = data.interpretations;

                    aiPanel.innerHTML = '';
                    if (Object.keys(interpretations).length === 0) {
                        aiPanel.innerHTML = '<div class="text-white/60 font-mono text-[10px] p-2 text-center">No conclusive interpretations.</div>';
                        addLog('AI returned no conclusive interpretations.', 'warn');
                    } else {
                        let html = '';
                        Object.keys(interpretations).forEach(regId => {
----------------
Match at 2167:
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
----------------
Match at 2168:
                    const interpretations = data.interpretations;

                    aiPanel.innerHTML = '';
                    if (Object.keys(interpretations).length === 0) {
                        aiPanel.innerHTML = '<div class="text-white/60 font-mono text-[10px] p-2 text-center">No conclusive interpretations.</div>';
                        addLog('AI returned no conclusive interpretations.', 'warn');
                    } else {
                        let html = '';
                        Object.keys(interpretations).forEach(regId => {
                            const val = interpretations[regId];

----------------
Match at 2171:
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
----------------
Match at 2172:
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
----------------
Match at 2178:

                            if (val.status === 'unavailable') {
                                html += `
                                <div class="bg-red-500/10 border border-red-500/30 p-2 rounded-lg">
                                    <div class="text-red-400 font-mono text-[10px] mb-1 font-bold">Region ${val.region_id}</div>
                                    <div class="text-white/60 text-[10px] font-sans">NVIDIA Nemotron Unavailable</div>
                                </div>`;
                                return;
                            }

                            if (val.status === 'skipped_small_crop') {
----------------
Match at 2216:
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
----------------
Match at 2222:
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