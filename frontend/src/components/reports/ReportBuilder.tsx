import {useState} from 'react';
import {Download,FileText} from 'lucide-react';
import {ErrorBanner,Field} from '../common';
import {ReportSections,SECTIONS} from './ReportSections';
import {downloadReport} from '../../services/reportApi';
import type {ReportFormat} from '../../types/chart';
import type {Dataset} from '../../types/dataset';
import type {AIExchange} from '../../types/analysis';

const FORMATS:{value:ReportFormat;label:string;note:string}[]=[{value:'html',label:'HTML',note:'Interactive web report'},{value:'pdf',label:'PDF',note:'Print-ready document'},{value:'markdown',label:'Markdown',note:'Portable plain text'}];

export function ReportBuilder({dataset,insights}:{dataset:Dataset;insights:AIExchange[]}){
  const [title,setTitle]=useState(`${dataset.name} — Analysis Report`);const [selected,setSelected]=useState(SECTIONS.map(x=>x.key));const [format,setFormat]=useState<ReportFormat>('html');const [busy,setBusy]=useState(false);const [error,setError]=useState('');
  const toggle=(key:string)=>setSelected(current=>current.includes(key)?current.filter(x=>x!==key):[...current,key]);
  const generate=async()=>{setBusy(true);setError('');try{await downloadReport(dataset.id,{title:title.trim()||'Dataset Analysis Report',sections:selected,format,insights:insights.map(x=>({question:x.question,answer:x.answer}))})}catch(cause){setError((cause as Error).message)}finally{setBusy(false)}};
  return <div className="automated-report"><ErrorBanner message={error} onDismiss={()=>setError('')}/><div className="report-context"><span><FileText/></span><div><b>{dataset.name}</b><small>{dataset.rows.toLocaleString()} rows · {dataset.column_names.length} columns</small></div></div><Field label="Report title"><input value={title} onChange={e=>setTitle(e.target.value)}/></Field><div className="report-control"><label>Select report sections</label><ReportSections selected={selected} onToggle={toggle}/></div><fieldset className="report-formats"><legend>Report format</legend>{FORMATS.map(item=><label key={item.value} className={format===item.value?'selected':''}><input type="radio" name="report-format" value={item.value} checked={format===item.value} onChange={()=>setFormat(item.value)}/><span><i/><b>{item.label}</b><small>{item.note}</small></span></label>)}</fieldset>{selected.includes('insights')&&!insights.length&&<p className="report-note">Key Insights is selected, but no AI result is currently available.</p>}<button className="primary generate-report" onClick={generate} disabled={busy||!selected.length}><Download size={17}/>{busy?'Generating report…':'Generate Report'}</button></div>;
}
