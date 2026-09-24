import { useState } from 'react';
import Telemetry from './components/Telemetry';
import GeoPulseStudio from './components/studio/GeoPulseStudio';
import Intelligence from './components/Intelligence';

export type ViewState = 'OVERVIEW' | 'STUDIO' | 'ANALYTICS' | 'EXPLORER' | 'INTELLIGENCE' | 'TELEMETRY';

export interface AnalysisContextData {
  t1Url: string;
  t2Url: string;
}

function App() {
  const [activeView, setActiveView] = useState<ViewState>('TELEMETRY');
  const [analysisContext, setAnalysisContext] = useState<AnalysisContextData | null>(null);

  const handleOpenAnalysis = (t1Url: string, t2Url: string) => {
    setAnalysisContext({ t1Url, t2Url });
    setActiveView('STUDIO');
  };

  return (
    <>
      {activeView === 'TELEMETRY' && <Telemetry onViewChange={setActiveView} />}
      {activeView === 'STUDIO' && <GeoPulseStudio onViewChange={setActiveView} analysisContext={analysisContext} />}
      {activeView === 'INTELLIGENCE' && <Intelligence onViewChange={setActiveView} onOpenAnalysis={handleOpenAnalysis} />}
    </>
  )
}

export default App;
