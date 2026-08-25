import { FileCode, FileText, FileType } from 'lucide-react';
import type { ReportFormat } from '../../types/chart';
import type { Dataset } from '../../types/dataset';

const FORMATS: { value: ReportFormat; label: string; icon: typeof FileText; note: string }[] = [
  { value: 'html', label: 'HTML', icon: FileCode, note: 'Self-contained page' },
  { value: 'pdf', label: 'PDF', icon: FileType, note: 'Print-ready document' },
  { value: 'markdown', label: 'Markdown', icon: FileText, note: 'Plain text tables' },
];

export function ReportPreview({ title, dataset, sections, insightCount, busy, onDownload }: {
  title: string;
  dataset: Dataset;
  sections: string[];
  insightCount: number;
  busy: ReportFormat | null;
  onDownload: (format: ReportFormat) => void;
}) {
  return (
    <div className="report-preview">
      <FileText size={48} />
      <span className="eyebrow">READY TO EXPORT</span>
      <h2>{title || 'Untitled report'}</h2>
      <p>
        {sections.length} section{sections.length === 1 ? '' : 's'} · from {dataset.name}
        {sections.includes('insights') && ` · ${insightCount} saved insight${insightCount === 1 ? '' : 's'}`}
      </p>
      <div className="format-buttons">
        {FORMATS.map(({ value, label, icon: Icon, note }) => (
          <button key={value} className={value === 'html' ? 'primary' : 'secondary'}
                  disabled={busy !== null || sections.length === 0}
                  onClick={() => onDownload(value)}>
            <Icon size={17} />
            <span>
              {busy === value ? 'Generating…' : label}
              <small>{note}</small>
            </span>
          </button>
        ))}
      </div>
      {sections.length === 0 && <p className="report-warning">Select at least one section to export.</p>}
    </div>
  );
}
