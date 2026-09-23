# GeoPulse Frontend

This is the React + TypeScript + Vite frontend for the GeoPulse visualization application.

## Prerequisites
- Node.js (v18+)

## Installation
Run the following from the `frontend` directory:
```bash
npm install
```

## Start Development Server
```bash
npm run dev
```

## Cesium Configuration
- Cesium is configured using the `vite-plugin-cesium` in `vite.config.ts`.
- The reusable viewer component is located at `src/components/CesiumViewer.tsx`.
- CSS for Cesium widgets is imported inside the viewer component.

## Phase 1 Implementation
- Scaffolded standard React + TypeScript + Vite app.
- Configured CesiumJS with Vite.
- Implemented `CesiumViewer` component that cleanly mounts and unmounts to prevent duplicate contexts.
- Configured camera to start focused on GeoPulse AOI (72.8, 18.9 to 72.9, 19.0).
- Created the main status overlay UI.

## Remaining for Phase 2
- Integrate georeferenced Sentinel-1 SAR TIFF overlays.
- Incorporate a 3D DEM (Digital Elevation Model) terrain layer.
- Render Model 3 change regions as 3D visualization objects.
- Add a timeline UI for before/after comparison.
