import React, { useState } from 'react';
import CesiumViewerComponent from './components/CesiumViewer';
import { fetchTimeline, fetchChangeDetection } from './api/timeline';

const ENABLE_3D_CHANGE_VIEW = false;

const App: React.FC = () => {
  const [isSarVisible, setIsSarVisible] = useState(true);
  const [activeLayer, setActiveLayer] = useState<'T1' | 'T2'>('T1');
  
  const [isDetecting, setIsDetecting] = useState(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  const [bbox, setBbox] = useState<[number, number, number, number] | null>(null);
  const [t1Image, setT1Image] = useState<string | null>(null);
  const [t2Image, setT2Image] = useState<string | null>(null);

  const handleLoadProductionScene = async () => {
    setIsDetecting(true);
    setErrorMsg(null);
    try {
      // 1. Fetch Timeline Observations to get the real bounding box
      const timelineRes = await fetchTimeline(-180, -90, 180, 90);
      
      // Find the observation containing Asset 1 or Asset 2
      let observationBbox: number[] | null = null;
      for (const obs of timelineRes.observations) {
        if (obs.assets.some(a => a.scene_asset_id === 1 || a.id === 1 || a.scene_asset_id === 2 || a.id === 2)) {
            observationBbox = obs.bbox;
            break;
        }
      }

      if (!observationBbox) {
          throw new Error("Timeline metadata unavailable: Could not find Observation containing Asset 1 or Asset 2.");
      }

      if (observationBbox.length !== 4) {
          throw new Error(`Invalid bbox: expected 4 coordinates, got ${observationBbox.length}`);
      }

      // The timeline observation returns the full Sentinel-1 scene bbox (e.g. 250x250km),
      // but the production SAR change detection runs on a specific 0.1x0.1 deg AOI slice.
      // We must use the AOI bounds so the SAR images drape correctly over the DEM.
      const [west, south, east, north] = [72.8, 18.9, 72.9, 19.0];
      if (west >= east || south >= north) {
          throw new Error(`Invalid bbox: [${west}, ${south}, ${east}, ${north}] is not well-formed (west < east, south < north).`);
      }

      // 2. Fetch the change detection base64 images using the known asset IDs
      const changeRes = await fetchChangeDetection(1, 2);

      if (!changeRes.t1_false_color_base64 || !changeRes.t2_false_color_base64) {
          throw new Error("Invalid base64 image: API did not return false-color SAR images.");
      }

      setBbox([west, south, east, north]);
      setT1Image(changeRes.t1_false_color_base64);
      setT2Image(changeRes.t2_false_color_base64);
      
    } catch (err: any) {
      setErrorMsg(err.message || "An unknown error occurred while loading the production scene.");
      console.error(err);
    } finally {
      setIsDetecting(false);
    }
  };

  const currentSarImageUrl = activeLayer === 'T1' ? t1Image : t2Image;

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100vh', margin: 0, fontFamily: 'sans-serif' }}>
      <header style={{ padding: '1rem', backgroundColor: '#1a1a1a', color: 'white', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <h1 style={{ margin: 0, fontSize: '1.5rem' }}>GeoPulse</h1>
        <button 
          onClick={handleLoadProductionScene}
          disabled={isDetecting}
          style={{
            padding: '8px 16px',
            backgroundColor: '#007bff',
            color: 'white',
            border: 'none',
            borderRadius: '4px',
            cursor: isDetecting ? 'not-allowed' : 'pointer',
            fontSize: '0.9rem',
            fontWeight: 'bold'
          }}
        >
          {isDetecting ? 'Loading Timeline...' : 'Load Production Scene'}
        </button>
      </header>

      <main style={{ flex: 1, position: 'relative', backgroundColor: '#333' }}>
        {ENABLE_3D_CHANGE_VIEW ? (
          <>
            <CesiumViewerComponent 
              bbox={bbox} 
              sarImageUrl={currentSarImageUrl} 
              isSarVisible={isSarVisible} 
            />
            
            <div style={{
              position: 'absolute',
              bottom: '20px',
              left: '20px',
              backgroundColor: 'rgba(0, 0, 0, 0.7)',
              color: 'white',
              padding: '15px',
              borderRadius: '8px',
              zIndex: 1,
              pointerEvents: 'auto',
              minWidth: '250px'
            }}>
              <h2 style={{ margin: '0 0 10px 0', fontSize: '1rem' }}>3D Terrain Visualization</h2>
              
              {errorMsg && (
                <div style={{ backgroundColor: 'rgba(255, 0, 0, 0.2)', color: '#ffaaaa', padding: '8px', borderRadius: '4px', marginBottom: '10px', fontSize: '0.85rem' }}>
                  Error: {errorMsg}
                </div>
              )}

              {bbox ? (
                <div style={{ fontSize: '0.85rem', marginBottom: '15px' }}>
                  <div style={{ marginBottom: '4px' }}>
                    <strong>AOI:</strong> {bbox[0].toFixed(2)}, {bbox[1].toFixed(2)} &rarr; {bbox[2].toFixed(2)}, {bbox[3].toFixed(2)}
                  </div>
                  <div>
                    <strong>Scene:</strong> Asset 1 (2024-01-13) &rarr; Asset 2 (2024-06-17)
                  </div>
                </div>
              ) : (
                <div style={{ fontSize: '0.85rem', marginBottom: '15px', color: '#aaaaaa' }}>
                  No scene loaded. Click "Load Production Scene" to begin.
                </div>
              )}
              
              <div style={{ display: 'flex', alignItems: 'center', marginBottom: '10px', fontSize: '0.9rem' }}>
                <label style={{ display: 'flex', alignItems: 'center', cursor: 'pointer', marginRight: '20px' }}>
                  <input 
                    type="checkbox" 
                    checked={isSarVisible} 
                    onChange={(e) => setIsSarVisible(e.target.checked)} 
                    style={{ marginRight: '8px' }}
                    disabled={!bbox}
                  />
                  SAR Overlay: {isSarVisible ? 'ON' : 'OFF'}
                </label>
              </div>

              <div style={{ display: 'flex', alignItems: 'center', fontSize: '0.9rem' }}>
                <span style={{ marginRight: '10px' }}>Layer:</span>
                <label style={{ marginRight: '10px', cursor: 'pointer' }}>
                  <input 
                    type="radio" 
                    name="layer" 
                    value="T1" 
                    checked={activeLayer === 'T1'} 
                    onChange={() => setActiveLayer('T1')} 
                    disabled={!bbox}
                  /> T1
                </label>
                <label style={{ cursor: 'pointer' }}>
                  <input 
                    type="radio" 
                    name="layer" 
                    value="T2" 
                    checked={activeLayer === 'T2'} 
                    onChange={() => setActiveLayer('T2')}
                    disabled={!bbox}
                  /> T2
                </label>
              </div>
            </div>
          </>
        ) : (
          <div style={{ width: '100%', height: '100%', display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center' }}>
            {errorMsg && (
              <div style={{ backgroundColor: 'rgba(255, 0, 0, 0.2)', color: '#ffaaaa', padding: '8px', borderRadius: '4px', marginBottom: '10px', fontSize: '0.85rem' }}>
                Error: {errorMsg}
              </div>
            )}
            
            {!currentSarImageUrl ? (
              <div style={{ color: '#aaaaaa' }}>2D View Active. Load Production Scene to view imagery.</div>
            ) : (
              <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', height: '100%', width: '100%', padding: '20px', boxSizing: 'border-box' }}>
                <img 
                  src={currentSarImageUrl} 
                  alt="SAR 2D Layer" 
                  style={{ maxWidth: '100%', maxHeight: '80vh', objectFit: 'contain', border: '2px solid #555' }} 
                />
                
                <div style={{ marginTop: '20px', display: 'flex', gap: '20px', color: 'white', backgroundColor: '#1a1a1a', padding: '10px 20px', borderRadius: '8px' }}>
                  <label style={{ cursor: 'pointer' }}>
                    <input 
                      type="radio" 
                      name="layer2d" 
                      value="T1" 
                      checked={activeLayer === 'T1'} 
                      onChange={() => setActiveLayer('T1')} 
                    /> T1
                  </label>
                  <label style={{ cursor: 'pointer' }}>
                    <input 
                      type="radio" 
                      name="layer2d" 
                      value="T2" 
                      checked={activeLayer === 'T2'} 
                      onChange={() => setActiveLayer('T2')}
                    /> T2
                  </label>
                </div>
              </div>
            )}
          </div>
        )}
      </main>
    </div>
  );
};

export default App;
