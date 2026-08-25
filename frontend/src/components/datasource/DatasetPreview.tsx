import { CheckCircle2 } from 'lucide-react';
import { Card, DataTable, Metric } from '../common';
import { formatInteger } from '../../utils/formatters';
import type { Dataset } from '../../types/dataset';

export function DatasetPreview({ dataset, onContinue }: { dataset: Dataset; onContinue: () => void }) {
  return (
    <>
      <div className="loaded-banner">
        <CheckCircle2 size={20} />
        <span><b>{dataset.name}</b> loaded from {dataset.source}</span>
        <button className="primary" onClick={onContinue}>Explore this dataset</button>
      </div>
      <div className="metrics">
        <Metric label="ROWS" value={formatInteger(dataset.rows)} />
        <Metric label="COLUMNS" value={dataset.column_names.length} />
        <Metric label="SOURCE" value={dataset.source} />
        <Metric label="PREVIEW" value={`${dataset.preview.length} rows`} />
      </div>
      <Card title="Data preview" sub="First rows exactly as loaded">
        <DataTable rows={dataset.preview} limit={20} />
      </Card>
    </>
  );
}
