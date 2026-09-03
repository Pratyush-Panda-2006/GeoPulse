import { useState } from 'react';
import { InteractiveMapCanvas } from './InteractiveMapCanvas';
import { LayerInferenceControlPanel } from './LayerInferenceControlPanel';
import { Bell, User } from 'lucide-react';

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
      {/* 1. Global Mission Bar (Exact Match with Image Design) */}
      <header className="h-12 px-6 bg-[#0B0F17] border-b border-[#2D3748] relative flex items-center justify-between text-xs select-none z-50 shrink-0">
        {/* Brand Logo (Left) */}
        <a href="overview.html" className="flex items-center gap-2 font-mono font-bold tracking-wider text-[#00DC82] hover:text-[#00c574] transition-colors shrink-0">
          <span className="w-2 h-2 rounded-full bg-[#00DC82]" />
          <span className="text-sm font-bold tracking-wider">GEOPULSE</span>
        </a>

        {/* High-Contrast Navigation Links (Centered) */}
        <nav className="hidden md:flex items-center gap-8 text-xs font-mono tracking-wider absolute left-1/2 -translate-x-1/2">
          <a href="overview.html" className="text-slate-400 hover:text-slate-100 transition-colors py-1">OVERVIEW</a>
          <a href="studio.html" className="text-[#00DC82] font-semibold border-b-2 border-[#00DC82] pb-0.5">STUDIO</a>
          <a href="analytics.html" className="text-slate-400 hover:text-slate-100 transition-colors py-1">ANALYTICS</a>
          <a href="explorer.html" className="text-slate-400 hover:text-slate-100 transition-colors py-1">EXPLORER</a>
          <a href="intelligence.html" className="text-slate-400 hover:text-slate-100 transition-colors py-1">INTELLIGENCE</a>
          <a href="telemetry.html" className="text-slate-400 hover:text-slate-100 transition-colors py-1">TELEMETRY</a>
        </nav>

        {/* Right Side: CDSE Satellite Link Badge + Bell + Profile Icons */}
        <div className="flex items-center gap-4 shrink-0">
          <a href="telemetry.html" className="flex items-center gap-2 px-3 py-1 bg-[#00DC82]/5 border border-[#00DC82]/40 rounded text-[#00DC82] font-mono text-xs tracking-tight hover:bg-[#00DC82]/10 transition-colors" title="Copernicus Data Space Ecosystem Link Active">
            <span className="w-1.5 h-1.5 rounded-full bg-[#00DC82] animate-pulse" />
            <span>CDSE SATELLITE LINK: ACTIVE</span>
          </a>

          <button className="text-slate-400 hover:text-slate-100 p-1 transition-colors" title="System Notifications">
            <Bell className="w-4 h-4" />
          </button>

          <button className="text-slate-400 hover:text-slate-100 p-1 transition-colors" title="Operator Profile">
            <User className="w-4 h-4" />
          </button>
        </div>
      </header>

      {/* 2. Primary Full-Bleed SAR Workspace (Side-by-Side Flex Layout, Statically Framed) */}
      <main className="relative flex-1 w-full h-[calc(100vh-48px)] flex overflow-hidden">
        <div className="relative flex-1 h-full overflow-hidden">
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
        </div>

        {/* Docked Right-Hand Triage & Analytical Telemetry Inspector (Not Floating) */}
        <LayerInferenceControlPanel 
          isOpen={isInspectorOpen}
          onClose={() => setIsInspectorOpen(false)}
          activeLayer={activeLayer}
          onSelectLayer={setActiveLayer}
          metrics={{
            threshold: 0.60,
            clusters: 38,
            changePercentage: 3.202,
            changedPixels: 6152,
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
