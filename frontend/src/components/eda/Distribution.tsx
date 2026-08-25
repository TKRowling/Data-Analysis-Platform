import { useMemo, useState } from 'react';
import Plot from 'react-plotly.js';
import { Card, Field, Loading, Metric } from '../common';
import { useEDA } from '../../hooks/useEDA';
import { getDistribution } from '../../services/edaApi';
import { formatNumber } from '../../utils/formatters';
import type { CategoricalDistribution, NumericDistribution } from '../../types/eda';
import type { ColumnProfile, Dataset } from '../../types/dataset';

const PLOT_CONFIG = { displayModeBar: false, responsive: true };
const PIE_COLORS = ['#3859d9', '#5b7ce8', '#e85d75', '#f0a04b', '#33b3a6', '#8a63d2',
                    '#e0729a', '#4aa3df', '#7ac36a', '#c9ab5e'];

function NumericView({ data }: { data: NumericDistribution }) {
  const edges = data.histogram.edges;
  return (
    <>
      <div className="metrics">
        <Metric label="MEAN" value={formatNumber(data.statistics.mean)} />
        <Metric label="MEDIAN" value={formatNumber(data.statistics.median)} />
        <Metric label="STD DEV" value={formatNumber(data.statistics.std)} />
        <Metric label="SKEWNESS" value={formatNumber(data.statistics.skewness, 3)}
                note={`${data.outliers.count} IQR outliers`} />
      </div>
      <div className="two distribution-plots">
        <Card title="Histogram" sub={`${data.statistics.count.toLocaleString()} non-null values`}>
          <Plot
            data={[{
              type: 'bar', x: edges.slice(0, -1), y: data.histogram.counts,
              marker: { color: '#3859d9' },
              hovertemplate: 'value %{x}<br>count %{y}<extra></extra>',
            } as never]}
            layout={{ height: 340, autosize: true, bargap: 0.02, margin: { l: 55, r: 20, t: 16, b: 44 } }}
            config={PLOT_CONFIG} useResizeHandler className="distribution-plot" style={{ width: '100%', height: '340px' }}
          />
        </Card>
        <Card title="Box plot" sub="Quartiles, whiskers, and spread">
          <Plot
            data={[{
              type: 'box', name: data.column, orientation: 'h',
              q1: [data.box.q1], median: [data.box.median], q3: [data.box.q3],
              lowerfence: [data.box.min], upperfence: [data.box.max],
              marker: { color: '#3859d9' }, boxpoints: false,
            } as never]}
            layout={{ height: 340, autosize: true, showlegend: false, margin: { l: 55, r: 20, t: 16, b: 44 } }}
            config={PLOT_CONFIG} useResizeHandler className="distribution-plot" style={{ width: '100%', height: '340px' }}
          />
          <div className="quartiles">
            {(['min', 'q1', 'median', 'q3', 'max'] as const).map((key) => (
              <div key={key}><small>{key.toUpperCase()}</small><b>{formatNumber(data.box[key])}</b></div>
            ))}
          </div>
        </Card>
      </div>
      <p className="insight">{data.interpretation}</p>
    </>
  );
}

function CategoricalView({ data }: { data: CategoricalDistribution }) {
  const top = data.values.slice(0, 12);
  const remainder = data.values.slice(12).reduce((sum, entry) => sum + entry.count, 0);
  const pieLabels = remainder > 0 ? [...top.map((v) => v.label), 'Other'] : top.map((v) => v.label);
  const pieValues = remainder > 0 ? [...top.map((v) => v.count), remainder] : top.map((v) => v.count);

  return (
    <>
      <div className="metrics">
        <Metric label="DISTINCT VALUES" value={data.unique} />
        <Metric label="NON-NULL ROWS" value={data.total.toLocaleString()} />
        <Metric label="MOST FREQUENT" value={data.values[0]?.label ?? '—'}
                note={data.values[0] ? `${(data.values[0].proportion * 100).toFixed(1)}% of rows` : undefined} />
      </div>
      <div className="two distribution-plots">
        <Card title="Category counts" sub="Frequency of each value">
          <Plot
            data={[{
              type: 'bar', x: top.map((v) => v.label), y: top.map((v) => v.count),
              marker: { color: '#3859d9' },
              hovertemplate: '%{x}<br>count %{y}<extra></extra>',
            } as never]}
            layout={{ height: 360, autosize: true, margin: { l: 55, r: 20, t: 16, b: 96 },
                      xaxis: { tickangle: -35 } }}
            config={PLOT_CONFIG} useResizeHandler className="distribution-plot" style={{ width: '100%', height: '360px' }}
          />
        </Card>
        <Card title="Proportion" sub="Share of rows per category">
          <Plot
            data={[{
              type: 'pie', labels: pieLabels, values: pieValues, hole: 0.45,
              marker: { colors: PIE_COLORS },
              textinfo: 'percent', hovertemplate: '%{label}<br>%{value} rows (%{percent})<extra></extra>',
            } as never]}
            layout={{ height: 360, autosize: true, margin: { l: 20, r: 20, t: 16, b: 20 },
                      legend: { orientation: 'v', x: 1, y: 0.5 } }}
            config={PLOT_CONFIG} useResizeHandler className="distribution-plot" style={{ width: '100%', height: '360px' }}
          />
        </Card>
      </div>
      <p className="insight">{data.interpretation}</p>
      {data.values.length > 12 && (
        <p className="muted-text">Showing the 12 most frequent of {data.unique} distinct values.</p>
      )}
    </>
  );
}

export function Distribution({ dataset, columns, revision }: {
  dataset: Dataset;
  columns: ColumnProfile[];
  revision: number;
}) {
  const options = useMemo(
    () => (columns.length ? columns.map((c) => c.name) : dataset.column_names),
    [columns, dataset.column_names],
  );
  const [column, setColumn] = useState(options[0] ?? '');
  const { data, loading, error } = useEDA(
    dataset.id && column ? dataset.id : undefined,
    (id) => getDistribution(id, column),
    [column, revision],
  );

  const kind = columns.find((c) => c.name === column)?.kind;

  return (
    <>
      <Card title="Variable distribution"
            sub="Choose any column to inspect its shape. Numeric columns show a histogram and box plot; categorical columns show counts and proportions.">
        <div className="controls">
          <Field label="Column">
            <select value={column} onChange={(event) => setColumn(event.target.value)}>
              {options.map((name) => <option key={name} value={name}>{name}</option>)}
            </select>
          </Field>
          {kind && <span className={`kind-badge ${kind}`}>{kind}</span>}
        </div>
      </Card>

      {loading && <Loading label="Analyzing distribution…" />}
      {error && <p className="error">{error}</p>}
      {!loading && data && (data.kind === 'numeric'
        ? <NumericView data={data} />
        : <CategoricalView data={data} />)}
    </>
  );
}
