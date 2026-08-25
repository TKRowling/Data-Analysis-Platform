import { Table2 } from 'lucide-react';
import type { Dataset } from '../../types/dataset';

export function Header({ title, dataset }: { title: string; dataset: Dataset | null }) {
  return (
    <header>
      <div>
        <small>WORKSPACE</small>
        <h2>{title}</h2>
      </div>
      {dataset ? (
        <div className="dataset-pill">
          <Table2 size={17} />
          <span>
            <b title={dataset.name}>{dataset.name}</b>
            <small>{dataset.rows.toLocaleString()} rows · {dataset.column_names.length} cols</small>
          </span>
        </div>
      ) : (
        <div className="dataset-pill muted">No dataset loaded</div>
      )}
    </header>
  );
}
