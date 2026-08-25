import { Check, Plus, X } from 'lucide-react';

export const SECTIONS=[
  {key:'executive_summary',label:'Executive Summary',help:'Headline findings'},
  {key:'overview',label:'Data Overview',help:'Dataset size and columns'},
  {key:'quality',label:'Data Quality Assessment',help:'Missing values, duplicates, and outliers'},
  {key:'statistics',label:'Statistical Summary',help:'Numeric and categorical statistics'},
  {key:'correlation',label:'Correlation Analysis',help:'Relationships between numeric variables'},
  {key:'distribution',label:'Distribution Analysis',help:'Shape and skew of numeric columns'},
  {key:'insights',label:'Key Insights',help:'Latest verified AI analysis'},
];

export function ReportSections({selected,onToggle}:{selected:string[];onToggle:(key:string)=>void}){
  return <div className="report-section-picker">
    <div className="report-chips">{selected.map(key=>{const section=SECTIONS.find(x=>x.key===key);return section&&<button type="button" key={key} onClick={()=>onToggle(key)}>{section.label}<X size={13}/></button>})}{!selected.length&&<span>Select report sections below</span>}</div>
    <div className="report-section-options">{SECTIONS.map(section=><button type="button" key={section.key} className={selected.includes(section.key)?'selected':''} onClick={()=>onToggle(section.key)}><i>{selected.includes(section.key)?<Check size={13}/>:<Plus size={13}/>}</i><span><b>{section.label}</b><small>{section.help}</small></span></button>)}</div>
  </div>;
}
