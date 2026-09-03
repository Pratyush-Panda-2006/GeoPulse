import { useState } from 'react';
import { InteractiveMapCanvas } from './InteractiveMapCanvas';
import { LayerInferenceControlPanel } from './LayerInferenceControlPanel';
import { Satellite, AlertTriangle } from 'lucide-react';

export default function GeoPulseStudio() {
  const [activeLayer, setActiveLayer] = useState<string>('t2');
  const [opacity, setOpacity] = useState<number>(100);
  const [brightness, setBrightness] = useState<number>(100);
  const [contrast, setContrast] = useState<number>(100);
  const [colormap, setColormap] = useState<string>('turbo');
  const [isInspectorOpen, setIsInspectorOpen] = useState<boolean>(true);

  // Satellite Sentinel-1 SAR high-resolution textures
  const t1Url = "https://images.unsplash.com/photo-1509228468518-180dd4864904?auto=format&fit=crop&w=1600&q=80";
  const t2Url = "https://images.unsplash.com/photo-1451187580459-43490279c0fa?auto=format&fit=crop&w=1600&q=80";

  return (
    <div className="h-screen w-screen flex flex-col bg-[#0B0F17] text-slate-100 overflow-hidden font-sans select-none">
      {/* 1. Global Mission Bar (Height: 44px, Zero Overlap, Perfect Alignment) */}
      <header className="h-11 px-6 bg-[#0B0F17] border-b border-[#2D3748] flex items-center justify-between text-xs select-none z-50 shrink-0">
        <div className="flex items-center gap-8">
          <a href="index.html" className="flex items-center gap-2.5 font-mono font-bold tracking-wider text-slate-100 hover:text-emerald-400 transition-colors shrink-0">
            <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
            <span>GEOPULSE</span>
            <span className="text-[10px] text-emerald-400 font-normal border border-emerald-500/30 px-1.5 py-0.5 rounded">
              STUDIO 3D
            </span>
          </a>

          {/* High-Contrast Navigation Links */}
          <nav className="hidden md:flex items-center gap-6 text-xs font-mono tracking-wider text-slate-400">
            <a href="overview.html" className="hover:text-slate-100 transition-colors py-1">OVERVIEW</a>
            <a href="studio.html" className="text-emerald-400 font-bold border-b-2 border-emerald-400 py-1">STUDIO</a>
            <a href="analytics.html" className="hover:text-slate-100 transition-colors py-1">ANALYTICS</a>
            <a href="explorer.html" className="hover:text-slate-100 transition-colors py-1">EXPLORER</a>
            <a href="intelligence.html" className="hover:text-slate-100 transition-colors py-1">INTELLIGENCE</a>
            <a href="telemetry.html" className="hover:text-slate-100 transition-colors py-1">TELEMETRY</a>
          </nav>
        </div>

        {/* Consolidated Diagnostics Status Badges */}
        <div className="flex items-center gap-3 shrink-0">
          <div className="flex items-center gap-1.5 px-3 py-1 bg-amber-500/10 border border-amber-500/30 rounded-lg text-amber-300 font-mono text-[11px]" title="Lee Filter 5x5 Radiometric Enhancement Active">
            <AlertTriangle className="w-3.5 h-3.5 text-amber-400" />
            <span className="hidden sm:inline">RADIOMETRIC ENHANCEMENT: ACTIVE</span>
            <span className="sm:hidden">ENHANCED</span>
          </div>

          <a href="telemetry.html" className="flex items-center gap-1.5 px-3 py-1 bg-emerald-500/10 border border-emerald-500/20 hover:border-emerald-500/40 rounded-lg text-emerald-400 font-mono text-[11px] transition-colors" title="View Real-Time Satellite Telemetry">
            <Satellite className="w-3.5 h-3.5 text-emerald-400" />
            <span className="hidden sm:inline">CDSE LINK: ACTIVE</span>
            <span className="sm:hidden">LINK</span>
          </a>
        </div>
      </header>

      {/* 2. Primary Full-Bleed SAR Workspace (Statically Framed, 0px Height Shift) */}
      <main className="relative flex-1 w-full h-[calc(100vh-44px)] overflow-hidden">
        <InteractiveMapCanvas 
          t1ImageUrl={t1Url}
          t2ImageUrl={t2Url}
          activeLayer={activeLayer}
          onSelectLayer={setActiveLayer}
          opacity={opacity}
          brightness={brightness}
          contrast={contrast}
          onToggleInspector={() => setIsInspectorOpen(prev => !prev)}
          isInspectorOpen={isInspectorOpen}
        />

        {/* Collapsible Layer & Analytical Telemetry Inspector Dock */}
        <LayerInferenceControlPanel 
          isOpen={isInspectorOpen}
          onClose={() => setIsInspectorOpen(false)}
          activeLayer={activeLayer}
          onSelectLayer={setActiveLayer}
          metrics={{
            threshold: 0.60,
            clusters: 2,
            changePercentage: 0.196,
            changedPixels: 294,
            totalPixels: 262144
          }}
          opacity={opacity}
          setOpacity={setOpacity}
          brightness={brightness}
          setBrightness={setBrightness}
          contrast={contrast}
          setContrast={setContrast}
          colormap={colormap}
          setColormap={setColormap}
        />
      </main>
    </div>
  );
}
