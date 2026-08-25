import { Card, Field } from '../common';
import type { Aggregation, ChartRequest, ChartType } from '../../types/chart';
import type { ColumnProfile } from '../../types/dataset';

const CHART_TYPES: { value: ChartType; label: string }[] = [
  { value: 'bar', label: 'Bar chart' },
  { value: 'line', label: 'Line chart' },
  { value: 'scatter', label: 'Scatter plot' },
  { value: 'histogram', label: 'Histogram' },
  { value: 'box', label: 'Box plot' },
  { value: 'pie', label: 'Pie chart' },
  { value: 'heatmap', label: 'Correlation heatmap' },
];

const AGGREGATIONS: Aggregation[] = ['none', 'sum', 'mean', 'count', 'min', 'max'];

/** Which axes each chart type actually uses, so the form only offers what applies. */
const USES = {
  bar: { x: true, y: true, color: true },
  line: { x: true, y: true, color: true },
  scatter: { x: true, y: true, color: true },
  histogram: { x: true, y: false, color: true },
  box: { x: true, y: true, color: true },
  pie: { x: true, y: true, color: false },
  heatmap: { x: false, y: false, color: false },
} as const;

export function ChartControls({ request, columns, onChange, onGenerate, busy }: {
  request: ChartRequest;
  columns: ColumnProfile[];
  onChange: (next: ChartRequest) => void;
  onGenerate: () => void;
  busy: boolean;
}) {
  const uses = USES[request.chart_type];
  const names = columns.map((c) => c.name);
  const numeric = columns.filter((c) => c.kind === 'numeric').map((c) => c.name);
  const set = <K extends keyof ChartRequest>(key: K, value: ChartRequest[K]) =>
    onChange({ ...request, [key]: value });

  const yLabel = request.chart_type === 'pie' ? 'Values' : 'Y axis';
  const xLabel = request.chart_type === 'pie' ? 'Labels' : 'X axis';

  return (
    <Card title="Chart controls" sub="Pick a shape, then the fields to plot">
      <Field label="Chart type">
        <select value={request.chart_type}
                onChange={(event) => set('chart_type', event.target.value as ChartType)}>
          {CHART_TYPES.map((type) => <option key={type.value} value={type.value}>{type.label}</option>)}
        </select>
      </Field>

      {uses.x && (
        <Field label={xLabel}>
          <select value={request.x ?? ''} onChange={(event) => set('x', event.target.value || null)}>
            <option value="">Select field</option>
            {names.map((name) => <option key={name} value={name}>{name}</option>)}
          </select>
        </Field>
      )}

      {uses.y && (
        <Field label={yLabel}
               hint={request.aggregation === 'count' ? 'Not needed when aggregating by count.' : undefined}>
          <select value={request.y ?? ''} onChange={(event) => set('y', event.target.value || null)}
                  disabled={request.aggregation === 'count'}>
            <option value="">Select field</option>
            {(request.aggregation === 'none' ? names : numeric).map((name) => (
              <option key={name} value={name}>{name}</option>
            ))}
          </select>
        </Field>
      )}

      {request.chart_type !== 'heatmap' && (
        <Field label="Aggregation">
          <select value={request.aggregation}
                  onChange={(event) => set('aggregation', event.target.value as Aggregation)}>
            {AGGREGATIONS.map((option) => <option key={option} value={option}>{option}</option>)}
          </select>
        </Field>
      )}

      {uses.color && (
        <Field label="Group by colour" hint="Optional — splits the series by a category.">
          <select value={request.color ?? ''} onChange={(event) => set('color', event.target.value || null)}>
            <option value="">None</option>
            {names.map((name) => <option key={name} value={name}>{name}</option>)}
          </select>
        </Field>
      )}

      <Field label="Title">
        <input value={request.title ?? ''} placeholder="Optional chart title"
               onChange={(event) => set('title', event.target.value || null)} />
      </Field>

      <button className="primary wide" onClick={onGenerate} disabled={busy}>
        {busy ? 'Building…' : 'Generate chart'}
      </button>
    </Card>
  );
}
