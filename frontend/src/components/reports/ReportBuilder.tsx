import { useState } from 'react';
import { Card, ErrorBanner, Field } from '../common';
import { ReportPreview } from './ReportPreview';
import { ReportSections, SECTIONS } from './ReportSections';
import { downloadReport } from '../../services/reportApi';
import type { ReportFormat } from '../../types/chart';
import type { Dataset } from '../../types/dataset';
import type { AIExchange } from '../../types/analysis';

export function ReportBuilder({ dataset, insights }: { dataset: Dataset; insights: AIExchange[] }) {
  const [title, setTitle] = useState(`${dataset.name} — Analysis Report`);
  const [selected, setSelected] = useState(SECTIONS.map((s) => s.key));
  const [busy, setBusy] = useState<ReportFormat | null>(null);
  const [error, setError] = useState('');

  const toggle = (key: string) =>
    setSelected((current) => (current.includes(key) ? current.filter((k) => k !== key) : [...current, key]));

  const download = async (format: ReportFormat) => {
    setBusy(format);
    setError('');
    try {
      await downloadReport(dataset.id, {
        title: title.trim() || 'Dataset Analysis Report',
        sections: selected,
        format,
        insights: insights.map((item) => ({ question: item.question, answer: item.answer })),
      });
    } catch (cause) {
      setError((cause as Error).message);
    } finally {
      setBusy(null);
    }
  };

  return (
    <>
      <ErrorBanner message={error} onDismiss={() => setError('')} />
      <div className="report-grid">
        <Card title="Report details">
          <Field label="Report title">
            <input value={title} onChange={(event) => setTitle(event.target.value)} />
          </Field>
          <ReportSections selected={selected} onToggle={toggle} />
          {selected.includes('insights') && insights.length === 0 && (
            <p className="muted-text">
              No AI answers saved yet. Ask questions in AI analysis and they will be included here.
            </p>
          )}
        </Card>
        <ReportPreview title={title} dataset={dataset} sections={selected}
                       insightCount={insights.length} busy={busy} onDownload={download} />
      </div>
    </>
  );
}
