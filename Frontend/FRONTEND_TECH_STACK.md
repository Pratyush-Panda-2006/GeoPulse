# GeoPulse Frontend — Technology Stack & Architecture Specification

A comprehensive technical reference documenting all technologies, frameworks, libraries, multimedia streams, audio synthesis, state management, and geospatial visualizers used in the **GeoPulse Frontend Suite**.

---

## 1. Architectural Overview

The GeoPulse frontend employs a **hybrid dual-tier architecture**:

1. **Mission-Critical Multi-Page Application (MPA)**:
   - Hosted on `http://localhost:3000` via a custom multi-threaded Python server (`serve.py`).
   - Powers 6 interconnected defense and satellite intelligence views with zero build step requirement for instant runtime triage.
2. **React 19 + Vite 8 Parallax Sub-Application**:
   - Hosted on `http://localhost:5173` in `Frontend/react-parallax/`.
   - Demonstrates modern component-driven telemetry and 3D terrain parallax layering.

```text
GeoPulse Frontend Suite
├── Core MPA Modules (Port 3000)
│   ├── index.html / explorer.html  ──► Multi-Temporal SAR Explorer & CDSE Ingest
│   ├── studio.html                 ──► 3D Geospatial Triage Studio & Split Comparison
│   ├── analytics.html              ──► Tactical Cluster Inspector & Anomaly Radar
│   ├── overview.html               ──► Strategic Defense Command Dashboard
│   ├── intelligence.html           ──► AI Semantic Interpretation (SNUNet + Nemotron)
│   ├── telemetry.html              ──► CDSE Downlink & GPU Compute Health Hub
│   ├── assets/sar-store.js         ──► Dual-Tier Persistence Engine (IndexedDB + SessionStorage)
│   └── serve.py                    ──► Clean-URL Threaded Web Server
└── React 19 Parallax Sub-App (Port 5173)
    ├── Vite 8 + TypeScript 6 + Tailwind v4
    ├── 3D Multi-Layer Wilderness Parallax Engine
    ├── CSS 3D Earth Globe Rotation Engine
    └── Real-Time Live Telemetry HUD
```

---

## 2. Technologies, Frameworks & Libraries

### A. Core Platform & Runtime
| Technology | Version / Source | Purpose |
| :--- | :--- | :--- |
| **HTML5** | W3C Standard | Semantic markup, canvas elements, video & audio embeddings |
| **CSS3** | Modern Specification | Glassmorphism (`backdrop-filter`), CSS variables, custom clip-paths |
| **Vanilla JavaScript** | ECMAScript 2024 (ES6+) | DOM manipulation, coordinate math, event loops, async fetch |
| **React** | `v19.2.8` | Reactive UI components in the Parallax / Telemetry app |
| **TypeScript** | `~6.0.2` | Strong type definitions for geospatial layers and telemetry state |
| **Vite** | `v8.2.2` | Hot Module Replacement (HMR) development server and bundler |
| **Python** | `3.10+` | Built-in `http.server` with custom clean URL routing (`serve.py`) |
| **Oxlint** | `v1.79.0` | High-speed JavaScript and TypeScript linting |

### B. Styling & Design Systems
| Library | Source | Usage |
| :--- | :--- | :--- |
| **Tailwind CSS (CDN)** | `cdn.tailwindcss.com` | Rapid utility styling across core HTML pages |
| **Tailwind Forms Plugin** | `?plugins=forms` | Tactical styled range sliders, inputs, checkboxes |
| **Tailwind Container Queries** | `?plugins=container-queries` | Responsive metric cards and modular sidebar layouts |
| **Tailwind CSS v4** | `@tailwindcss/postcss ^4.3.3` | PostCSS-based styling in the React sub-application |
| **Autoprefixer & PostCSS** | PostCSS `^8.5.26` | Cross-browser CSS prefixing |

### C. Motion & Animation Engines
| Engine | Version | Usage |
| :--- | :--- | :--- |
| **GSAP (GreenSock)** | `v3.12.2` | Camera zoom interpolation, cluster fly-to transforms, radar crosshair motion, row staggers |
| **Web Animations API** | Native Browser | Looping radar beam sweeps, pulse beacons, scanline passes |
| **CSS Keyframes** | Native CSS | Planetary rotation, reticle pinging, atmospheric flickering |

