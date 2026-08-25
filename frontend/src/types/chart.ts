export type ChartType = 'bar' | 'line' | 'scatter' | 'histogram' | 'box' | 'pie' | 'heatmap';
export type Aggregation = 'none' | 'sum' | 'mean' | 'count' | 'min' | 'max';

export interface ChartRequest {
  chart_type: ChartType;
  x?: string | null;
  y?: string | null;
  aggregation: Aggregation;
  color?: string | null;
  title?: string | null;
}

export interface PlotlyFigure {
  data: Record<string, unknown>[];
  layout: Record<string, unknown>;
}

export type ReportFormat = 'html' | 'markdown' | 'pdf';

export interface ReportRequest {
  title: string;
  sections: string[];
  format: ReportFormat;
  insights: { question?: string; answer: string }[];
}
