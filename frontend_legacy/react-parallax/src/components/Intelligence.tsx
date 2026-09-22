import { useState, useRef, useEffect } from 'react';
import { Bell, User, Upload, Search, Crosshair, Map, Calendar, Clock } from 'lucide-react';
import type { ViewState } from '../App';
import { retrievalApi } from '../lib/api';
import type { RetrievalResult } from '../types/retrieval';

interface IntelligenceProps {
  onViewChange: (view: ViewState) => void;
  onOpenAnalysis?: (t1Url: string, t2Url: string) => void;
}

export default function Intelligence({ onViewChange, onOpenAnalysis }: IntelligenceProps) {
  const [searchMode, setSearchMode] = useState<'IMAGE' | 'TEXT'>('IMAGE');
  const [isSearching, setIsSearching] = useState(false);
  const [isDragging, setIsDragging] = useState(false);
  const [results, setResults] = useState<RetrievalResult[]>([]);
  const [selectedResult, setSelectedResult] = useState<RetrievalResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [uploadedImageUrl, setUploadedImageUrl] = useState<string | null>(null);
  const [textQuery, setTextQuery] = useState('');
  const [timeline, setTimeline] = useState<import('../lib/api').TimelineResponse | null>(null);
  const [isLoadingTimeline, setIsLoadingTimeline] = useState(false);
  const [timelineError, setTimelineError] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const processFile = async (file: File) => {
    setIsSearching(true);
    setError(null);
    setResults([]);
    setSelectedResult(null);

    try {
      const response = await retrievalApi.searchImage(file);
      setResults(response.results);
    } catch (err: any) {
      setError(err.message || 'An error occurred during retrieval');
    } finally {
      setIsSearching(false);
    }
  };

  const executeTextSearch = async () => {
    if (!textQuery.trim() || isSearching) return;
    
    setIsSearching(true);
    setError(null);
    setResults([]);
    setSelectedResult(null);
    setUploadedImageUrl(null); // Clear uploaded image since we're in text mode

    try {
      const response = await retrievalApi.searchText(textQuery.trim());
      setResults(response.results);
    } catch (err: any) {
      setError(err.message || 'An error occurred during text retrieval');
    } finally {
      setIsSearching(false);
    }
  };

  useEffect(() => {
    if (!selectedResult) {
      setTimeline(null);
      setTimelineError(null);
      return;
    }

    const loadTimeline = async () => {
      setIsLoadingTimeline(true);
      setTimelineError(null);

      try {
        const response = await retrievalApi.getTimeline(
          selectedResult.record.bounds,
          undefined,
          undefined,
          selectedResult.record.crs
        );

        setTimeline(response);
      } catch (err: any) {
        setTimeline(null);
        setTimelineError(err.message || 'Unable to load historical timeline');
      } finally {
        setIsLoadingTimeline(false);
      }
    };

    loadTimeline();
  }, [selectedResult]);

  const handleImageUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      if (uploadedImageUrl) URL.revokeObjectURL(uploadedImageUrl);
      setUploadedImageUrl(URL.createObjectURL(file));
      processFile(file);
    }
  };

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    if (!isSearching) setIsDragging(true);
  };

  const handleDragLeave = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
    if (isSearching) return;
    
    const file = e.dataTransfer.files?.[0];
    if (file && (file.type === 'image/png' || file.type === 'image/jpeg')) {
      if (uploadedImageUrl) URL.revokeObjectURL(uploadedImageUrl);
      setUploadedImageUrl(URL.createObjectURL(file));
      processFile(file);
    } else if (file) {
      setError('Please upload a valid PNG or JPEG image.');
    }
  };

  return (
    <div className="h-screen w-screen flex flex-col bg-[#0B0F17] text-slate-100 overflow-hidden font-sans select-none">
      {/* 1. Global Mission Bar (Exact Match with GeoPulseStudio) */}
      <header className="h-12 px-6 bg-[#0B0F17] border-b border-[#2D3748] relative flex items-center justify-between text-xs select-none z-50 shrink-0">
        <div className="flex items-center gap-2 font-mono font-bold tracking-wider text-[#00DC82] shrink-0">
          <span className="w-2 h-2 rounded-full bg-[#00DC82]" />
          <span className="text-sm font-bold tracking-wider uppercase">GeoPulse</span>
        </div>

        <nav className="hidden md:flex items-center gap-8 text-xs font-mono tracking-wider absolute left-1/2 -translate-x-1/2">
          <a href="overview.html" className="text-slate-400 hover:text-slate-100 transition-colors py-1">OVERVIEW</a>
          <button onClick={() => onViewChange('STUDIO')} className="text-slate-400 hover:text-slate-100 transition-colors py-1">STUDIO</button>
          <a href="analytics.html" className="text-slate-400 hover:text-slate-100 transition-colors py-1">ANALYTICS</a>
          <a href="explorer.html" className="text-slate-400 hover:text-slate-100 transition-colors py-1">EXPLORER</a>
          <button onClick={() => onViewChange('INTELLIGENCE')} className="text-[#00DC82] font-semibold border-b-2 border-[#00DC82] pb-0.5">INTELLIGENCE</button>
          <button onClick={() => onViewChange('TELEMETRY')} className="text-slate-400 hover:text-slate-100 transition-colors py-1">TELEMETRY</button>
        </nav>

        <div className="flex items-center gap-4 shrink-0">
          <button className="flex items-center gap-2 px-3 py-1 bg-[#00DC82]/5 border border-[#00DC82]/40 rounded text-[#00DC82] font-mono text-xs tracking-tight hover:bg-[#00DC82]/10 transition-colors" title="Copernicus Data Space Ecosystem Link Active">
            <span className="w-1.5 h-1.5 rounded-full bg-[#00DC82] animate-pulse" />
            <span>CDSE SATELLITE LINK: ACTIVE</span>
          </button>
          <button className="text-slate-400 hover:text-slate-100 p-1 transition-colors" title="System Notifications">
            <Bell className="w-4 h-4" />
          </button>
          <button className="text-slate-400 hover:text-slate-100 p-1 transition-colors" title="Operator Profile">
            <User className="w-4 h-4" />
          </button>
        </div>
      </header>

      {/* 2. Intelligence Workspace */}
      <main className="flex-1 w-full h-[calc(100vh-48px)] flex overflow-hidden">
        
        {/* Left Panel: Search Console */}
        <div className="w-[400px] border-r border-[#2D3748] bg-[#0d131f] flex flex-col z-10 shrink-0 shadow-2xl">
          <div className="p-5 border-b border-[#2D3748]">
            <h2 className="text-sm font-mono font-bold tracking-widest text-slate-200 mb-4 flex items-center gap-2 uppercase">
              <Crosshair className="w-4 h-4 text-[#00DC82]" />
              Retrieval Search
            </h2>
            <div className="flex bg-[#131B2A] rounded p-1 mb-6 border border-[#2D3748]">
              <button 
                onClick={() => setSearchMode('IMAGE')}
                className={`flex-1 py-1.5 text-xs font-mono font-bold tracking-wider rounded ${searchMode === 'IMAGE' ? 'bg-[#00DC82]/10 text-[#00DC82]' : 'text-slate-500 hover:text-slate-300'}`}
              >
                IMAGE
              </button>
              <button 
                onClick={() => setSearchMode('TEXT')}
                className={`flex-1 py-1.5 text-xs font-mono font-bold tracking-wider rounded ${searchMode === 'TEXT' ? 'bg-[#00DC82]/10 text-[#00DC82]' : 'text-slate-500 hover:text-slate-300'}`}
              >
                TEXT
              </button>
            </div>

            {searchMode === 'IMAGE' ? (
              <div className="space-y-4">
                <input 
                  type="file" 
                  ref={fileInputRef}
                  onChange={handleImageUpload}
                  accept="image/png,image/jpeg"
                  className="hidden" 
                />
                <button 
                  onClick={() => fileInputRef.current?.click()}
                  onDragOver={handleDragOver}
                  onDragLeave={handleDragLeave}
                  onDrop={handleDrop}
                  disabled={isSearching}
                  className={`w-full flex flex-col items-center justify-center gap-3 p-8 border-2 border-dashed rounded transition-all group disabled:opacity-50 disabled:cursor-not-allowed ${isDragging ? 'border-[#00DC82] bg-[#00DC82]/10' : 'border-[#2D3748] hover:border-[#00DC82]/50 hover:bg-[#00DC82]/5'}`}
                >
                  <Upload className={`w-8 h-8 ${isSearching ? 'text-[#00DC82] animate-bounce' : isDragging ? 'text-[#00DC82] scale-110' : 'text-slate-400 group-hover:text-[#00DC82]'}`} />
                  <div className="text-center pointer-events-none">
                    <div className={`text-xs font-mono font-bold tracking-wider mb-1 ${isDragging ? 'text-[#00DC82]' : 'text-slate-300'}`}>
                      {isSearching ? 'PROCESSING TILE...' : isDragging ? 'DROP TO UPLOAD' : 'UPLOAD SAR TILE'}
                    </div>
                    <div className={`text-[10px] ${isDragging ? 'text-[#00DC82]/70' : 'text-slate-500'}`}>
                      {isDragging ? 'Release to begin search' : 'Supports PNG, JPEG'}
                    </div>
                  </div>
                </button>
              </div>
            ) : (
              <div className="space-y-4 relative">
                <div className="p-3 bg-[#131B2A] border border-[#2D3748] rounded focus-within:border-[#00DC82]/50 transition-colors">
                  <div className="text-[10px] font-mono text-slate-500 mb-2 uppercase tracking-wider">Semantic Query</div>
                  <textarea 
                    value={textQuery}
                    onChange={(e) => setTextQuery(e.target.value)}
                    onKeyDown={(e) => {
                      if (e.key === 'Enter' && !e.shiftKey) {
                        e.preventDefault();
                        executeTextSearch();
                      }
                    }}
                    disabled={isSearching}
                    placeholder="e.g. dense urban area with buildings and roads"
                    className="w-full bg-transparent text-sm text-slate-300 outline-none font-sans min-h-[80px] resize-none disabled:opacity-50"
                  />
                </div>
                <button 
                  onClick={executeTextSearch}
                  disabled={isSearching || !textQuery.trim()}
                  className="w-full py-2 bg-[#2D3748] hover:bg-[#00DC82]/20 text-slate-300 hover:text-[#00DC82] disabled:opacity-50 disabled:hover:bg-[#2D3748] disabled:hover:text-slate-300 disabled:cursor-not-allowed text-xs font-mono font-bold rounded flex justify-center items-center gap-2 transition-colors border border-transparent hover:border-[#00DC82]/50"
                >
                  <Search className={`w-3 h-3 ${isSearching ? 'animate-spin' : ''}`} />
                  {isSearching ? 'SEARCHING ARCHIVE...' : 'EXECUTE QUERY'}
                </button>
              </div>
            )}

            {error && (
              <div className="mt-4 p-3 border border-red-500/30 bg-red-500/10 rounded text-xs font-mono text-red-400">
                {error}
              </div>
            )}
          </div>

          <div className="flex-1 overflow-y-auto p-5 bg-[#0B0F17]">
            <h3 className="text-[10px] font-mono font-bold text-slate-500 uppercase tracking-widest mb-4">
              {results.length > 0 ? `FAISS Results (${results.length})` : 'Awaiting Query'}
            </h3>
            
            <div className="space-y-3">
              {results.map((result) => (
                <div 
                  key={result.record.tile_id}
                  onClick={() => setSelectedResult(result)}
                  className={`p-3 border rounded cursor-pointer transition-all ${selectedResult?.record.tile_id === result.record.tile_id ? 'border-[#00DC82] bg-[#00DC82]/10' : 'border-[#2D3748] bg-[#131B2A] hover:border-slate-500'}`}
                >
                  <div className="flex justify-between items-start mb-2">
                    <span className="text-[10px] font-mono font-bold text-slate-400 bg-black/40 px-1.5 py-0.5 rounded">RANK {result.rank}</span>
                    <span className="text-[10px] font-mono font-bold text-[#00DC82]">SIMILARITY: {result.score.toFixed(3)}</span>
                  </div>
                  <div className="text-sm font-semibold text-slate-200 mb-1">{result.record.location}</div>
                  <div className="text-xs text-slate-400 flex items-center gap-1.5 mb-2 font-mono">
                    <Calendar className="w-3 h-3" />
                    ACQUISITION: {result.record.acquisition_date || result.record.date_label}
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* Right Panel: Result Inspection Workspace */}
        <div className="flex-1 bg-black relative flex flex-col">
          {selectedResult ? (
            <>
              {/* Toolbar */}
              <div className="absolute top-4 left-4 right-4 z-20 flex justify-between items-start pointer-events-none">
                <div className="bg-[#0B0F17]/90 backdrop-blur border border-[#2D3748] rounded shadow-2xl p-4 pointer-events-auto w-[320px]">
                  <h3 className="text-xs font-mono font-bold text-slate-300 uppercase tracking-widest border-b border-[#2D3748] pb-2 mb-3">Location Details</h3>
                  <div className="space-y-3">
                    <div>
                      <div className="text-[10px] font-mono text-slate-500 uppercase tracking-widest">Region</div>
                      <div className="text-sm font-semibold text-slate-200">{selectedResult.record.location}</div>
                    </div>
                    <div>
                      <div className="text-[10px] font-mono text-slate-500 uppercase tracking-widest">Acquisition</div>
                      <div className="text-xs font-mono text-slate-300">{selectedResult.record.acquisition_date || selectedResult.record.date_label}</div>
                    </div>
                    <div>
                      <div className="text-[10px] font-mono text-slate-500 uppercase tracking-widest">Similarity Score</div>
                      <div className="text-xs font-mono text-[#00DC82]">{selectedResult.score.toFixed(4)}</div>
                    </div>
                  </div>
                </div>

                <div className="bg-[#0B0F17]/90 backdrop-blur border border-[#2D3748] rounded shadow-2xl p-4 pointer-events-auto w-[320px]">
                  <h3 className="text-xs font-mono font-bold text-slate-300 uppercase tracking-widest border-b border-[#2D3748] pb-2 mb-3">Provenance / Telemetry</h3>
                  <div className="space-y-2">
                    <div className="flex justify-between">
                      <span className="text-[10px] font-mono text-slate-500 uppercase">Sensor</span>
                      <span className="text-[10px] font-mono text-slate-300">SENTINEL-1 SAR</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-[10px] font-mono text-slate-500 uppercase">CRS</span>
                      <span className="text-[10px] font-mono text-slate-300">{selectedResult.record.crs}</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-[10px] font-mono text-slate-500 uppercase">Bounds (B, L)</span>
                      <span className="text-[10px] font-mono text-slate-300">{selectedResult.record.bounds.bottom.toFixed(4)}, {selectedResult.record.bounds.left.toFixed(4)}</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-[10px] font-mono text-slate-500 uppercase">Bounds (T, R)</span>
                      <span className="text-[10px] font-mono text-slate-300">{selectedResult.record.bounds.top.toFixed(4)}, {selectedResult.record.bounds.right.toFixed(4)}</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-[10px] font-mono text-slate-500 uppercase">Source TIFF</span>
                      <span className="text-[10px] font-mono text-slate-300 truncate max-w-[150px]" title={selectedResult.record.source_tiff}>{selectedResult.record.source_tiff}</span>
                    </div>
                  </div>

                  <div className="mt-4 pt-4 border-t border-[#2D3748]">
                    <button 
                      onClick={() => {
                        if (onOpenAnalysis && uploadedImageUrl) {
                          onOpenAnalysis(uploadedImageUrl, retrievalApi.getTileImageUrl(selectedResult.record.tile_id));
                        } else {
                          onViewChange('STUDIO');
                        }
                      }}
                      className="w-full py-2 bg-[#00DC82]/10 border border-[#00DC82]/40 hover:bg-[#00DC82]/20 text-[#00DC82] text-xs font-mono font-bold tracking-widest transition-colors flex items-center justify-center gap-2"
                    >
                      <Map className="w-4 h-4" />
                      OPEN ANALYSIS
                    </button>
                  </div>
                </div>
              </div>

              {/* Central Raster Tile */}
              <div className="w-full h-full flex items-center justify-center bg-[#05080c] relative">
                {/* Simulated crosshairs */}
                <div className="absolute inset-0 pointer-events-none">
                  <div className="absolute top-1/2 left-0 right-0 h-[1px] bg-[#00DC82]/20" />
                  <div className="absolute left-1/2 top-0 bottom-0 w-[1px] bg-[#00DC82]/20" />
                  <Crosshair className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-8 h-8 text-[#00DC82]/40 stroke-1" />
                </div>
                
                <img 
                  src={retrievalApi.getTileImageUrl(selectedResult.record.tile_id)}
                  alt="Retrieved SAR Tile"
                  className="max-w-[80%] max-h-[80%] object-contain border border-[#2D3748] shadow-2xl z-10"
                />
              </div>

              {/* Multi-Temporal Timeline */}
              <div className="absolute bottom-6 left-1/2 -translate-x-1/2 bg-[#0B0F17]/95 backdrop-blur border border-[#2D3748] rounded px-6 py-4 shadow-2xl min-w-[560px] max-w-[80%]">
                <div className="flex items-center justify-between mb-4">
                  <div className="flex items-center gap-2">
                    <Clock className="w-3 h-3 text-[#00DC82]" />
                    <span className="text-[10px] font-mono font-bold text-slate-300 uppercase tracking-widest">
                      Historical Timeline
                    </span>
                  </div>

                  {timeline && (
                    <span className="text-[10px] font-mono text-[#00DC82]">
                      {timeline.count} OBSERVATIONS
                    </span>
                  )}
                </div>

                {isLoadingTimeline ? (
                  <div className="py-4 text-center text-[10px] font-mono text-slate-500 uppercase tracking-widest">
                    LOADING HISTORICAL OBSERVATIONS...
                  </div>
                ) : timelineError ? (
                  <div className="py-4 text-center text-[10px] font-mono text-red-400">
                    {timelineError}
                  </div>
                ) : timeline && timeline.observations.length > 0 ? (
                  <div className="flex items-start justify-center gap-0">
                    {timeline.observations.map((observation, index) => (
                      <div
                        key={observation.scene_id}
                        className="flex items-start"
                      >
                        <div className="flex flex-col items-center min-w-[110px]">
                          <div className="w-3 h-3 rounded-full border-2 border-[#00DC82] bg-[#0B0F17]" />

                          <span className="mt-2 text-[10px] font-mono text-slate-300 whitespace-nowrap">
                            {new Date(observation.acquisition_date).toLocaleDateString(
                              undefined,
                              {
                                day: '2-digit',
                                month: 'short',
                                year: 'numeric',
                              }
                            )}
                          </span>

                          <span className="mt-1 text-[9px] font-mono text-slate-500">
                            {observation.assets.length > 0
                              ? `${observation.assets.length} LOCAL ASSET${observation.assets.length > 1 ? 'S' : ''}`
                              : 'ARCHIVE ONLY'}
                          </span>
                        </div>

                        {index < timeline.observations.length - 1 && (
                          <div className="w-10 h-[1px] bg-slate-700 mt-1.5" />
                        )}
                      </div>
                    ))}
                  </div>
                ) : (
                  <div className="py-4 text-center text-[10px] font-mono text-slate-500 uppercase tracking-widest">
                    NO HISTORICAL OBSERVATIONS FOUND
                  </div>
                )}
              </div>
            </>
          ) : (
            <div className="w-full h-full flex flex-col items-center justify-center opacity-30 text-slate-500 font-mono text-sm tracking-widest bg-[url('/grid.svg')]">
              <Crosshair className="w-16 h-16 mb-4 opacity-50" />
              <div>AWAITING RETRIEVAL TARGET</div>
            </div>
          )}
        </div>
      </main>
    </div>
  );
}
