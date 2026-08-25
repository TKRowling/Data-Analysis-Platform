import { useState } from 'react';
import { ChartControls } from './ChartControls';
import { ChartPreview } from './ChartPreview';
import { ErrorBanner } from '../common';
import { createChart } from '../../services/visualizationApi';
import type { ChartRequest, PlotlyFigure } from '../../types/chart';
import type { ColumnProfile, Dataset } from '../../types/dataset';

const INITIAL: ChartRequest = { chart_type: 'bar', x: null, y: null, aggregation: 'sum', color: null, title: null };

export function ChartBuilder({ dataset, columns }: { dataset: Dataset; columns: ColumnProfile[] }) {
  const [request, setRequest] = useState<ChartRequest>(INITIAL);
  const [figure, setFigure] = useState<PlotlyFigure | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');

  const generate = async () => {
    setBusy(true);
    setError('');
    try {
      setFigure(await createChart(dataset.id, request));
    } catch (cause) {
      setError((cause as Error).message);
      setFigure(null);
    } finally {
      setBusy(false);
    }
  };

  return (
    <>
      <ErrorBanner message={error} onDismiss={() => setError('')} />
      <div className="builder">
        <ChartControls request={request} columns={columns} onChange={setRequest}
                       onGenerate={generate} busy={busy} />
        <ChartPreview figure={figure} loading={busy} />
      </div>
    </>
  );
}
