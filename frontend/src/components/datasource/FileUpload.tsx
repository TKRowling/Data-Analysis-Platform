import { useState } from 'react';
import { Upload } from 'lucide-react';

export function FileUpload({ onSelect, busy }: { onSelect: (file: File) => void; busy: boolean }) {
  const [dragging, setDragging] = useState(false);

  return (
    <label
      className={`upload ${dragging ? 'drag' : ''}`}
      onDragOver={(event) => { event.preventDefault(); setDragging(true); }}
      onDragLeave={() => setDragging(false)}
      onDrop={(event) => {
        event.preventDefault();
        setDragging(false);
        const file = event.dataTransfer.files[0];
        if (file) onSelect(file);
      }}
    >
      <input type="file" accept=".csv,.xlsx,.xls" disabled={busy}
             onChange={(event) => event.target.files?.[0] && onSelect(event.target.files[0])} />
      <span className="upload-icon"><Upload /></span>
      <h2>{busy ? 'Reading dataset…' : 'Drop your dataset here'}</h2>
      <p>or click to browse from your computer</p>
      <span className="formats">CSV · XLSX · XLS &nbsp; up to 100 MB</span>
    </label>
  );
}
