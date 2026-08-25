import { useState } from 'react';
import { CloudUpload } from 'lucide-react';

export function FileUpload({ onSelect, busy }: { onSelect: (file: File) => void; busy: boolean }) {
  const [dragging, setDragging] = useState(false);
  return <label className={`upload ${dragging ? 'drag' : ''}`}
    onDragOver={event => { event.preventDefault(); setDragging(true); }} onDragLeave={() => setDragging(false)}
    onDrop={event => { event.preventDefault(); setDragging(false); const file=event.dataTransfer.files[0]; if(file) onSelect(file); }}>
    <input type="file" accept=".csv,.xlsx,.xls" disabled={busy} onChange={event => event.target.files?.[0] && onSelect(event.target.files[0])} />
    <span className="upload-icon"><CloudUpload /></span>
    <span className="upload-copy"><b>{busy ? 'Reading dataset…' : 'Drag and drop file here'}</b><small>Limit 100MB per file · CSV, XLSX, XLS</small></span>
    <span className="browse-button">Browse files</span>
  </label>;
}
