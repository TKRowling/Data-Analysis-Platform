import Plot from 'react-plotly.js';
import { Bot, CheckCircle2 } from 'lucide-react';
import { DataTable } from '../common';
import { InsightCard } from './InsightCard';
import { formatNumber, titleCase } from '../../utils/formatters';
import type { AIExchange } from '../../types/analysis';

const PLOT_CONFIG = { displayModeBar: false, responsive: true };

/** Charts the answer's own data, when the agent suggested a shape for it. */
function ResultChart({ result }: { result: AIExchange }) {
  const rows = result.data.rows as Record<string, unknown>[] | undefined;
  const chart = result.suggested_chart;
  if (!chart || !rows?.length || rows.length > 40) return null;

  const keys = Object.keys(rows[0]);
  const labelKey = (result.data.group as string) ?? keys[0];
  const valueKey = (result.data.metric as string) ?? keys.find((k) => typeof rows[0][k] === 'number');
  if (!labelKey || !valueKey || !(labelKey in rows[0]) || !(valueKey in rows[0])) return null;

  const labels = rows.map((row) => String(row[labelKey]));
  const values = rows.map((row) => Number(row[valueKey]));
  if (values.some((v) => !Number.isFinite(v))) return null;

  return (
    <Plot
      data={[{
        type: chart === 'line' ? 'scatter' : 'bar',
        mode: chart === 'line' ? 'lines+markers' : undefined,
        x: labels, y: values, marker: { color: '#3859d9' },
        hovertemplate: `%{x}<br>${valueKey} %{y}<extra></extra>`,
      } as never]}
      layout={{ height: 300, autosize: true, margin: { l: 60, r: 20, t: 12, b: 74 },
                xaxis: { tickangle: labels.length > 6 ? -30 : 0 } }}
      config={PLOT_CONFIG} useResizeHandler style={{ width: '100%' }}
    />
  );
}

function KeyFigures({ data }: { data: Record<string, unknown> }) {
  const scalars = Object.entries(data).filter(
    ([key, value]) => (typeof value === 'number' || typeof value === 'string')
      && !['rows', 'matrix', 'points', 'columns'].includes(key),
  ).slice(0, 6);
  if (!scalars.length) return null;
  return (
    <div className="figures">
      {scalars.map(([key, value]) => (
        <div key={key}>
          <small>{titleCase(key)}</small>
          <b>{typeof value === 'number' ? formatNumber(value) : String(value)}</b>
        </div>
      ))}
    </div>
  );
}

export function AnalysisResult({ result }: { result: AIExchange }) {
  const rows = result.data.rows as Record<string, unknown>[] | undefined;
  return (
    <article className="answer">
      <div className="agent">
        <span><Bot size={18} /></span>
        {result.agent.replace(/_/g, ' ')}
        <span className="intent-tag">{result.intent}</span>
        {result.verified && <em><CheckCircle2 size={14} /> computed from your data</em>}
      </div>
      <p className="asked">{result.question}</p>
      <h2>{result.answer}</h2>
      <KeyFigures data={result.data} />
      <ResultChart result={result} />
      {Array.isArray(rows) && rows.length > 0 && <DataTable rows={rows} limit={25} />}
      <InsightCard trace={result.trace} />
    </article>
  );
}
