import { ReportBuilder } from '../../components/reports/ReportBuilder';
import { Empty, Title } from '../../components/common';
import type { AIExchange } from '../../types/analysis';
import type { Dataset } from '../../types/dataset';

export function ReportsPage({ dataset, insights }: { dataset: Dataset | null; insights: AIExchange[] }) {
  if (!dataset) return <Empty />;
  return (
    <>
      <Title eyebrow="AUTOMATED REPORTING" title="Automated Reports"
             text="Generate a comprehensive analysis report from your dataset, verified insights, and selected analytical sections." />
      <ReportBuilder dataset={dataset} insights={insights} />
    </>
  );
}
