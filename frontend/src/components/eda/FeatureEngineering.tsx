import { useState } from 'react';
import { Plus, Wand2 } from 'lucide-react';
import { Card, ErrorBanner, Field } from '../common';
import { createFeature, transformFeature } from '../../services/edaApi';
import { markDatasetChanged } from '../../store/datasetStore';
import type { ColumnProfile, Dataset, FeatureResult } from '../../types/dataset';

const TRANSFORMS: { value: string; label: string; help: string; kinds: string[] }[] = [
  { value: 'standardize', label: 'Standardize (z-score)', help: 'Centre on 0 with unit standard deviation.', kinds: ['numeric'] },
  { value: 'min_max', label: 'Min–max scale', help: 'Rescale to the 0–1 range.', kinds: ['numeric'] },
  { value: 'log', label: 'Log transform', help: 'Natural log. Requires all values above zero.', kinds: ['numeric'] },
  { value: 'bin', label: 'Quantile bins', help: 'Split into equal-frequency buckets.', kinds: ['numeric'] },
  { value: 'one_hot', label: 'One-hot encode', help: 'One 0/1 column per category.', kinds: ['categorical', 'boolean'] },
  { value: 'frequency', label: 'Frequency encode', help: 'Replace each category with how often it occurs.', kinds: ['categorical', 'boolean'] },
  { value: 'datetime_parts', label: 'Extract date parts', help: 'Add year, month, day, and weekday columns.', kinds: ['datetime', 'categorical'] },
];

export function FeatureEngineering({ dataset, columns, onChanged }: {
  dataset: Dataset;
  columns: ColumnProfile[];
  onChanged: () => void;
}) {
  const [name, setName] = useState('new_feature');
  const [expression, setExpression] = useState('');
  const [column, setColumn] = useState(columns[0]?.name ?? dataset.column_names[0] ?? '');
  const [transform, setTransform] = useState('standardize');
  const [bins, setBins] = useState(4);
  const [created, setCreated] = useState<FeatureResult[]>([]);
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);

  const selectedKind = columns.find((c) => c.name === column)?.kind;
  const available = TRANSFORMS.filter((t) => !selectedKind || t.kinds.includes(selectedKind));
  const active = TRANSFORMS.find((t) => t.value === transform);

  const run = async (task: () => Promise<FeatureResult>) => {
    setBusy(true);
    setError('');
    try {
      const result = await task();
      setCreated((items) => [result, ...items]);
      markDatasetChanged(result.created);
      onChanged();
    } catch (cause) {
      setError((cause as Error).message);
    } finally {
      setBusy(false);
    }
  };

  return (
    <>
      <ErrorBanner message={error} onDismiss={() => setError('')} />

      <Card title="Calculated column" sub="Build a new variable from arithmetic over existing columns: + − × ÷ ** %">
        <div className="controls">
          <Field label="Feature name">
            <input value={name} onChange={(event) => setName(event.target.value)} />
          </Field>
          <Field label="Formula" hint="Example: revenue / units">
            <input placeholder="revenue / units" value={expression}
                   onChange={(event) => setExpression(event.target.value)} />
          </Field>
          <button className="primary" disabled={busy || !expression.trim() || !name.trim()}
                  onClick={() => run(() => createFeature(dataset.id, name, expression))}>
            <Plus size={17} /> Create feature
          </button>
        </div>
        <p className="muted-text">
          Formulas are evaluated with a restricted parser that understands column names, numbers, and
          arithmetic only — no function calls or imports.
        </p>
      </Card>

      <Card title="Transform a column" sub="Apply a standard preparation step and add the result as new columns">
        <div className="controls">
          <Field label="Column">
            <select value={column} onChange={(event) => setColumn(event.target.value)}>
              {(columns.length ? columns.map((c) => c.name) : dataset.column_names).map((c) => (
                <option key={c} value={c}>{c}</option>
              ))}
            </select>
          </Field>
          <Field label="Transform">
            <select value={transform} onChange={(event) => setTransform(event.target.value)}>
              {available.map((option) => <option key={option.value} value={option.value}>{option.label}</option>)}
            </select>
          </Field>
          {transform === 'bin' && (
            <Field label="Bins">
              <input type="number" min={2} max={20} value={bins}
                     onChange={(event) => setBins(Number(event.target.value))} />
            </Field>
          )}
          <button className="primary" disabled={busy || !column}
                  onClick={() => run(() => transformFeature(dataset.id, column, transform, undefined, bins))}>
            <Wand2 size={17} /> Apply
          </button>
        </div>
        {active && <p className="muted-text">{active.help}</p>}
      </Card>

      {created.length > 0 && (
        <Card title="Columns added this session">
          <ul className="created-list">
            {created.map((feature, index) => (
              <li key={`${feature.name}-${index}`}>
                <b>{feature.created.join(', ')}</b>
                <em>{feature.expression ? `= ${feature.expression}` : `${feature.transform} of ${feature.column}`}</em>
                <span>{feature.type}</span>
              </li>
            ))}
          </ul>
        </Card>
      )}
    </>
  );
}
