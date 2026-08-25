import { ReportBuilder } from '../../components/reports/ReportBuilder';
import { Empty, Title } from '../../components/common';
import type { AIExchange } from '../../types/analysis';
import type { Dataset } from '../../types/dataset';

export function ReportsPage({ dataset, insights }: { dataset: Dataset | null; insights: AIExchange[] }) {
  if (!dataset) return <Empty />;
  return (
    <>
      <Title eyebrow="REPORT BUILDER" title="Package the analysis"
             text="Select the evidence your audience needs and export it as HTML, PDF, or Markdown." />
      <ReportBuilder dataset={dataset} insights={insights} />
    </>
  );
}
