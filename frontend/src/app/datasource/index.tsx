import { useState } from 'react';
import { Database, FileSpreadsheet, Folder } from 'lucide-react';
import { DatabaseForm } from '../../components/datasource/DatabaseForm';
import { DatasetPreview } from '../../components/datasource/DatasetPreview';
import { FileUpload } from '../../components/datasource/FileUpload';
import { ErrorBanner } from '../../components/common';
import { useDataset } from '../../hooks/useDataset';
import type { DatabaseConfig } from '../../types/dataset';

export function DataSourcePage({ onLoaded }: { onLoaded: () => void }) {
  const { dataset, busy, error, clearError, load, connect } = useDataset();
  const [sourceTab, setSourceTab] = useState<'file' | 'database'>('file');
  const handleConnect = async (config: DatabaseConfig) => {
    const result = await connect(config);
    if (result) setSourceTab('file');
  };
  return <>
    <ErrorBanner message={error} onDismiss={clearError} />
    <div className="source-heading"><Folder /><h1>Data Sources</h1></div>
    <div className="source-tabs" role="tablist">
      <button className={sourceTab === 'file' ? 'active' : ''} onClick={() => setSourceTab('file')}><FileSpreadsheet />File Upload</button>
      <button className={sourceTab === 'database' ? 'active' : ''} onClick={() => setSourceTab('database')}><Database />Database</button>
    </div>
    <section className="source-panel">
      <h2>{sourceTab === 'file' ? 'Upload Data Files' : 'Connect to Database'}</h2>
      {sourceTab === 'file' ? <><p className="input-label">Choose a file <span title="CSV and Excel files are supported">?</span></p><FileUpload onSelect={load} busy={busy} /></> : <DatabaseForm onConnect={handleConnect} busy={busy} />}
    </section>
    {dataset && <DatasetPreview dataset={dataset} onContinue={onLoaded} />}
  </>;
}
