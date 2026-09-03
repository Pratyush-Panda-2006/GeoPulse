import { useEffect, useState } from "react";
import Globe from "./ui/globe";
import Speedometer from "./ui/speedometer";

export default function Telemetry() {
  const [istTime, setIstTime] = useState("--:--:--");
  const [latency, setLatency] = useState(122);
  const [gpuUsage, setGpuUsage] = useState({ percent: 21.7, vram: 1.3 });
  
  // Simulated SARStore metadata
  const [metadata] = useState({
    model: "SNUNet (ResNet34)",
    threshold: 0.45,
    execution_time_sec: 1.24,
    status: "SUCCESS",
    total_pixels: 1048576,
    changed_pixels: 45210,
    change_percentage: 4.31,
    num_change_clusters: 12
  });

  useEffect(() => {
    const timeInterval = setInterval(() => {
      const now = new Date();
      const options: Intl.DateTimeFormatOptions = { 
        timeZone: 'Asia/Kolkata', 
        hour12: false, 
        hour: '2-digit', 
        minute: '2-digit', 
        second: '2-digit' 
      };
      setIstTime(now.toLocaleTimeString('en-IN', options));
    }, 1000);

    const dataInterval = setInterval(() => {
      // Latency between 90 and 120
      setLatency(Math.floor(Math.random() * 31) + 90);
      
      let basePercent = 20 + (Math.random() * 15 - 5); 
      basePercent = Math.max(5, Math.min(basePercent, 95));
      const currentVram = (basePercent / 100) * 6.0;
      setGpuUsage({ percent: basePercent, vram: currentVram });
    }, 2500); // 2.5 seconds to make it slower and observable

    return () => {
      clearInterval(timeInterval);
      clearInterval(dataInterval);
    };
  }, []);

  const fmtNum = (n: number) => (typeof n === 'number' && isFinite(n)) ? n.toLocaleString() : '--';

  return (
    <div className="min-h-screen text-on-background relative antialiased selection:bg-primary/30 selection:text-primary overflow-hidden">
      <Globe />
      
      <div className="absolute inset-0 pointer-events-none z-[-1] grid grid-cols-4 md:grid-cols-8 lg:grid-cols-12 gap-sm lg:gap-gutter px-sm md:px-md lg:px-margin">
        {[...Array(12)].map((_, i) => (
          <div key={i} className={`border-l border-white/5 h-full ${i === 11 ? 'border-r' : ''} ${i >= 4 ? 'hidden md:block' : ''} ${i >= 8 ? 'hidden lg:block' : ''}`} />
        ))}
      </div>

      {/* TopNavBar */}
      <nav className="fixed top-0 left-0 right-0 z-50 flex justify-between items-center bg-black/40 backdrop-blur-xl border-b border-white/10 px-6 py-3">
        <a href="index.html" className="flex items-center gap-2 font-headline-md text-xl font-bold text-primary tracking-tighter uppercase transition-all">
          <div className="h-2.5 w-2.5 rounded-full bg-emerald-500 animate-pulse"></div>
          <span>GeoPulse</span>
        </a>
        <div className="hidden md:flex gap-6 lg:gap-8 items-center">
          <a className="font-semibold text-sm uppercase tracking-widest text-gray-400 hover:text-white transition-colors" href="overview.html">OVERVIEW</a>
          <a className="font-semibold text-sm uppercase tracking-widest text-gray-400 hover:text-white transition-colors" href="studio.html">STUDIO</a>
          <a className="font-semibold text-sm uppercase tracking-widest text-gray-400 hover:text-white transition-colors" href="analytics.html">ANALYTICS</a>
          <a className="font-semibold text-sm uppercase tracking-widest text-gray-400 hover:text-white transition-colors" href="explorer.html">EXPLORER</a>
          <a className="font-semibold text-sm uppercase tracking-widest text-gray-400 hover:text-white transition-colors" href="intelligence.html">Intelligence</a>
          <a className="font-semibold text-sm uppercase tracking-widest text-primary border-b-2 border-primary pb-1" href="telemetry.html">TELEMETRY</a>
        </div>
        <div className="flex gap-4 items-center">
          <a href="#" className="flex items-center gap-2 bg-primary/10 border border-primary/20 px-3 py-1 font-mono text-xs text-primary">
            <div className="w-2 h-2 rounded-full bg-primary animate-pulse"></div>
            <span className="uppercase tracking-widest hidden lg:inline">Link Active (UI DEMO)</span>
            <span className="uppercase tracking-widest lg:hidden">Active</span>
          </a>
        </div>
      </nav>

      <main className="flex-1 pt-24 px-8 md:px-12 lg:px-16 overflow-y-auto relative z-10 w-full max-w-[1920px] mx-auto pb-32">
        <header className="mb-10 border-b border-white/10 pb-4 flex flex-wrap justify-between items-end gap-4">
            <div>
                <h1 className="text-4xl md:text-5xl font-bold text-white uppercase tracking-tight shadow-black drop-shadow-lg">SENTINEL-1 TELEMETRY HUB</h1>
                <p className="italic text-gray-300 mt-2 max-w-2xl font-serif">Real-time health, link lock & CUDA compute telemetry for GeoPulse SAR Processing Engines.</p>
            </div>
            <div className="flex gap-3">
                <a href="explorer.html" className="bg-primary text-black px-5 py-2 font-semibold text-xs uppercase tracking-widest hover:bg-emerald-400 transition-all flex items-center gap-1.5">
                    Return to Explorer
                </a>
            </div>
        </header>

        <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
          {/* Connectivity Panel */}
          <div className="col-span-1 lg:col-span-4 bg-black/30 backdrop-blur-2xl border border-white/10 p-6 flex flex-col justify-between shadow-2xl">
              <div>
                  <div className="flex items-center justify-between mb-6">
                      <h3 className="font-semibold text-gray-300 uppercase tracking-widest text-sm">Connectivity <span className="text-[10px] text-purple-400 ml-2">(SIMULATED)</span></h3>
                  </div>
                  <div className="mb-4">
                      <span className="font-mono text-xs text-gray-400 block mb-1 uppercase tracking-widest">Active Link</span>
                      <span className="text-xl font-bold text-white font-mono">ESA SENTINEL-1</span>
                      <span className="font-mono text-xs text-gray-400 block mt-2 uppercase tracking-widest">Station Lock: ISTRAC, Bengaluru</span>
                      <span className="font-mono text-xs text-gray-400 block mt-2 uppercase tracking-widest">Last Update: <span>{istTime}</span> IST</span>
                  </div>
              </div>
              <div className="mt-4 pt-4 border-t border-white/10 border-dotted flex-1 flex flex-col justify-center items-center">
                  <Speedometer value={latency} max={200} label="DOWNLINK LATENCY" />
              </div>
          </div>

          {/* AI Engine Specs */}
          <div className="col-span-1 lg:col-span-8 bg-black/30 backdrop-blur-2xl border border-white/10 p-6 relative overflow-hidden shadow-2xl">
              <div className="relative z-10 flex flex-col h-full">
                  <div className="flex items-center justify-between mb-6">
                      <h3 className="font-semibold text-gray-300 uppercase tracking-widest text-sm">AI Compute Node <span className="text-[10px] text-purple-400 ml-2">(SIMULATED)</span></h3>
                  </div>
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                      <div className="bg-black/40 p-4 border border-white/5">
                          <span className="font-mono text-xs text-gray-400 block mb-2 uppercase tracking-widest">Framework</span>
                          <span className="text-lg font-bold text-white font-mono">PyTorch 2.x (SNUNet)</span>
                      </div>
                      <div className="bg-black/40 p-4 border border-white/5">
                          <span className="font-mono text-xs text-gray-400 block mb-2 uppercase tracking-widest">Hardware Accelerator</span>
                          <span className="text-lg font-bold text-white font-mono">CUDA: NVIDIA RTX 3050</span>
                      </div>
                  </div>
                  <div className="mt-6 border-t border-white/10 pt-6 border-dotted">
                      <div className="flex justify-between items-center mb-2">
                          <span className="font-mono text-xs text-gray-400 uppercase tracking-widest">GPU VRAM Usage</span>
                          <span className="text-xl text-cyan-400 font-mono tracking-tight">{gpuUsage.vram.toFixed(1)} GB / 6.0 GB</span>
                      </div>
                      <div className="w-full bg-black/50 border border-white/10 h-3">
                          <div className="bg-cyan-400 h-full transition-all duration-300" style={{ width: `${gpuUsage.percent}%` }}></div>
                      </div>
                  </div>
                  
                  {/* Embedded System Uptime and Inference Results */}
                  <div className="mt-8 grid grid-cols-1 xl:grid-cols-12 gap-6 flex-1">
                      {/* Historical Uptime Chart */}
                      <div className="xl:col-span-4 bg-black/40 border border-white/5 p-4 flex flex-col relative overflow-hidden">
                          <div className="relative z-10 flex flex-col h-full">
                              <div className="flex items-center justify-between mb-4 border-b border-white/10 pb-2">
                                  <h3 className="font-semibold text-gray-300 uppercase tracking-widest text-xs">System Uptime</h3>
                                  <span className="text-sm font-bold text-primary font-mono">99.98%</span>
                              </div>
                              <div className="flex-1 flex items-end space-x-1 min-h-[120px]">
                                  <div className="w-full h-full flex items-end space-x-2">
                                      <div className="bg-black/50 border border-white/10 w-full h-[90%] hover:bg-primary/50 transition-colors flex items-end justify-center p-1"><span className="text-[8px] font-mono text-gray-500">T-7</span></div>
                                      <div className="bg-black/50 border border-white/10 w-full h-[95%] hover:bg-primary/50 transition-colors flex items-end justify-center p-1"><span className="text-[8px] font-mono text-gray-500">T-6</span></div>
                                      <div className="bg-black/50 border border-white/10 w-full h-[100%] hover:bg-primary/50 transition-colors flex items-end justify-center p-1"><span className="text-[8px] font-mono text-gray-500">T-5</span></div>
                                      <div className="bg-black/50 border border-white/10 w-full h-[88%] hover:bg-primary/50 transition-colors flex items-end justify-center p-1"><span className="text-[8px] font-mono text-gray-500">T-4</span></div>
                                      <div className="bg-red-500/20 w-full h-[65%] hover:bg-red-500/50 transition-colors border border-red-500 flex items-end justify-center p-1"><span className="text-[8px] font-mono text-red-500">T-3</span></div>
                                      <div className="bg-black/50 border border-white/10 w-full h-[94%] hover:bg-primary/50 transition-colors flex items-end justify-center p-1"><span className="text-[8px] font-mono text-gray-500">T-2</span></div>
                                      <div className="bg-black/50 border border-white/10 w-full h-[99%] hover:bg-primary/50 transition-colors flex items-end justify-center p-1"><span className="text-[8px] font-mono text-primary">T-1</span></div>
                                  </div>
                              </div>
                              <div className="flex justify-between mt-2 font-mono text-[8px] text-gray-500 tracking-widest uppercase">
                                  <span>T-7d</span>
                                  <span>{istTime} IST</span>
                              </div>
                          </div>
                      </div>

                      {/* Real Inference Metadata */}
                      <div className="xl:col-span-8 bg-primary/5 border border-primary/20 p-4 flex flex-col relative overflow-hidden">
                          <div className="relative z-10 flex flex-col h-full">
                              <div className="flex items-center justify-between mb-4 border-b border-primary/20 pb-2">
                                  <h3 className="font-semibold text-primary uppercase tracking-widest text-xs">Inference Results <span className="text-[8px] text-primary ml-2 font-bold">(REAL DATA)</span></h3>
                              </div>
                              <div className="grid grid-cols-2 md:grid-cols-4 gap-3 h-full">
                                  <div className="bg-black/60 p-2 border border-primary/10 flex flex-col justify-center">
                                      <span className="font-mono text-[9px] text-gray-400 uppercase tracking-widest mb-1">Model Name</span>
                                      <span className="font-mono text-sm text-primary truncate" title={metadata.model}>{metadata.model}</span>
                                  </div>
                                  <div className="bg-black/60 p-2 border border-primary/10 flex flex-col justify-center">
                                      <span className="font-mono text-[9px] text-gray-400 uppercase tracking-widest mb-1">Threshold</span>
                                      <span className="font-mono text-sm text-primary">{metadata.threshold}</span>
                                  </div>
                                  <div className="bg-black/60 p-2 border border-primary/10 flex flex-col justify-center">
                                      <span className="font-mono text-[9px] text-gray-400 uppercase tracking-widest mb-1">Execution Time</span>
                                      <span className="font-mono text-sm text-primary">{metadata.execution_time_sec} s</span>
                                  </div>
                                  <div className="bg-black/60 p-2 border border-primary/10 flex flex-col justify-center">
                                      <span className="font-mono text-[9px] text-gray-400 uppercase tracking-widest mb-1">Run Status</span>
                                      <span className="font-mono text-sm text-emerald-400 uppercase">{metadata.status}</span>
                                  </div>
                                  <div className="bg-black/60 p-2 border border-primary/10 flex flex-col justify-center">
                                      <span className="font-mono text-[9px] text-gray-400 uppercase tracking-widest mb-1">Total Pixels</span>
                                      <span className="font-mono text-sm text-white">{fmtNum(metadata.total_pixels)}</span>
                                  </div>
                                  <div className="bg-black/60 p-2 border border-primary/10 flex flex-col justify-center">
                                      <span className="font-mono text-[9px] text-gray-400 uppercase tracking-widest mb-1">Changed Pixels</span>
                                      <span className="font-mono text-sm text-primary">{fmtNum(metadata.changed_pixels)}</span>
                                  </div>
                                  <div className="bg-black/60 p-2 border border-primary/10 flex flex-col justify-center">
                                      <span className="font-mono text-[9px] text-gray-400 uppercase tracking-widest mb-1">Change %</span>
                                      <span className="font-mono text-sm text-primary">{metadata.change_percentage}%</span>
                                  </div>
                                  <div className="bg-black/60 p-2 border border-primary/10 flex flex-col justify-center">
                                      <span className="font-mono text-[9px] text-gray-400 uppercase tracking-widest mb-1">Clusters</span>
                                      <span className="font-mono text-sm text-primary">{fmtNum(metadata.num_change_clusters)}</span>
                                  </div>
                              </div>
                          </div>
                      </div>
                  </div>
              </div>
          </div>
        </div>
      </main>
    </div>
  );
}
