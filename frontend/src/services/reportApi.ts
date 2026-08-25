import { downloadBlob, postForBlob } from './api';
import type { ReportFormat, ReportRequest } from '../types/chart';

const EXTENSIONS: Record<ReportFormat, string> = { html: 'html', markdown: 'md', pdf: 'pdf' };

export async function downloadReport(id: string, request: ReportRequest): Promise<void> {
  const blob = await postForBlob(`/datasets/${id}/reports`, request);
  downloadBlob(blob, `analysis-report.${EXTENSIONS[request.format]}`);
}
