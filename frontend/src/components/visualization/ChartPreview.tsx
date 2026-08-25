import Plot from 'react-plotly.js';
import { BarChart3 } from 'lucide-react';
import { Card, Loading } from '../common';
import type { PlotlyFigure } from '../../types/chart';

export function ChartPreview({ figure, loading }: { figure: PlotlyFigure | null; loading: boolean }) {
  return (
    <Card title="Preview" sub={figure ? 'Interactive — hover, zoom, and export from the toolbar' : undefined}>
      {loading && <Loading label="Building chart…" />}
      {!loading && figure && (
        <Plot
          data={figure.data as never[]}
          layout={{ ...figure.layout, autosize: true, height: 520 }}
          config={{ responsive: true, displaylogo: false }}
          useResizeHandler
          style={{ width: '100%' }}
        />
      )}
      {!loading && !figure && (
        <div className="chart-empty">
          <BarChart3 />
          <p>Choose your fields and generate a chart</p>
        </div>
      )}
    </Card>
  );
}
