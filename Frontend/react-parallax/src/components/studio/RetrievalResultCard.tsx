import React from 'react';
import type { RetrievalResult } from '../../types/retrieval';
import { Map, Calendar, Crop } from 'lucide-react';

interface RetrievalResultCardProps {
  result: RetrievalResult;
  isSelected: boolean;
  onSelect: (result: RetrievalResult) => void;
}

export const RetrievalResultCard: React.FC<RetrievalResultCardProps> = ({
  result,
  isSelected,
  onSelect
}) => {
  const { rank, score, record } = result;
  
  return (
    <div 
      onClick={() => onSelect(result)}
      className={`p-3 rounded-lg border transition-all cursor-pointer select-none group ${
        isSelected 
          ? 'bg-[#00DC82]/10 border-[#00DC82]/50 shadow-[0_0_15px_rgba(0,220,130,0.15)]' 
          : 'bg-[#1A2234] border-[#2D3748] hover:border-slate-500 hover:bg-[#1A2234]/80'
      }`}
    >
      <div className="flex justify-between items-start mb-2">
        <div className="flex items-center gap-2">
          <span className={`text-xs font-mono font-bold px-1.5 py-0.5 rounded ${
            isSelected ? 'bg-[#00DC82] text-slate-900' : 'bg-slate-700 text-slate-300'
          }`}>
            #{rank.toString().padStart(2, '0')}
          </span>
          <span className="text-sm font-bold tracking-wide uppercase text-slate-100 group-hover:text-white">
            {record.location}
          </span>
        </div>
        <div className="text-right">
          <div className="text-[10px] text-slate-400 font-mono tracking-tighter uppercase">Similarity</div>
          <div className={`text-sm font-mono font-bold ${isSelected ? 'text-[#00DC82]' : 'text-emerald-400'}`}>
            {score.toFixed(4)}
          </div>
        </div>
      </div>

      <div className="grid grid-cols-2 gap-y-2 mt-3 text-xs font-mono">
        <div className="flex items-center gap-1.5 text-slate-400">
          <Calendar className="w-3.5 h-3.5" />
          <span>{record.date_label || 'Unknown Date'}</span>
        </div>
        <div className="flex items-center gap-1.5 text-slate-400">
          <Map className="w-3.5 h-3.5" />
          <span>{record.crs || 'Unknown CRS'}</span>
        </div>
        <div className="flex items-center gap-1.5 text-slate-400 col-span-2">
          <Crop className="w-3.5 h-3.5" />
          <span className="truncate" title={record.tile_id}>
            {record.tile_id}
          </span>
        </div>
      </div>
    </div>
  );
};
