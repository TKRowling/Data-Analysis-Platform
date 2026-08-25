import Plot from 'react-plotly.js';
import { Card, DataTable } from '../common';
import type { Correlation as CorrelationData } from '../../types/eda';

const SCALE: [number, string][] = [[0, '#25388f'], [0.5, '#f6f8fc'], [1, '#e85d75']];

export function Correlation({ data, method, onMethodChange }: {
  data: CorrelationData;
  method: string;
  onMethodChange: (method: string) => void;
}) {
  if (!data.columns.length) {
    return <Card title="Correlation analysis"><p className="muted-text">This dataset has no numeric columns to correlate.</p></Card>;
  }

  const size = Math.max(420, Math.min(data.columns.length * 46 + 160, 760));

  return (
    <div className="two">
      <Card
        title="Correlation matrix"
        sub={`${data.columns.length} numeric columns · ${method} coefficient`}
        action={
          <select value={method} onChange={(event) => onMethodChange(event.target.value)} aria-label="Correlation method">
            <option value="pearson">Pearson</option>
            <option value="spearman">Spearman</option>
            <option value="kendall">Kendall</option>
          </select>
        }
      >
        <Plot
          data={[{
            z: data.matrix, x: data.columns, y: data.columns,
            type: 'heatmap', colorscale: SCALE, zmin: -1, zmax: 1,
            hovertemplate: '%{y} ↔ %{x}<br>r = %{z:.3f}<extra></extra>',
          } as never]}
          layout={{ autosize: true, height: size, margin: { l: 110, r: 30, t: 12, b: 110 } }}
          config={{ displayModeBar: false, responsive: true }}
          useResizeHandler
          style={{ width: '100%' }}
        />
      </Card>

      <Card title="Strong correlations" sub="Absolute coefficient ≥ 0.70">
        <DataTable
          rows={data.strong as unknown as Record<string, unknown>[]}
          empty="No pair reached |r| ≥ 0.70."
        />
        {data.strong.length > 0 && (
          <p className="insight">
            Correlation measures association only. A strong coefficient does not mean one column causes the other.
          </p>
        )}
      </Card>
    </div>
  );
}
