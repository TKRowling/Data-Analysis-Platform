import { Card, DataTable, Metric } from '../common';
import { formatBytes, formatInteger } from '../../utils/formatters';
import type { Overview } from '../../types/dataset';

export function DatasetOverview({ data }: { data: Overview }) {
  return (
    <>
      <div className="metrics">
        <Metric label="ROWS" value={formatInteger(data.rows)} />
        <Metric label="COLUMNS" value={data.columns_count} />
        <Metric label="MEMORY" value={formatBytes(data.memory_bytes)} />
        <Metric label="NUMERIC" value={data.kinds.numeric} note={`${data.kinds.categorical} categorical · ${data.kinds.datetime} datetime`} />
      </div>
      <Card title="Column profile" sub="Type, completeness, and cardinality for every field">
        <DataTable rows={data.columns as unknown as Record<string, unknown>[]} limit={200} />
      </Card>
      <Card title="Data sample" sub="First rows as loaded">
        <DataTable rows={data.sample} limit={8} />
      </Card>
    </>
  );
}
