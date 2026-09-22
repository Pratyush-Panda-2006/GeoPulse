import React, { useRef, useState } from 'react';
import { Upload, Search, Image as ImageIcon, FileText, AlertTriangle, Loader2 } from 'lucide-react';
import { retrievalApi } from '../../lib/api';
import type { RetrievalResult } from '../../types/retrieval';
import { RetrievalResultCard } from './RetrievalResultCard';

interface RetrievalSidebarProps {
  onResultsFetched: (results: RetrievalResult[]) => void;
  onSelectResult: (result: RetrievalResult) => void;
  selectedResult: RetrievalResult | null;
  results: RetrievalResult[];
}

export const RetrievalSidebar: React.FC<RetrievalSidebarProps> = ({
  onResultsFetched,
  onSelectResult,
  selectedResult,
  results
}) => {
  const [searchMode, setSearchMode] = useState<'IMAGE' | 'TEXT'>('IMAGE');
  const [isSearching, setIsSearching] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [previewImage, setPreviewImage] = useState<string | null>(null);
  
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleFileChange = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    // Create local preview
    const objectUrl = URL.createObjectURL(file);
    setPreviewImage(objectUrl);
    setError(null);
    setIsSearching(true);
    
    try {
      const response = await retrievalApi.searchImage(file, 10);
      onResultsFetched(response.results);
      if (response.results.length > 0) {
        onSelectResult(response.results[0]);
      }
    } catch (err: any) {
      console.error(err);
      setError(err.message || 'Failed to search archive.');
      onResultsFetched([]);
    } finally {
      setIsSearching(false);
    }
  };

  const handleUploadClick = () => {
    if (searchMode === 'IMAGE' && fileInputRef.current) {
      fileInputRef.current.click();
    }
  };

  return (
    <div className="w-80 h-full bg-[#0B0F17] border-r border-[#2D3748] flex flex-col shrink-0">
      
      {/* Search Mode Toggle */}
      <div className="p-4 border-b border-[#2D3748]">
        <div className="flex bg-[#1A2234] rounded-lg p-1 border border-[#2D3748]">
          <button 
            onClick={() => setSearchMode('IMAGE')}
            className={`flex-1 py-1.5 text-xs font-mono font-bold rounded flex items-center justify-center gap-2 transition-colors ${
              searchMode === 'IMAGE' ? 'bg-[#2D3748] text-emerald-400' : 'text-slate-500 hover:text-slate-300'
            }`}
          >
            <ImageIcon className="w-3.5 h-3.5" />
            IMAGE
          </button>
          <button 
            onClick={() => setSearchMode('TEXT')}
            className={`flex-1 py-1.5 text-xs font-mono font-bold rounded flex items-center justify-center gap-2 transition-colors ${
              searchMode === 'TEXT' ? 'bg-[#2D3748] text-emerald-400' : 'text-slate-500 hover:text-slate-300'
            }`}
          >
            <FileText className="w-3.5 h-3.5" />
            TEXT
          </button>
        </div>
      </div>

      {/* Query Input Area */}
      <div className="p-4 border-b border-[#2D3748]">
        <h3 className="text-[10px] font-mono tracking-widest text-slate-500 mb-3 uppercase">Archive Search Query</h3>
        
        {searchMode === 'IMAGE' ? (
          <div 
            onClick={handleUploadClick}
            className={`relative w-full aspect-video rounded-lg border-2 border-dashed flex flex-col items-center justify-center cursor-pointer transition-all overflow-hidden ${
              previewImage 
                ? 'border-[#2D3748] hover:border-emerald-500/50' 
                : 'border-[#2D3748] hover:border-emerald-500 hover:bg-[#1A2234]'
            }`}
          >
            {previewImage ? (
              <>
                <img src={previewImage} alt="Query preview" className="absolute inset-0 w-full h-full object-cover opacity-60" />
                <div className="absolute inset-0 bg-black/40 flex items-center justify-center opacity-0 hover:opacity-100 transition-opacity">
                  <span className="text-xs font-mono text-white bg-black/60 px-3 py-1 rounded border border-white/20">CHANGE IMAGE</span>
                </div>
              </>
            ) : (
              <>
                <Upload className="w-6 h-6 text-slate-500 mb-2" />
                <span className="text-xs font-mono text-slate-400 text-center px-4">
                  Drop SAR patch or click to upload
                </span>
              </>
            )}
            <input 
              type="file" 
              ref={fileInputRef} 
              className="hidden" 
              accept="image/*"
              onChange={handleFileChange}
            />
          </div>
        ) : (
          <div className="w-full aspect-video rounded-lg border border-[#2D3748] bg-[#1A2234] flex flex-col items-center justify-center p-4 text-center">
            <AlertTriangle className="w-6 h-6 text-amber-500 mb-2 opacity-80" />
            <span className="text-xs font-mono text-slate-400">
              Semantic text retrieval
            </span>
            <span className="text-[10px] font-mono text-amber-500/80 mt-1">
              Backend integration pending
            </span>
          </div>
        )}
      </div>

      {/* Results Area */}
      <div className="flex-1 overflow-y-auto p-4 custom-scrollbar">
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-[10px] font-mono tracking-widest text-slate-500 uppercase">
            Ranked Observations
          </h3>
          {results.length > 0 && (
            <span className="text-[10px] font-mono text-emerald-500 bg-emerald-500/10 px-2 py-0.5 rounded">
              {results.length} FOUND
            </span>
          )}
        </div>

        {isSearching ? (
          <div className="flex flex-col items-center justify-center py-12 text-slate-400">
            <Loader2 className="w-6 h-6 animate-spin mb-3 text-emerald-500" />
            <span className="text-xs font-mono animate-pulse">Searching local archive...</span>
          </div>
        ) : error ? (
          <div className="p-4 bg-red-500/10 border border-red-500/30 rounded-lg text-center">
            <AlertTriangle className="w-5 h-5 text-red-400 mx-auto mb-2" />
            <p className="text-xs font-mono text-red-300">{error}</p>
          </div>
        ) : results.length > 0 ? (
          <div className="flex flex-col gap-3">
            {results.map((result) => (
              <RetrievalResultCard 
                key={result.record.tile_id}
                result={result}
                isSelected={selectedResult?.record.tile_id === result.record.tile_id}
                onSelect={onSelectResult}
              />
            ))}
          </div>
        ) : (
          <div className="flex flex-col items-center justify-center py-12 text-slate-500 text-center px-4">
            <Search className="w-8 h-8 mb-3 opacity-20" />
            <span className="text-xs font-mono">
              {searchMode === 'IMAGE' ? 'Select an image to search the archive.' : 'Text search not implemented.'}
            </span>
          </div>
        )}
      </div>
    </div>
  );
};