---

## 3. Multimedia, Video & Audio Assets

### A. Full-Bleed Orbital Video
- **Location**: [`explorer.html`](file:///e:/GeoPluse/GeoPulse/Frontend/explorer.html)
- **Source**: `https://d8j0ntlcm91z4.cloudfront.net/user_38xzZboKViGWJOttwIXH07lWA1P/hf_20260315_073750_51473149-4350-4920-ae24-c8214286f323.mp4`
- **Format**: H.264 / MP4 (HTML5 `<video>`)
- **Parameters**: `autoplay`, `muted`, `loop`, `playsinline`, `preload="auto"`
- **Optical Vignette**:
  ```css
  background: radial-gradient(ellipse at center, rgba(10, 15, 29, 0.45) 0%, rgba(5, 8, 16, 0.85) 100%);
  ```

### B. Procedural CSS 3D Earth Globe
- **Location**: [`globe.tsx`](file:///e:/GeoPluse/GeoPulse/Frontend/react-parallax/src/components/ui/globe.tsx)
- **Planetary Texture**: `https://pub-940ccf6255b54fa799a9b01050e6c227.r2.dev/globe.jpeg`
- **Volumetric Shading**: 6-level inset box shadow creating spherical atmospheric depth and horizon glow:
  ```css
  box-shadow: 0 0 40px rgba(255,255,255,0.2), -10px 0 16px #c3f4ff inset, 30px 4px 50px #000 inset, -48px -4px 68px #c3f4ff99 inset, 500px 0 88px #00000066 inset, 300px 0 76px #000000aa inset;
  ```

### C. Multi-Plane Wilderness Parallax Assets
- **Location**: [`wilderness.tsx`](file:///e:/GeoPluse/GeoPulse/Frontend/react-parallax/src/components/ui/wilderness.tsx)
- **Panoramic Vista**: `https://images.unsplash.com/photo-1519681393784-d120267933ba`
- **Atmospheric Fog Layers**:
  - `https://i.ibb.co/DHhNwG0X/fog-7.png`
  - `https://i.ibb.co/rW6cjXV/fog-6.png`
- **Mountain Topography Layers**:
  - `https://i.ibb.co/4gT3LR9K/mountain-10.png`
  - `https://i.ibb.co/zHWDdxRR/mountain-9.png`

### D. Tactical Sound Synthesis (Web Audio API)
- **Location**: [`overview.html`](file:///e:/GeoPluse/GeoPulse/Frontend/overview.html)
- **Engine**: Browser-native `window.AudioContext`
- **Mechanics**: Zero external MP3/WAV files required. Programmatically generates an 800 Hz to 400 Hz exponential frequency drop over 50 ms with an exponential gain decay (`0.02` to `0.001`), producing a distinct military tactile click on `.synth-click` elements.

### E. Tactical Map & Noise Textures
- **India Border Tactical Map**:
  - `https://lh3.googleusercontent.com/aida-public/AB6AXuDBipvc13muhDU84O-GEV1lXzNJLdVGGZMDHVYs-ClBsbz5_jsoOw7toHUCCNDpUhEWbA62Y2u7JH1f7RVxYSACdkqxkyURQhw5rMILekseMAJwpo3DNKIEP0RZaljGWZFJNSt0KRZmgrnDH_v1y_7ZhS7R_yDJLcJE15D_FE7FH9VckUK2UQ2bxrysnNF9PxvA9iGUAQdVFAo5ZDqGpBf7IC_7uHftsW-kXq3fAtNFHNA0YwQUMcbD`
- **Fractal Noise Film Grain**: Procedural SVG `feTurbulence` filter (4% opacity) layered over the viewport.

---

## 4. Typography & Iconography

| Asset | Source | Weights / Formats | Purpose |
| :--- | :--- | :--- | :--- |
| **Bricolage Grotesque** | Google Fonts | `700`, `800` | High-impact tactical headers and branding |
| **Inter** | Google Fonts | `400`, `500`, `600`, `700` | Primary application typography and data grids |
| **JetBrains Mono** | Google Fonts | `400`, `500`, `700` | Coordinate readouts, dB metrics, timestamps, telemetry |
| **Playfair Display** | Google Fonts | `Italic` | Tactical accent sub-headings |
| **Material Symbols Outlined** | Google Fonts | Variable (`FILL 0..1`, `wght 100..700`) | Navigation, toolbar, and sensor icons |
| **Lucide React** | NPM Package | SVG Components | React telemetry and HUD icons |

---

## 5. Client State Management & Persistence (`sar-store.js`)

Located in [`Frontend/assets/sar-store.js`](file:///e:/GeoPluse/GeoPulse/Frontend/assets/sar-store.js), this module manages cross-page state without a heavyweight Redux or Vuex dependency:

```
┌────────────────────────────────────────────────────────┐
│               Inference Pipeline Result                │
└──────────────────────────┬─────────────────────────────┘
                           │
             ┌─────────────┴─────────────┐
             ▼                           ▼
 ┌──────────────────────┐    ┌──────────────────────────┐
 │ Compact JSON Metadata│    │ Large Base64 Previews    │
 │ (job_id, threshold,  │    │ (t1, t2, mask, heatmap,  │
 │  regions, centroids) │    │  overlay, boxes)         │
 └──────────┬───────────┘    └──────────┬───────────────┘
            │                           │
            ▼                           ▼
 ┌──────────────────────┐    ┌──────────────────────────┐
 │    sessionStorage    │    │        IndexedDB         │
 │     (sar_results)    │    │  (sar_intel -> previews) │
 └──────────────────────┘    └──────────────────────────┘
```

1. **`sessionStorage` (`sar_results`)**:
   - Stores strictly compact metadata to eliminate quota overflow risks.
2. **`IndexedDB` (`sar_intel` DB / `previews` store)**:
   - Persists high-resolution multi-temporal base64 rasters (`t1`, `t2`, `mask`, `heatmap`, `overlay`, `boxes`).
3. **In-Memory Cache**:
   - Delivers synchronous, instant layer switching on the active page.
4. **URL Query Routing**:
   - Supports deep linking: `studio.html?cluster=1`, `explorer.html?scene=03_chongqing`, `?api=http://127.0.0.1:8000`.

---

## 6. Viewport Components & Geospatial Tools

1. **Interactive Before/After Split Curtain**:
   - Pointer-captured vertical curtain dragging divider with dynamic SVG grip and synchronized CSS `clip-path: polygon(...)`.
2. **Draggable & Rotatable Azimuth Compass HUD**:
   - Interactive 360° SVG dial with red North / slate South needles and dynamic 16-point cardinal telemetry (e.g. `045° NE`).
3. **Cartographic Graticule & Dynamic Ground Scale**:
   - Cursor hover tracking calibrated to WGS84 UTM 43N coordinates with simulated radar reflectance values (`-14.2 dB`).
4. **Tactical Mini-Radar Viewport**:
   - Concentric range rings, beacon dots, and an animated crosshair reticle for targeting anomaly clusters.
5. **Multi-Spectral / Radiometric Colormap Engine**:
   - Dynamic switching between **Turbo (Scientific)**, **Viridis (Perceptual)**, and **Binary Red (High-Alert)** scales.

---

## 7. Backend REST API Integration

The frontend communicates with a high-performance **FastAPI backend** running on port 8000:

| HTTP Method | Route | Description |
| :--- | :--- | :--- |
| `POST` | `/api/v1/detect/change-detection` | Multi-temporal GeoTIFF pair inference via the SNUNet-CD engine |
| `POST` | `/api/v1/detect/sentinel` | Direct bounding-box ingestion of Sentinel-1 Level-1 GRD tiles via CDSE |
| `GET` | `/api/v1/detect/{job_id}/detections.geojson` | GeoJSON export of detected surface anomaly polygons |
| `GET` | `/api/v1/detect/{job_id}/` | Full analysis report, including Nemotron AI semantic interpretations |
