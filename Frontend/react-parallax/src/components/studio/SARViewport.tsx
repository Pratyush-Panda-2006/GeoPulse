import React, { useState, useRef, useEffect, useCallback } from 'react';
import { 
  ZoomIn, 
  ZoomOut, 
  Maximize2, 
  Lock, 
  Unlock, 
  Compass, 
  SlidersHorizontal
} from 'lucide-react';

interface SARViewportProps {
  t1ImageUrl: string;
  t2ImageUrl: string;
  maskImageUrl?: string;
  heatmapImageUrl?: string;
  activeLayer: string;
  onSelectLayer: (layer: string) => void;
  opacity: number;
  brightness: number;
  contrast: number;
  t1Date?: string;
  t2Date?: string;
  onToggleInspector: () => void;
  isInspectorOpen: boolean;
}

export const SARViewport: React.FC<SARViewportProps> = ({
  t1ImageUrl,
  t2ImageUrl,
  maskImageUrl,
  heatmapImageUrl,
  activeLayer,
  onSelectLayer,
  opacity,
  brightness,
  contrast,
  t1Date = '2026-08-12',
  t2Date = '2026-09-02',
  onToggleInspector,
  isInspectorOpen
}) => {
  // Split Slider Position (0 to 100%)
  const [splitPos, setSplitPos] = useState<number>(50);
  const [isLocked, setIsLocked] = useState<boolean>(false);
  const [isDragging, setIsDragging] = useState<boolean>(false);

  // Zoom & Pan State
  const [zoom, setZoom] = useState<number>(100);
  const [pan, setPan] = useState<{ x: number; y: number }>({ x: 0, y: 0 });
  const [isPanning, setIsPanning] = useState<boolean>(false);
  const panStartRef = useRef<{ x: number; y: number; startPanX: number; startPanY: number }>({
    x: 0,
    y: 0,
    startPanX: 0,
    startPanY: 0
  });

  // Coordinate Telemetry
  const [telemetry, setTelemetry] = useState<{ lat: string; lng: string; db: string }>({
    lat: '18°56\'43" N',
    lng: '72°57\'58" E',
    db: '-14.2 dB'
  });

  const containerRef = useRef<HTMLDivElement>(null);
  const sliderRef = useRef<HTMLDivElement>(null);

  // Dynamic ground scale bar calculation based on zoom level
  const getGroundScale = (currentZoom: number) => {
    if (currentZoom >= 250) return { distance: '50 m', widthPx: 64 };
    if (currentZoom >= 150) return { distance: '250 m', widthPx: 90 };
    if (currentZoom >= 80) return { distance: '1 km', widthPx: 120 };
    return { distance: '5 km', widthPx: 140 };
  };

  const scaleMetric = getGroundScale(zoom);

  // --- Split Slider Drag Mechanics ---
  const handlePointerDown = (e: React.PointerEvent) => {
    if (isLocked) return;
    setIsDragging(true);
    e.currentTarget.setPointerCapture(e.pointerId);
    e.stopPropagation();
  };

  const handlePointerMove = (e: React.PointerEvent) => {
    if (!isDragging || isLocked || !containerRef.current) return;
    const rect = containerRef.current.getBoundingClientRect();
    const xPos = Math.max(0, Math.min(e.clientX - rect.left, rect.width));
    const pct = Math.round((xPos / rect.width) * 1000) / 10;
    setSplitPos(pct);
  };

  const handlePointerUp = (e: React.PointerEvent) => {
    if (isDragging) {
      setIsDragging(false);
      try { e.currentTarget.releasePointerCapture(e.pointerId); } catch {}
    }
  };

  // Keyboard navigation for split slider
  const handleSliderKeyDown = (e: React.KeyboardEvent) => {
    if (isLocked) return;
    if (e.key === 'ArrowLeft') {
      setSplitPos(prev => Math.max(0, prev - 2));
      e.preventDefault();
    } else if (e.key === 'ArrowRight') {
      setSplitPos(prev => Math.min(100, prev + 2));
      e.preventDefault();
    } else if (e.key === 'Home') {
      setSplitPos(0);
      e.preventDefault();
    } else if (e.key === 'End') {
      setSplitPos(100);
      e.preventDefault();
    }
  };

  // --- Canvas Pan Mechanics ---
  const handleCanvasMouseDown = (e: React.MouseEvent) => {
    if ((e.target as HTMLElement).closest('[data-no-pan]')) return;
    if (e.button !== 0) return; // Primary left-click only
    setIsPanning(true);
    panStartRef.current = {
      x: e.clientX,
      y: e.clientY,
      startPanX: pan.x,
      startPanY: pan.y
    };
  };

  const handleCanvasMouseMove = (e: React.MouseEvent) => {
    if (containerRef.current) {
      const rect = containerRef.current.getBoundingClientRect();
      const nx = (e.clientX - rect.left) / rect.width;
      const ny = (e.clientY - rect.top) / rect.height;
      const latBase = 18.9440 + (1 - ny) * 0.04;
      const lngBase = 72.8359 + nx * 0.04;
      const simDb = (-10 - Math.sin(nx * 6) * 6).toFixed(1);

      setTelemetry({
        lat: `${latBase.toFixed(4)}° N`,
        lng: `${lngBase.toFixed(4)}° E`,
        db: `${simDb} dB`
      });
    }

    if (!isPanning) return;
    const dx = e.clientX - panStartRef.current.x;
    const dy = e.clientY - panStartRef.current.y;
    setPan({
      x: panStartRef.current.startPanX + dx,
      y: panStartRef.current.startPanY + dy
    });
  };

  const handleCanvasMouseUp = () => {
    if (isPanning) setIsPanning(false);
  };

  // Wheel zoom centered on canvas
  const handleWheel = useCallback((e: WheelEvent) => {
    e.preventDefault();
    const factor = e.deltaY < 0 ? 1.15 : 0.85;
    setZoom(prev => Math.min(Math.max(50, Math.round(prev * factor)), 500));
  }, []);

  useEffect(() => {
    const el = containerRef.current;
    if (!el) return;
    el.addEventListener('wheel', handleWheel, { passive: false });
    return () => el.removeEventListener('wheel', handleWheel);
  }, [handleWheel]);

  const zoomStep = (multiplier: number) => {
    setZoom(prev => Math.min(Math.max(50, Math.round(prev * multiplier)), 500));
  };

  const resetExtent = () => {
    setZoom(100);
    setPan({ x: 0, y: 0 });
    setSplitPos(50);
  };

  // Build GPU-accelerated raster filter string
  const rasterFilter = `brightness(${brightness}%) contrast(${contrast}%)`;

  return (
    <div 
      ref={containerRef}
      onMouseDown={handleCanvasMouseDown}
      onMouseMove={handleCanvasMouseMove}
      onMouseUp={handleCanvasMouseUp}
      onMouseLeave={handleCanvasMouseUp}
      className={`relative w-full h-full bg-[#0B0F17] overflow-hidden select-none outline-none ${
        isPanning ? 'cursor-grabbing' : 'cursor-crosshair'
      }`}
      role="region"
      aria-label="High-Resolution SAR Canvas Split Viewport"
    >
      {/* 1. Synchronized Hardware-Accelerated Raster Imagery Layer */}
      <div 
        className="absolute inset-0 will-change-[transform,filter] transition-transform duration-75 origin-center"
        style={{
          transform: `translate3d(${pan.x}px, ${pan.y}px, 0px) scale(${zoom / 100})`
        }}
      >
        {/* T1 Baseline Pass (Left Pane) */}
        <div 
          className="absolute inset-0 bg-cover bg-center"
          style={{
            backgroundImage: `url(${t1ImageUrl})`,
            filter: rasterFilter
          }}
        />

        {/* T2 Survey Target (Right Pane clipped to Split Curtain Position) */}
        <div 
          className="absolute inset-0 bg-cover bg-center"
          style={{
            backgroundImage: `url(${t2ImageUrl})`,
            clipPath: `polygon(${splitPos}% 0%, 100% 0%, 100% 100%, ${splitPos}% 100%)`,
            opacity: opacity / 100,
            filter: rasterFilter
          }}
        >
          {/* Neural Mask / Heatmap Overlay if selected */}
          {activeLayer === 'heatmap' && heatmapImageUrl && (
            <div 
              className="absolute inset-0 bg-cover bg-center mix-blend-screen opacity-70 pointer-events-none"
              style={{ backgroundImage: `url(${heatmapImageUrl})` }}
            />
          )}
          {activeLayer === 'mask' && maskImageUrl && (
            <div 
              className="absolute inset-0 bg-cover bg-center mix-blend-screen pointer-events-none"
              style={{ backgroundImage: `url(${maskImageUrl})`, imageRendering: 'pixelated' }}
            />
          )}
        </div>
      </div>

      {/* 2. Interactive Before-After Split Curtain Slider */}
      <div 
        ref={sliderRef}
        data-no-pan
        tabIndex={0}
        role="separator"
        aria-orientation="vertical"
        aria-valuenow={splitPos}
        aria-label="Split-view divider curtain. Use left and right arrow keys to adjust."
        onKeyDown={handleSliderKeyDown}
        onPointerDown={handlePointerDown}
        onPointerMove={handlePointerMove}
        onPointerUp={handlePointerUp}
        style={{ left: `${splitPos}%` }}
        className={`absolute top-0 bottom-0 w-0.5 bg-emerald-400 z-20 cursor-ew-resize touch-none select-none focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-emerald-400 ${
          isDragging ? 'bg-emerald-300 shadow-[0_0_12px_rgba(16,185,129,0.8)]' : 'hover:bg-emerald-300'
        }`}
      >
        {/* Ergonomic Handle Grip */}
        <div 
          className="absolute top-1/2 -translate-y-1/2 -translate-x-1/2 w-6 h-11 bg-slate-900/95 border border-slate-700 hover:border-emerald-400 rounded-md flex items-center justify-center gap-1 shadow-2xl transition-colors duration-150"
          title="Drag to compare epochs (Left: T1, Right: T2)"
        >
          <span className="w-0.5 h-3.5 bg-slate-400 rounded-full" />
          <span className="w-0.5 h-3.5 bg-slate-400 rounded-full" />
        </div>

        {/* Date-Stamped Split Badges */}
        <div className="absolute top-3.5 -translate-x-1/2 flex items-center gap-2 pointer-events-none select-none whitespace-nowrap">
          <span className="bg-[#1A2234]/90 backdrop-blur-md border border-[#2D3748] px-2.5 py-1 rounded text-[11px] font-mono text-slate-300 shadow-xl">
            <strong className="text-slate-100 font-semibold">T1:</strong> {t1Date}
          </span>
          <span className="bg-[#1A2234]/90 backdrop-blur-md border border-emerald-500/40 px-2.5 py-1 rounded text-[11px] font-mono text-emerald-300 shadow-xl">
            <strong className="text-emerald-400 font-semibold">T2:</strong> {t2Date}
          </span>
        </div>
      </div>

      {/* 3. Top-Left Cartographic Instrument: North Compass & GSD Badge */}
      <div 
        data-no-pan
        className="absolute top-3.5 left-3.5 z-30 flex items-center gap-2.5 bg-[#1A2234]/90 backdrop-blur-md border border-[#2D3748] px-3 py-1.5 rounded-lg shadow-xl select-none"
      >
        <div className="flex items-center gap-1.5 text-emerald-400">
          <Compass className="w-4 h-4" />
          <span className="font-mono text-xs font-bold tracking-wider text-slate-100">NORTH 000°</span>
        </div>
        <div className="w-px h-3.5 bg-[#2D3748]" />
        <span className="text-[10px] font-mono text-slate-400">GSD: 10m/px</span>
      </div>

      {/* 4. Top-Center Unified Contextual Floating Pill Dock */}
      <nav 
        data-no-pan
        aria-label="Mission Viewport Quick Controls"
        className="absolute top-3.5 left-1/2 -translate-x-1/2 z-30 flex items-center gap-1.5 bg-[#1A2234]/95 backdrop-blur-md border border-[#2D3748] p-1.5 rounded-xl shadow-2xl select-none"
      >
        {/* Layer Quick Switchers */}
        <div className="flex items-center gap-1 pr-1.5 border-r border-[#2D3748]">
          <button
            onClick={() => onSelectLayer('t1')}
            className={`px-2.5 py-1 text-xs font-mono rounded-lg transition-colors ${
              activeLayer === 't1' 
                ? 'bg-emerald-500/20 text-emerald-300 border border-emerald-500/40 font-semibold' 
                : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800'
            }`}
            title="Switch to Baseline SAR (T1)"
            aria-label="Baseline Pass"
          >
            T1
          </button>
          <button
            onClick={() => onSelectLayer('t2')}
            className={`px-2.5 py-1 text-xs font-mono rounded-lg transition-colors ${
              activeLayer === 't2' 
                ? 'bg-emerald-500/20 text-emerald-300 border border-emerald-500/40 font-semibold' 
                : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800'
            }`}
            title="Switch to Target SAR (T2)"
            aria-label="Target Pass"
          >
            T2
          </button>
          <button
            onClick={() => onSelectLayer('mask')}
            className={`px-2.5 py-1 text-xs font-mono rounded-lg transition-colors ${
              activeLayer === 'mask' 
                ? 'bg-red-500/20 text-red-300 border border-red-500/40 font-semibold' 
                : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800'
            }`}
            title="Binary Change Mask"
            aria-label="Change Mask"
          >
            MASK
          </button>
          <button
            onClick={() => onSelectLayer('heatmap')}
            className={`px-2.5 py-1 text-xs font-mono rounded-lg transition-colors ${
              activeLayer === 'heatmap' 
                ? 'bg-amber-500/20 text-amber-300 border border-amber-500/40 font-semibold' 
                : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800'
            }`}
            title="Confidence Heatmap"
            aria-label="Confidence Heatmap"
          >
            HEATMAP
          </button>
        </div>

        {/* Split Lock & Reset */}
        <button
          onClick={() => setIsLocked(!isLocked)}
          className={`px-2.5 py-1 rounded-lg text-xs font-mono flex items-center gap-1.5 transition-colors ${
            isLocked 
              ? 'bg-amber-500/20 text-amber-300 border border-amber-500/40 font-bold' 
              : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800'
          }`}
          title={isLocked ? "Unlock split slider" : "Lock split slider position"}
          aria-pressed={isLocked}
        >
          {isLocked ? <Lock className="w-3.5 h-3.5" /> : <Unlock className="w-3.5 h-3.5" />}
          <span>{isLocked ? 'LOCKED' : 'SLIDER'}</span>
        </button>

        <button
          onClick={() => setSplitPos(50)}
          className="px-2 py-1 rounded-lg text-xs font-mono text-slate-400 hover:text-slate-200 hover:bg-slate-800 transition-colors"
          title="Reset split divider to center (50%)"
        >
          1:1
        </button>

        {/* Inspector Dock Toggle */}
        <button
          onClick={onToggleInspector}
          className={`ml-1 px-3 py-1 rounded-lg text-xs font-mono flex items-center gap-1.5 transition-all ${
            isInspectorOpen
              ? 'bg-emerald-500/20 text-emerald-300 border border-emerald-500/40 font-bold'
              : 'bg-emerald-500/10 hover:bg-emerald-500/20 text-emerald-400 border border-emerald-500/30'
          }`}
          title="Toggle Triage & Inference Inspector"
          aria-expanded={isInspectorOpen}
        >
          <SlidersHorizontal className="w-3.5 h-3.5" />
          <span className="hidden sm:inline">INSPECTOR</span>
        </button>
      </nav>

      {/* 5. Bottom-Left Dynamic Cartographic Scale Bar & Coordinates */}
      <div 
        data-no-pan
        className="absolute bottom-3.5 left-3.5 z-30 flex flex-col gap-1.5 bg-[#1A2234]/90 backdrop-blur-md border border-[#2D3748] p-3 rounded-xl shadow-2xl font-mono select-none"
      >
        <div className="flex items-center gap-2.5 text-xs text-slate-200">
          <span className="font-semibold text-emerald-400">{telemetry.lat}</span>
          <span className="text-slate-600">|</span>
          <span className="font-semibold text-emerald-400">{telemetry.lng}</span>
          <span className="text-slate-600">|</span>
          <span className="text-slate-400">{telemetry.db}</span>
        </div>

        {/* Scale Bar Ruler Line */}
        <div className="flex items-center gap-2.5 pt-1.5 border-t border-[#2D3748]">
          <div 
            style={{ width: `${scaleMetric.widthPx}px` }}
            className="h-1.5 border-b-2 border-l-2 border-r-2 border-slate-300 relative transition-all duration-150"
          >
            <span className="absolute -top-4 left-1/2 -translate-x-1/2 text-[10px] text-slate-300 font-medium tracking-tight">
              {scaleMetric.distance}
            </span>
          </div>
          <span className="text-[10px] text-slate-500">WGS84 UTM 43N</span>
        </div>
      </div>

      {/* 6. Bottom-Right Floating Zoom Controls */}
      <div 
        data-no-pan
        className="absolute bottom-3.5 right-3.5 z-30 flex items-center gap-1 bg-[#1A2234]/90 backdrop-blur-md border border-[#2D3748] p-1.5 rounded-xl shadow-2xl select-none"
      >
        <button
          onClick={() => zoomStep(1.25)}
          className="p-1.5 rounded-lg text-slate-400 hover:text-slate-100 hover:bg-slate-800 transition-colors focus-visible:ring-2 focus-visible:ring-emerald-400"
          title="Zoom in (+)"
          aria-label="Zoom In"
        >
          <ZoomIn className="w-4 h-4" />
        </button>
        <span className="px-1.5 font-mono text-xs font-semibold text-slate-200 min-w-[44px] text-center">
          {zoom}%
        </span>
        <button
          onClick={() => zoomStep(0.8)}
          className="p-1.5 rounded-lg text-slate-400 hover:text-slate-100 hover:bg-slate-800 transition-colors focus-visible:ring-2 focus-visible:ring-emerald-400"
          title="Zoom out (-)"
          aria-label="Zoom Out"
        >
          <ZoomOut className="w-4 h-4" />
        </button>
        <div className="w-px h-4 bg-[#2D3748] mx-0.5" />
        <button
          onClick={resetExtent}
          className="p-1.5 rounded-lg text-slate-400 hover:text-slate-100 hover:bg-slate-800 transition-colors focus-visible:ring-2 focus-visible:ring-emerald-400"
          title="Reset Extent & Center (1:1)"
          aria-label="Reset Extent"
        >
          <Maximize2 className="w-4 h-4" />
        </button>
      </div>
    </div>
  );
};
