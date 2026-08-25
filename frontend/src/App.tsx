import { useState } from 'react';
import { MainLayout } from './components/layout/MainLayout';
import type { ModuleId } from './components/layout/Sidebar';
import { AIAnalysisPage } from './app/ai-analysis';
import { DataSourcePage } from './app/datasource';
import { ExploratoryAnalysisPage } from './app/exploratory-analysis';
import { ReportsPage } from './app/reports';
import { VisualizationPage } from './app/visualization';
import { useAIAnalysis } from './hooks/useAIAnalysis';
import { useDatasetStore } from './store/datasetStore';

export default function App() {
  const [module, setModule] = useState<ModuleId>('source');
  const { dataset, revision } = useDatasetStore();

  // Lifted so saved answers survive tab switches and can feed the report builder.
  const ai = useAIAnalysis(dataset?.id);

  return (
    <MainLayout module={module} onSelect={setModule} dataset={dataset} online>
      {module === 'source' && <DataSourcePage onLoaded={() => setModule('eda')} />}
      {module === 'eda' && <ExploratoryAnalysisPage dataset={dataset} revision={revision} />}
      {module === 'ai' && (
        <AIAnalysisPage dataset={dataset} history={ai.history}
                        busy={ai.busy} error={ai.error} onAsk={ai.ask} />
      )}
      {module === 'visualize' && <VisualizationPage dataset={dataset} revision={revision} />}
      {module === 'reports' && <ReportsPage dataset={dataset} insights={ai.history} />}
    </MainLayout>
  );
}
