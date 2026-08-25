import { Check, X } from 'lucide-react';
import { Card, Field } from '../common';
import type { Aggregation, ChartRequest, ChartType } from '../../types/chart';
import type { ColumnProfile } from '../../types/dataset';

const CHART_TYPES: { value: ChartType; label: string }[] = [
  { value: 'line', label: 'Line Chart' }, { value: 'bar', label: 'Bar Chart' },
  { value: 'scatter', label: 'Scatter Plot' }, { value: 'histogram', label: 'Histogram' },
  { value: 'box', label: 'Box Plot' }, { value: 'pie', label: 'Pie Chart' },
  { value: 'heatmap', label: 'Correlation Heatmap' },
];
const AGGREGATIONS: Aggregation[] = ['none', 'sum', 'mean', 'count', 'min', 'max'];

function MultiColumns({ values, options, onChange }: { values:string[];options:string[];onChange:(v:string[])=>void }) {
  const toggle=(name:string)=>onChange(values.includes(name)?values.filter(x=>x!==name):[...values,name]);
  return <div className="multi-columns">
    <div className="selected-columns">{values.length ? values.map(name=><button type="button" key={name} onClick={()=>toggle(name)}>{name}<X size={13}/></button>) : <span>All numeric columns</span>}</div>
    <div className="column-options">{options.map(name=><button type="button" key={name} className={values.includes(name)?'selected':''} onClick={()=>toggle(name)}><i>{values.includes(name)&&<Check size={12}/>}</i>{name}</button>)}</div>
  </div>;
}

export function ChartControls({ request, columns, onChange, onGenerate, busy }: {
  request: ChartRequest; columns: ColumnProfile[]; onChange:(next:ChartRequest)=>void; onGenerate:()=>void; busy:boolean;
}) {
  const names=columns.map(c=>c.name); const numeric=columns.filter(c=>c.kind==='numeric').map(c=>c.name);
  const set=<K extends keyof ChartRequest>(key:K,value:ChartRequest[K])=>onChange({...request,[key]:value});
  const isHeatmap=request.chart_type==='heatmap'; const isMultiLine=request.chart_type==='line';
  const label=CHART_TYPES.find(x=>x.value===request.chart_type)?.label;
  return <Card>
    <div className="visualization-type"><Field label="Select visualization type"><select value={request.chart_type} onChange={e=>onChange({...request,chart_type:e.target.value as ChartType,y:null,y_columns:[],columns:[],aggregation:e.target.value==='line'?'none':request.aggregation})}>{CHART_TYPES.map(x=><option key={x.value} value={x.value}>{x.label}</option>)}</select></Field></div>
    <h2 className="chart-form-title">{label}</h2>
    {isHeatmap ? <Field label="Select columns" hint="Leave empty to include all numeric columns"><MultiColumns values={request.columns||[]} options={numeric} onChange={v=>set('columns',v)}/></Field> : <>
      <div className="chart-fields">
        <Field label={request.chart_type==='pie'?'Labels':'X-axis'}><select value={request.x||''} onChange={e=>set('x',e.target.value||null)}><option value="">Select column</option>{names.map(x=><option key={x}>{x}</option>)}</select></Field>
        {isMultiLine ? <Field label="Y-axis" hint="Select one or more numeric columns"><MultiColumns values={request.y_columns||[]} options={numeric} onChange={v=>set('y_columns',v)}/></Field> : request.chart_type!=='histogram'&&<Field label={request.chart_type==='pie'?'Values':'Y-axis'}><select value={request.y||''} disabled={request.aggregation==='count'} onChange={e=>set('y',e.target.value||null)}><option value="">Select column</option>{numeric.map(x=><option key={x}>{x}</option>)}</select></Field>}
      </div>
      <div className="chart-fields secondary-fields">
        <Field label="Color by" hint="Optional"><select value={request.color||''} onChange={e=>set('color',e.target.value||null)}><option value="">None</option>{names.map(x=><option key={x}>{x}</option>)}</select></Field>
        <Field label="Aggregation"><select value={request.aggregation} onChange={e=>set('aggregation',e.target.value as Aggregation)}>{AGGREGATIONS.map(x=><option key={x}>{x}</option>)}</select></Field>
      </div>
    </>}
    <div className="chart-submit"><Field label="Chart title"><input value={request.title||''} placeholder={`${label} title (optional)`} onChange={e=>set('title',e.target.value||null)}/></Field><button className="primary" onClick={onGenerate} disabled={busy}>{busy?'Building…':'Generate visualization'}</button></div>
  </Card>;
}
