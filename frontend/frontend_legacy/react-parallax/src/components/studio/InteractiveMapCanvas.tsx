import React, { useState, useRef } from 'react';
import { 
  Lock, 
  Unlock, 
  SlidersHorizontal,
  Crop
} from 'lucide-react';
import { TacticalCompassHUD } from './TacticalCompassHUD';

interface InteractiveMapCanvasProps {
  t1ImageUrl: string;
  t2ImageUrl: string;
  maskImageUrl?: string;
  heatmapImageUrl?: string;
  overlayImageUrl?: string;
  boxesImageUrl?: string;
  activeLayer: string;
  onSelectLayer: (layer: string) => void;
  opacity: number;
  brightness: number;
  contrast: number;
  blendMode?: 'normal' | 'difference' | 'screen';
  t1Date?: string;
  t2Date?: string;
  onToggleInspector: () => void;
  isInspectorOpen: boolean;
}

export const InteractiveMapCanvas: React.FC<InteractiveMapCanvasProps> = ({
  t1ImageUrl,
  t2ImageUrl,
  maskImageUrl,
  heatmapImageUrl,
  overlayImageUrl,
  boxesImageUrl,
  activeLayer,
  onSelectLayer,
  opacity,
  brightness,
  contrast,
  blendMode = 'normal',
  t1Date = '2026-08-12',
  t2Date = '2026-09-02',
  onToggleInspector,
  isInspectorOpen
}) => {
  // --- Viewport State (Statically Framed Canvas) ---
  const [rotation, setRotation] = useState<number>(0);
  const [splitPos, setSplitPos] = useState<number>(50); // Split curtain % across X
  const [isLocked, setIsLocked] = useState<boolean>(false);
  const [isDraggingSplit, setIsDraggingSplit] = useState<boolean>(false);

  // --- Coordinates Telemetry (Hover Tracking) ---
  const [telemetry, setTelemetry] = useState<{ lat: string; lng: string; db: string }>({
    lat: '18°56\'43" N',
    lng: '72°57\'58" E',
    db: '-14.2 dB'
  });

  const containerRef = useRef<HTMLDivElement>(null);
  const splitSliderRef = useRef<HTMLDivElement>(null);

  // --- Split Slider Drag Mechanics ---
  const handleSplitPointerDown = (e: React.PointerEvent) => {
    if (isLocked) return;
    setIsDraggingSplit(true);
    e.currentTarget.setPointerCapture(e.pointerId);
    e.stopPropagation();
  };

  const handleSplitPointerMove = (e: React.PointerEvent) => {
    if (!isDraggingSplit || isLocked || !containerRef.current) return;
    const rect = containerRef.current.getBoundingClientRect();
    const x = Math.max(0, Math.min(e.clientX - rect.left, rect.width));
    setSplitPos(Math.round((x / rect.width) * 1000) / 10);
  };

  const handleSplitPointerUp = (e: React.PointerEvent) => {
    if (isDraggingSplit) {
      setIsDraggingSplit(false);
      try { e.currentTarget.releasePointerCapture(e.pointerId); } catch {}
    }
  };

  // Track coordinates across statically framed container without pan displacement
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
  };

  // Resolve Survey Target Imagery based on Active Raster Layer
  const resolveTargetImage = () => {
    if (activeLayer === 't1') return t1ImageUrl;
    if (activeLayer === 'boxes') return boxesImageUrl || overlayImageUrl || t2ImageUrl;
    if (activeLayer === 'overlay') return overlayImageUrl || t2ImageUrl;
    if (activeLayer === 'mask') return maskImageUrl || t2ImageUrl;
    if (activeLayer === 'heatmap') return heatmapImageUrl || t2ImageUrl;
    return t2ImageUrl;
  };

  // Combined CSS filters for raster layers
  const rasterFilter = `brightness(${brightness}%) contrast(${contrast}%)`;

  return (
    <div
      ref={containerRef}
      tabIndex={0}
      role="region"
      aria-label="Clean SAR Viewport Canvas"
      onMouseMove={handleCanvasMouseMove}
      className="relative w-full h-full bg-[#0B0F17] overflow-hidden select-none outline-none cursor-default"
    >
      {/* 1. Statically Framed Coordinate Plane (Zero Drift) */}
      <div
        style={{
          transform: rotation ? `rotate(${rotation}deg)` : 'none',
          willChange: 'transform'
        }}
        className="absolute inset-0 origin-center pointer-events-none"
      >
        {/* T1 Baseline Raster (Full-bleed left background) */}
        <div
          className="absolute inset-0 bg-cover bg-center transition-all"
          style={{
            backgroundImage: `url(${t1ImageUrl})`,
            filter: rasterFilter
          }}
        />

        {/* Survey Target Raster (Clipped to Curtain Split Position) */}
        <div
          className="absolute inset-0 bg-cover bg-center transition-all"
          style={{
            backgroundImage: `url(${resolveTargetImage()})`,
            clipPath: `polygon(${splitPos}% 0%, 100% 0%, 100% 100%, ${splitPos}% 100%)`,
            opacity: opacity / 100,
            filter: rasterFilter,
            mixBlendMode: blendMode,
            imageRendering: activeLayer === 'mask' ? 'pixelated' : 'auto'
          }}
        >
          {activeLayer === 'heatmap' && heatmapImageUrl && (
            <div
              className="absolute inset-0 bg-cover bg-center mix-blend-screen opacity-70 pointer-events-none"
              style={{ backgroundImage: `url(${heatmapImageUrl})` }}
            />
          )}
        </div>
      </div>

      {/* 2. Interactive Before-After Split Curtain Slider */}
      <div
        ref={splitSliderRef}
        data-no-pan
        tabIndex={0}
        role="separator"
        aria-orientation="vertical"
        aria-valuenow={splitPos}
        aria-label="Before/After Split Divider Curtain. Drag horizontally to compare passes."
        onPointerDown={handleSplitPointerDown}
        onPointerMove={handleSplitPointerMove}
        onPointerUp={handleSplitPointerUp}
        style={{ left: `${splitPos}%` }}
        className={`absolute top-0 bottom-0 w-0.5 bg-emerald-400 z-20 cursor-ew-resize touch-none select-none focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-emerald-400 ${
          isDraggingSplit ? 'bg-emerald-300 shadow-[0_0_12px_rgba(16,185,129,0.8)]' : 'hover:bg-emerald-300'
        }`}
      >
        {/* Laser Grip Handle */}
        <div 
          className="absolute top-1/2 -translate-y-1/2 -translate-x-1/2 w-6 h-11 bg-slate-900/95 border border-slate-700 hover:border-emerald-400 rounded-md flex items-center justify-center gap-1 shadow-2xl transition-colors duration-150"
          title="Drag to compare epochs (Left: T1, Right: T2)"
        >
          <span className="w-0.5 h-3.5 bg-slate-400 rounded-full" />
          <span className="w-0.5 h-3.5 bg-slate-400 rounded-full" />
        </div>

        {/* Floating Epoch Badges */}
        <div className="absolute top-3.5 -translate-x-1/2 flex items-center gap-2 pointer-events-none select-none whitespace-nowrap">
          <span className="bg-[#1A2234]/90 backdrop-blur-md border border-[#2D3748] px-2.5 py-1 rounded text-[11px] font-mono tracking-tight text-slate-300 shadow-xl">
            <strong className="text-slate-100 font-semibold">T1:</strong> {t1Date}
          </span>
          <span className="bg-[#1A2234]/90 backdrop-blur-md border border-emerald-500/40 px-2.5 py-1 rounded text-[11px] font-mono tracking-tight text-emerald-300 shadow-xl">
            <strong className="text-emerald-400 font-semibold">T2:</strong> {t2Date}
          </span>
        </div>
      </div>

      {/* 3. Interactive Draggable Tactical Compass HUD (Rotatable Matrix) */}
      <div data-no-pan>
        <TacticalCompassHUD
          rotation={rotation}
          onRotationChange={setRotation}
          onResetRotation={() => setRotation(0)}
        />
      </div>

      {/* 4. Top-Center Unified Contextual Floating Tool Strip */}
      <nav
        data-no-pan
        aria-label="Mission Viewport Quick Controls"
        className="absolute top-3.5 left-1/2 -translate-x-1/2 z-30 flex items-center gap-1.5 bg-[#1A2234]/95 backdrop-blur-md border border-[#2D3748] p-1.5 rounded-xl shadow-2xl select-none"
      >
        <div className="flex items-center gap-1 pr-1.5 border-r border-[#2D3748]">
          {(['t1', 't2', 'mask', 'heatmap', 'falsecolor', 'overlay'] as const).map(layerId => (
            <button
              key={layerId}
              onClick={() => onSelectLayer(layerId)}
              className={`px-2.5 py-1 text-xs font-mono rounded-lg transition-colors ${
                activeLayer === layerId
                  ? 'bg-emerald-500/20 text-emerald-300 border border-emerald-500/40 font-semibold'
                  : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800'
              }`}
            >
              {layerId.toUpperCase()}
            </button>
          ))}

          {/* Highlight Changes (Original Raster Detections) */}
          <button
            onClick={() => onSelectLayer('boxes')}
            className={`px-2 py-0.5 text-xs font-mono rounded flex items-center gap-1 transition-colors ${
              activeLayer === 'boxes'
                ? 'text-amber-300 bg-amber-500/20 border border-amber-400 font-bold'
                : 'text-amber-400 hover:bg-amber-500/10 border border-amber-500/30'
            }`}
            title="Highlight major changed areas with labeled boxes"
          >
            <Crop className="w-3.5 h-3.5" />
            <span>HIGHLIGHT</span>
          </button>
        </div>

        {/* Split Lock Button */}
        <button
          onClick={() => setIsLocked(!isLocked)}
          className={`px-2.5 py-1 rounded-lg text-xs font-mono flex items-center gap-1.5 transition-colors ${
            isLocked
              ? 'bg-amber-500/20 text-amber-300 border border-amber-500/40 font-bold'
              : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800'
          }`}
          aria-pressed={isLocked}
          title={isLocked ? "Unlock split slider" : "Lock split slider position"}
        >
          {isLocked ? <Lock className="w-3.5 h-3.5" /> : <Unlock className="w-3.5 h-3.5" />}
          <span>{isLocked ? 'LOCKED' : 'SLIDER'}</span>
        </button>

        {/* 1:1 Reset Button */}
        <button
          onClick={() => setSplitPos(50)}
          className="px-2 py-1 rounded-lg text-xs font-mono text-slate-400 hover:text-slate-200 hover:bg-slate-800 transition-colors"
          title="Reset split divider to center (50%)"
        >
          1:1
        </button>

        {/* Inspector Toggle */}
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

      {/* 5. Bottom-Left Cartographic Scale Bar & Coordinates */}
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
            style={{ width: '120px' }}
            className="h-1.5 border-b-2 border-l-2 border-r-2 border-slate-300 relative transition-all duration-150"
          >
            <span className="absolute -top-4 left-1/2 -translate-x-1/2 text-[10px] text-slate-300 font-medium tracking-tight">
              1 km
            </span>
          </div>
          <span className="text-[10px] text-slate-500">WGS84 UTM 43N</span>
        </div>
      </div>
    </div>
  );
};
