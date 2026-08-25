import Plot from 'react-plotly.js';
import { Card, DataTable, Metric } from '../common';
import { formatNumber } from '../../utils/formatters';
import type { Statistics as StatisticsData } from '../../types/eda';

const PLOT_CONFIG = { displayModeBar: false, responsive: true };

export function Statistics({ data }: { data: StatisticsData }) {
  return (
    <>
      <div className="metrics">
        <Metric label="NUMERIC FIELDS" value={data.numeric.length} />
        <Metric label="CATEGORICAL FIELDS" value={data.categorical.length} />
        <Metric label="TOTAL PROFILED" value={data.numeric.length + data.categorical.length} />
      </div>

      <Card title="Numeric column statistics" sub="Central tendency, spread, and shape">
        <DataTable rows={data.numeric as unknown as Record<string, unknown>[]} limit={100} />
      </Card>

      <Card title="Distribution overview" sub="Histogram of every numeric column">
        {data.histograms.length ? (
          <div className="mini-charts">
            {data.histograms.map((histogram) => (
              <div className="mini-chart" key={histogram.column}>
                <h4>{histogram.column}</h4>
                <Plot
                  data={[{
                    type: 'bar',
                    x: histogram.edges.slice(0, -1),
                    y: histogram.counts,
                    marker: { color: '#3859d9' },
                    hovertemplate: 'value %{x}<br>count %{y}<extra></extra>',
                  } as never]}
                  layout={{
                    height: 190, autosize: true, bargap: 0.02, showlegend: false,
                    margin: { l: 42, r: 12, t: 8, b: 30 },
                    xaxis: { fixedrange: true }, yaxis: { fixedrange: true },
                  }}
                  config={PLOT_CONFIG}
                  useResizeHandler
                  style={{ width: '100%', height: '190px' }}
                />
              </div>
            ))}
          </div>
        ) : <p className="muted-text">No numeric columns to plot.</p>}
      </Card>

      <Card title="Categorical column statistics" sub="Distinct values and the most frequent categories">
        {data.categorical.length ? (
          <div className="table-wrap">
            <table>
              <thead>
                <tr><th>Column</th><th>Distinct</th><th>Missing</th><th>Top values</th></tr>
              </thead>
              <tbody>
                {data.categorical.map((column) => (
                  <tr key={column.column}>
                    <td>{column.column}</td>
                    <td>{formatNumber(column.unique)}</td>
                    <td>{formatNumber(column.missing)}</td>
                    <td>
                      <div className="chips">
                        {column.top_values.slice(0, 5).map((entry) => (
                          <span className="chip" key={entry.value}>
                            {entry.value}
                            <em>{(entry.proportion * 100).toFixed(1)}%</em>
                          </span>
                        ))}
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : <p className="muted-text">No categorical columns in this dataset.</p>}
      </Card>
    </>
  );
}
