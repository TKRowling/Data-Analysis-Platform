import Plot from 'react-plotly.js';
import { BarChart3 } from 'lucide-react';
import { Card, Loading } from '../common';
import type { PlotlyFigure } from '../../types/chart';

export function ChartPreview({ figure, loading }: { figure: PlotlyFigure | null; loading: boolean }) {
  const rawTitle=figure?.layout?.title; const title=typeof rawTitle==='object'&&rawTitle&&'text' in rawTitle?String((rawTitle as {text:unknown}).text):typeof rawTitle==='string'?rawTitle:'Visualization preview';
  return <Card title={title} sub={figure?'Interactive — hover, zoom, pan, and export from the toolbar':undefined}>
    {loading&&<Loading label="Building chart…"/>}
    {!loading&&figure&&<Plot data={figure.data as never[]} layout={{...figure.layout,autosize:true,height:520}} config={{responsive:true,displaylogo:false}} useResizeHandler className="visualization-preview-plot" style={{width:'100%',height:'520px'}}/>}
    {!loading&&!figure&&<div className="chart-empty"><BarChart3/><p>Select columns and generate a visualization</p></div>}
  </Card>;
}
