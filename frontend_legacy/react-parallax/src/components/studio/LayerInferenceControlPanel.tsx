import React from 'react';
import { 
  Sliders, 
  X, 
  RotateCcw, 
  ArrowUpRight 
} from 'lucide-react';
import { TacticalLayerDock } from './TacticalLayerDock';

interface LayerInferenceControlPanelProps {
  isOpen: boolean;
  onClose: () => void;
  activeLayer: string;
  onSelectLayer: (layerId: string) => void;
  metrics: {
    threshold: number;
    clusters: number;
    changePercentage: number;
    changedPixels: number;
    totalPixels: number;
  };
  opacity: number;
  setOpacity: (val: number) => void;
  brightness: number;
  setBrightness: (val: number) => void;
  contrast: number;
  setContrast: (val: number) => void;
  colormap: string;
  setColormap: (mapId: string) => void;
}

const COLORMAPS = [
  { id: 'turbo', name: 'Turbo (Scientific)', gradient: 'from-blue-600 via-emerald-400 to-red-500' },
  { id: 'viridis', name: 'Viridis (Perceptual)', gradient: 'from-[#440154] via-[#21918c] to-[#fde725]' },
  { id: 'binary', name: 'High-Alert Binary', gradient: 'from-slate-900 to-red-500' },
  { id: 'plasma', name: 'Plasma Radiometric', gradient: 'from-[#0d0887] via-[#cc4778] to-[#f0f921]' },
];

