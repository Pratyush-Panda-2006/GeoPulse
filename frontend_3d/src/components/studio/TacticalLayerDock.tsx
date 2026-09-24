import React from 'react';
import { Layers, Check } from 'lucide-react';

export interface TacticalLayer {
  id: string;
  name: string;
  spec: string;
  sensor: string;
  description: string;
  swatchGradient: string;
}

export const TACTICAL_LAYERS: TacticalLayer[] = [
  {
    id: 't2',
    name: 'Survey Target (T2)',
    spec: 'Polarimetric SAR',
    sensor: 'Sentinel-1 C-SAR',
    description: 'Current monitoring pass',
    swatchGradient: 'from-emerald-600 to-teal-400'
  },
  {
    id: 't1',
    name: 'Baseline Pass (T1)',
    spec: 'Temporal Reference',
    sensor: 'Sentinel-1 C-SAR',
    description: 'Prior baseline acquisition',
    swatchGradient: 'from-slate-600 to-slate-400'
  },
  {
    id: 'mask',
    name: 'Binary Change Mask',
    spec: 'p > 0.60 Delta Detection',
    sensor: 'SNUNet Engine',
    description: 'Thresholded change pixels',
    swatchGradient: 'from-slate-950 via-red-600 to-red-400'
  },
  {
    id: 'heatmap',
    name: 'Confidence Heatmap',
    spec: 'Probabilistic Surface',
    sensor: 'Tensor Analytics',
    description: 'Continuous anomaly confidence',
    swatchGradient: 'from-blue-600 via-emerald-400 to-amber-400'
  },
  {
    id: 'falsecolor',
    name: 'Pauli Dual-Pol',
    spec: 'VV / VH / Ratio',
    sensor: 'Decomposition',
    description: 'Surface vs volume scattering',
    swatchGradient: 'from-rose-500 via-emerald-500 to-blue-500'
  },
  {
    id: 'overlay',
    name: 'Composite Overlay',
    spec: 'Multi-Temporal Fusion',
    sensor: 'Mission Overlay',
    description: 'T2 survey with change mask',
    swatchGradient: 'from-slate-800 via-amber-500 to-emerald-400'
  },
  {
    id: 'boxes',
    name: 'Highlight Changes',
    spec: 'Target Detections',
    sensor: 'AI BOXES',
    description: 'Labeled target detections and cluster bounding boxes',
    swatchGradient: 'from-amber-500 via-red-500 to-rose-600'
  }
];

interface TacticalLayerDockProps {
  activeLayer: string;
  onSelectLayer: (layerId: string) => void;
}

export const TacticalLayerDock: React.FC<TacticalLayerDockProps> = ({
  activeLayer,
  onSelectLayer
}) => {
  return (
    <section className="flex flex-col gap-3 select-none" aria-labelledby="layer-dock-heading">
      {/* Section Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Layers className="w-4 h-4 text-emerald-400" />
          <h3 id="layer-dock-heading" className="text-xs font-mono uppercase tracking-wider text-slate-200 font-semibold">
            Active Raster Layer Stack
          </h3>
        </div>
        <span className="text-[10px] font-mono text-slate-400">{TACTICAL_LAYERS.length} AVAILABLE</span>
      </div>

      {/* 2-Column High-Density Tactical Grid */}
      <div className="grid grid-cols-2 gap-2.5" role="radiogroup" aria-label="SAR Raster Layers">
        {TACTICAL_LAYERS.map(layer => {
          const isActive = activeLayer === layer.id;
          const isBoxes = layer.id === 'boxes';
          return (
            <button
              key={layer.id}
              role="radio"
              aria-checked={isActive}
              onClick={() => onSelectLayer(layer.id)}
              className={`group relative p-2.5 rounded-lg border text-left flex flex-col justify-between transition-all duration-150 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-emerald-400 ${
                isActive
                  ? isBoxes
                    ? 'bg-amber-950/40 border-amber-400/80 ring-1 ring-amber-400 shadow-[0_0_12px_rgba(245,158,11,0.25)]'
                    : 'bg-slate-900/95 border-emerald-400/80 ring-1 ring-emerald-400 shadow-[0_0_12px_rgba(16,185,129,0.25)]'
                  : 'bg-[#0B0F17]/70 border-[#2D3748] hover:bg-slate-800/60 hover:border-slate-600'
              }`}
            >
              {/* Header: Swatch + Spec Badge */}
              <div className="flex items-center justify-between w-full mb-1.5">
                <div 
                  className={`w-4 h-4 rounded shadow-sm bg-gradient-to-br ${layer.swatchGradient} border border-white/20`} 
                  title={`Swatch: ${layer.name}`}
                />
                <span className={`text-[9px] font-mono px-1.5 py-0.5 rounded border tracking-tight ${
                  isActive 
                    ? isBoxes
                      ? 'border-amber-500/40 bg-amber-500/10 text-amber-300 font-bold'
                      : 'border-emerald-500/40 bg-emerald-500/10 text-emerald-300 font-bold' 
                    : isBoxes
                      ? 'border-amber-500/30 bg-amber-500/5 text-amber-400'
                      : 'border-[#2D3748] bg-[#0B0F17] text-slate-400'
                }`}>
                  {layer.sensor}
                </span>
              </div>

              {/* Layer Title */}
              <span className={`text-xs font-semibold tracking-tight line-clamp-1 ${
                isActive 
                  ? isBoxes ? 'text-amber-200' : 'text-emerald-200' 
                  : 'text-slate-200 group-hover:text-slate-100'
              }`}>
                {layer.name}
              </span>

              {/* Sub-spec & Indicator */}
              <div className="mt-2 pt-1.5 border-t border-[#2D3748]/80 flex items-center justify-between text-[9px] font-mono text-slate-400">
                <span className="truncate max-w-[80%]" title={layer.spec}>{layer.spec}</span>
                {isActive ? (
                  <Check className={`w-3.5 h-3.5 shrink-0 ${isBoxes ? 'text-amber-400' : 'text-emerald-400'}`} />
                ) : (
                  <span className="w-2 h-2 rounded-full border border-slate-600 shrink-0 group-hover:border-slate-400" />
                )}
              </div>
            </button>
          );
        })}
      </div>
    </section>
  );
};
