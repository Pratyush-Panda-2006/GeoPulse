# GeoPulse - SAR Earth Observation & Environmental Monitoring Suite

A unified multi-temporal Synthetic Aperture Radar (SAR) intelligence platform designed for deforestation tracking, wetland & coastal dynamics, climate surface shifts, 3D habitat split analysis, and satellite telemetry.

---

## Interconnected Suite Modules

All views are connected with universal global navigation, quick action launchpads, and live status routing:

| Page | Module | Key Features |
| :--- | :--- | :--- |
| [`index.html`](file:///Frontend/index.html) / [`explorer.html`](file:///Frontend/explorer.html) | **Biosphere SAR Explorer** | Multi-temporal acquisition controls (T1 baseline / T2 observation dates), draggable Biome ROI bounding box with live area calculation, live radar sweep, coordinate HUD reticle, radiometric calibration terminal logs, saved biome presets. |
| [`overview.html`](file:///Frontend/overview.html) | **Eco-Intelligence Center** | Strategic environmental dashboard, biome surveillance readiness, observation tracker, ecological disturbance zones (Alpha: Canopy Depletion, Beta: Mangrove/Coastal Inundation, Gamma: Surface Water Shrinkage) with routing to audit, executive ecosystem metrics, radar sweep animations. |
| [`studio.html`](file:///Frontend/studio.html) | **3D Terrain Studio** | Interactive before/after split-view slider (T1 baseline vs. T2 AI disturbance mask), colormap toggles (Turbo, Viridis, Binary Red), layer opacity/brightness/contrast controls, radiometric speckle filter alerts. |
| [`analytics.html`](file:///Frontend/analytics.html) | **Disturbance Audit & Analytics** | Interactive disturbance zone table with GSAP-powered fly-to map navigation, impact level filter buttons (Severe Loss, High Shift, Moderate Shift), zero-disturbance simulation toggle, export actions (PDF, GeoJSON, CSV), and live coordinate readouts. |
| [`telemetry.html`](file:///Frontend/telemetry.html) | **RISAT-2B / EOS-04 Telemetry Hub** | Real-time IST clock, dynamic downlink latency jitter readout, GPU VRAM allocation monitor, CUDA RTX compute specs, and historical 7-day system uptime telemetry. |

---

## Suite Directory Structure

```
Frontend/
├── index.html          # Main entry point (Biosphere SAR Explorer)
├── explorer.html       # Direct alias to Biosphere Explorer
├── overview.html       # Eco-Intelligence Center Overview Dashboard
├── studio.html         # 3D Terrain Habitat Split-View Studio
├── analytics.html      # SAR Disturbance Audit & Analytics Table
├── telemetry.html      # RISAT-2B / EOS-04 Real-time Telemetry & Health Hub
├── README.md           # Documentation & Navigation Map
└── assets/             # Scripts, styles, demo samples, and screenshots
```