export const LayerInferenceControlPanel: React.FC<LayerInferenceControlPanelProps> = ({
  isOpen,
  onClose,
  activeLayer,
  onSelectLayer,
  metrics,
  opacity,
  setOpacity,
  brightness,
  setBrightness,
  contrast,
  setContrast,
  colormap,
  setColormap
}) => {
  if (!isOpen) return null;

  return (
    <aside 
      className="w-[360px] h-full bg-[#0D121D] border-l border-[#2D3748] flex flex-col shrink-0 z-30 select-none overflow-hidden text-slate-200 font-sans transition-all duration-200"
      aria-label="Layer & Analytical Telemetry Control Panel"
    >
      {/* Header */}
      <div className="px-4 py-3 border-b border-[#2D3748] flex items-center justify-between bg-[#0B0F17]/80 shrink-0">
        <div className="flex items-center gap-2">
          <Sliders className="w-4 h-4 text-emerald-400" />
          <h2 className="font-bold text-xs uppercase tracking-wider text-slate-100">
            Triage & Analysis Inspector
          </h2>
        </div>
        <button 
          onClick={onClose}
          className="p-1 rounded-lg text-slate-400 hover:text-slate-100 hover:bg-slate-800 transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-emerald-400"
          aria-label="Close Inspector"
        >
          <X className="w-4 h-4" />
        </button>
      </div>

      {/* Scrollable Inspector Content */}
      <div className="flex-1 overflow-y-auto px-4 py-4 flex flex-col gap-4">
        {/* Section 1: KPI Metrics Readout Grid */}
        <section className="flex flex-col gap-2.5" aria-labelledby="metrics-heading">
          <div className="flex items-center justify-between">
            <span id="metrics-heading" className="text-[11px] font-mono uppercase tracking-wider text-slate-400 font-semibold">
              Inference Intelligence
            </span>
            <span className="inline-flex items-center px-2 py-0.5 rounded text-[10px] font-mono bg-emerald-500/10 text-emerald-400 border border-emerald-500/30 font-semibold">
              NOMINAL
            </span>
          </div>

          <div className="grid grid-cols-2 gap-2">
            <div className="p-3 bg-[#0B0F17]/80 border border-[#2D3748] rounded-lg flex flex-col">
              <span className="text-[10px] font-mono text-slate-400 uppercase">Threshold</span>
              <span className="text-base font-mono font-bold tracking-tight text-slate-100 mt-0.5 tabular-nums">
                {metrics.threshold.toFixed(2)}
              </span>
            </div>

            <div className="p-3 bg-[#0B0F17]/80 border border-[#2D3748] rounded-lg flex flex-col">
              <span className="text-[10px] font-mono text-slate-400 uppercase">Change Clusters</span>
              <span className="text-base font-mono font-bold tracking-tight text-amber-400 mt-0.5 tabular-nums">
                {metrics.clusters}
              </span>
            </div>

            <div className="p-3 bg-[#0B0F17]/80 border border-[#2D3748] rounded-lg flex flex-col">
              <span className="text-[10px] font-mono text-slate-400 uppercase">Total Delta Area</span>
              <span className="text-base font-mono font-bold tracking-tight text-emerald-400 mt-0.5 tabular-nums">
                {metrics.changePercentage.toFixed(3)}%
              </span>
            </div>

            <div className="p-3 bg-[#0B0F17]/80 border border-[#2D3748] rounded-lg flex flex-col">
              <span className="text-[10px] font-mono text-slate-400 uppercase">Changed Pixels</span>
              <span className="text-base font-mono font-bold tracking-tight text-slate-100 mt-0.5 tabular-nums">
                {metrics.changedPixels.toLocaleString()}
              </span>
            </div>
          </div>
        </section>

        {/* Section 2: Active Raster Layer Stack */}
        <TacticalLayerDock
          activeLayer={activeLayer}
          onSelectLayer={onSelectLayer}
        />

        {/* Section 3: Dual-Input Radiometric Sliders */}
        <section className="flex flex-col gap-3.5 pt-2 border-t border-[#2D3748]" aria-labelledby="radiometric-heading">
          <span id="radiometric-heading" className="text-[11px] font-mono uppercase tracking-wider text-slate-400 font-semibold">
            Radiometric Adjustments
          </span>

          {/* Opacity Control */}
          <div className="flex flex-col gap-1.5">
            <div className="flex justify-between items-center text-xs">
              <label htmlFor="opacity-range" className="text-slate-300">Layer Opacity</label>
              <div className="flex items-center gap-1.5">
                <input 
                  id="opacity-numeric"
                  type="number" 
                  min="0" 
                  max="100" 
                  value={opacity}
                  onChange={(e) => setOpacity(Math.max(0, Math.min(100, Number(e.target.value))))}
                  className="w-12 px-1.5 py-0.5 bg-[#0B0F17] border border-[#2D3748] rounded font-mono text-right text-xs text-slate-100 focus:border-emerald-400 focus:outline-none"
                  aria-label="Numeric opacity percentage"
                />
                <span className="text-[10px] text-slate-400 font-mono">%</span>
                <button 
                  onClick={() => setOpacity(100)} 
                  className="p-1 text-slate-500 hover:text-slate-300 transition-colors"
                  title="Reset opacity to 100%"
                >
                  <RotateCcw className="w-3 h-3" />
                </button>
              </div>
            </div>
            <input 
              id="opacity-range"
              type="range" 
              min="0" 
              max="100" 
              value={opacity}
              onChange={(e) => setOpacity(Number(e.target.value))}
              className="accent-emerald-400 h-1.5 bg-[#0B0F17] rounded-lg cursor-pointer focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-emerald-400"
            />
          </div>

          {/* Brightness Control */}
          <div className="flex flex-col gap-1.5">
            <div className="flex justify-between items-center text-xs">
              <label htmlFor="brightness-range" className="text-slate-300">Brightness Gain</label>
              <div className="flex items-center gap-1.5">
                <input 
                  id="brightness-numeric"
                  type="number" 
                  min="50" 
                  max="150" 
                  value={brightness}
                  onChange={(e) => setBrightness(Math.max(50, Math.min(150, Number(e.target.value))))}
                  className="w-12 px-1.5 py-0.5 bg-[#0B0F17] border border-[#2D3748] rounded font-mono text-right text-xs text-slate-100 focus:border-emerald-400 focus:outline-none"
                  aria-label="Numeric brightness percentage"
                />
                <span className="text-[10px] text-slate-400 font-mono">%</span>
                <button 
                  onClick={() => setBrightness(100)} 
                  className="p-1 text-slate-500 hover:text-slate-300 transition-colors"
                  title="Reset brightness to 100%"
                >
                  <RotateCcw className="w-3 h-3" />
                </button>
              </div>
            </div>
            <input 
              id="brightness-range"
              type="range" 
              min="50" 
              max="150" 
              value={brightness}
              onChange={(e) => setBrightness(Number(e.target.value))}
              className="accent-emerald-400 h-1.5 bg-[#0B0F17] rounded-lg cursor-pointer focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-emerald-400"
            />
          </div>

          {/* Contrast Control */}
          <div className="flex flex-col gap-1.5">
            <div className="flex justify-between items-center text-xs">
              <label htmlFor="contrast-range" className="text-slate-300">Contrast Multiplier</label>
              <div className="flex items-center gap-1.5">
                <input 
                  id="contrast-numeric"
                  type="number" 
                  min="50" 
                  max="200" 
                  value={contrast}
                  onChange={(e) => setContrast(Math.max(50, Math.min(200, Number(e.target.value))))}
                  className="w-12 px-1.5 py-0.5 bg-[#0B0F17] border border-[#2D3748] rounded font-mono text-right text-xs text-slate-100 focus:border-emerald-400 focus:outline-none"
                  aria-label="Numeric contrast percentage"
                />
                <span className="text-[10px] text-slate-400 font-mono">%</span>
                <button 
                  onClick={() => setContrast(100)} 
                  className="p-1 text-slate-500 hover:text-slate-300 transition-colors"
                  title="Reset contrast to 100%"
                >
                  <RotateCcw className="w-3 h-3" />
                </button>
              </div>
            </div>
            <input 
              id="contrast-range"
              type="range" 
              min="50" 
              max="200" 
              value={contrast}
              onChange={(e) => setContrast(Number(e.target.value))}
              className="accent-emerald-400 h-1.5 bg-[#0B0F17] rounded-lg cursor-pointer focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-emerald-400"
            />
          </div>
        </section>

        {/* Section 4: Scientific Radiometric Colormaps */}
        <section className="flex flex-col gap-2 pt-2 border-t border-[#2D3748]" aria-labelledby="colormap-heading">
          <div className="flex justify-between items-center">
            <span id="colormap-heading" className="text-[11px] font-mono uppercase tracking-wider text-slate-400 font-semibold">
              Radiometric Colormap
            </span>
            <span className="text-[10px] font-mono text-slate-400">dB Scale</span>
          </div>

          <div className="flex flex-col gap-1.5" role="radiogroup" aria-label="Colormaps">
            {COLORMAPS.map(map => (
              <label 
                key={map.id} 
                className={`flex items-center justify-between p-2 rounded-lg border cursor-pointer transition-colors ${
                  colormap === map.id 
                    ? 'border-emerald-500/40 bg-emerald-500/10' 
                    : 'border-[#2D3748] bg-[#0B0F17]/40 hover:bg-[#1A2234]/60'
                }`}
              >
                <div className="flex items-center gap-2">
                  <input 
                    type="radio" 
                    name="colormap-choice" 
                    value={map.id}
                    checked={colormap === map.id}
                    onChange={() => setColormap(map.id)}
                    className="text-emerald-500 bg-transparent border-slate-600 focus:ring-0"
                  />
                  <span className={`font-mono text-xs ${colormap === map.id ? 'text-slate-100 font-semibold' : 'text-slate-300'}`}>
                    {map.name}
                  </span>
                </div>
                <div className={`w-16 h-2 rounded bg-gradient-to-r ${map.gradient}`} />
              </label>
            ))}
          </div>

          {/* Calibrated dB Scale Legend */}
          <div className="mt-1 p-2 bg-[#0B0F17]/60 border border-[#2D3748] rounded-lg flex flex-col gap-1">
            <div className="w-full h-1.5 rounded bg-gradient-to-r from-blue-600 via-emerald-400 to-red-500" />
            <div className="flex justify-between font-mono text-[9px] text-slate-400">
              <span>-25 dB (Water)</span>
              <span>-12 dB</span>
              <span>0 dB (Urban)</span>
            </div>
          </div>
        </section>
      </div>

      {/* Inspector Footer Action (Send to Analytics Button) */}
      <div className="p-4 border-t border-[#2D3748] bg-[#0B0F17]/90 shrink-0">
        <a 
          href="analytics.html" 
          className="w-full py-2.5 px-4 bg-[#00DC82] hover:bg-[#00c574] text-[#0B0F17] font-bold text-sm rounded-lg flex items-center justify-center gap-2 tracking-wide transition-colors shadow-lg shadow-[#00DC82]/10 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-emerald-400 min-h-[42px]"
        >
          <span>Send to Analytics</span>
          <ArrowUpRight className="w-4 h-4" />
        </a>
      </div>
    </aside>
  );
};
