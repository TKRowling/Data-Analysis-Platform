import { ChartBuilder } from '../../components/visualization/ChartBuilder';
import { Empty, Title } from '../../components/common';
import { useEDA } from '../../hooks/useEDA';
import { getOverview } from '../../services/edaApi';
import type { Dataset } from '../../types/dataset';

export function VisualizationPage({ dataset, revision }: { dataset: Dataset | null; revision: number }) {
  const { data } = useEDA(dataset?.id, getOverview, [revision]);
  if (!dataset) return <Empty />;

  const columns = data?.columns ?? dataset.column_names.map((name) => ({
    name, type: 'unknown', kind: 'categorical' as const, non_null: 0, missing: 0, unique: 0, sample: null,
  }));

  return (
    <>
      <Title eyebrow="AUTOMATED VISUALIZATION" title="Interactive Visualizations"
             text="Select a chart, map your dataset columns, and generate an interactive analysis-ready visual." />
      <ChartBuilder dataset={dataset} columns={columns} />
    </>
  );
}
