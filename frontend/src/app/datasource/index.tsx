import { useState } from 'react';
import { ChevronRight, Database, Sparkles } from 'lucide-react';
import { DatabaseForm } from '../../components/datasource/DatabaseForm';
import { DatasetPreview } from '../../components/datasource/DatasetPreview';
import { FileUpload } from '../../components/datasource/FileUpload';
import { ErrorBanner } from '../../components/common';
import { useDataset } from '../../hooks/useDataset';
import type { DatabaseConfig } from '../../types/dataset';

export function DataSourcePage({ onLoaded }: { onLoaded: () => void }) {
  const { dataset, busy, error, clearError, load, connect } = useDataset();
  const [showDatabase, setShowDatabase] = useState(false);

  const handleConnect = async (config: DatabaseConfig) => {
    const result = await connect(config);
    if (result) setShowDatabase(false);
  };

  return (
    <>
      <ErrorBanner message={error} onDismiss={clearError} />

      <section className="hero">
        <div>
          <span className="eyebrow">NEW ANALYSIS</span>
          <h1>Turn raw data into<br /><em>clear decisions.</em></h1>
          <p>Bring in a dataset and move seamlessly from exploration to AI-assisted insight, visualization, and a polished report.</p>
        </div>
        <div className="hero-stat">
          <Sparkles />
          <b>5</b>
          <span>connected analysis modules</span>
        </div>
      </section>

      <div className="source-grid">
        <FileUpload onSelect={load} busy={busy} />
        <div className="db-card">
          <span className="tag">POSTGRESQL · MYSQL</span>
          <Database size={32} />
          <h2>Connect a database</h2>
          <p>Load data with a controlled, read-only SELECT statement.</p>
          <button onClick={() => setShowDatabase((open) => !open)}>
            {showDatabase ? 'Hide connection' : 'Configure connection'} <ChevronRight size={17} />
          </button>
        </div>
      </div>

      {showDatabase && <DatabaseForm onConnect={handleConnect} busy={busy} />}
      {dataset && <DatasetPreview dataset={dataset} onContinue={onLoaded} />}
    </>
  );
}
