export interface NumericStat {
  column: string;
  count: number;
  mean: number | null;
  median: number | null;
  std: number | null;
  min: number | null;
  q25: number | null;
  q75: number | null;
  max: number | null;
  skewness: number | null;
  kurtosis: number | null;
}

export interface CategoricalStat {
  column: string;
  unique: number;
  missing: number;
  top_values: { value: string; count: number; proportion: number }[];
}

export interface Histogram {
  column: string;
  counts: number[];
  edges: (number | null)[];
}

export interface Statistics {
  numeric: NumericStat[];
  categorical: CategoricalStat[];
  histograms: Histogram[];
}

export interface DatatypeIssue {
  column: string;
  dtype: string;
  issue: string;
  detail: string;
  severity: 'high' | 'medium' | 'low';
}

export interface Quality {
  score: number;
  missing: { column: string; count: number; percent: number }[];
  duplicate_rows: number;
  duplicate_percent: number;
  outliers: { column: string; count: number; percent: number; lower_bound: number | null; upper_bound: number | null }[];
  datatype_issues: DatatypeIssue[];
}

export interface StrongCorrelation {
  left: string;
  right: string;
  value: number;
  direction: 'positive' | 'negative';
}

export interface Correlation {
  columns: string[];
  matrix: (number | null)[][];
  strong: StrongCorrelation[];
  method: string;
}

export interface NumericDistribution {
  kind: 'numeric';
  column: string;
  statistics: { mean: number | null; median: number | null; std: number | null; skewness: number | null; count: number };
  histogram: { counts: number[]; edges: (number | null)[] };
  box: { min?: number | null; q1?: number | null; median?: number | null; q3?: number | null; max?: number | null };
  outliers: { count: number; percent: number };
  interpretation: string;
}

export interface CategoricalDistribution {
  kind: 'categorical';
  column: string;
  values: { label: string; count: number; proportion: number }[];
  unique: number;
  total: number;
  interpretation: string;
}

export type Distribution = NumericDistribution | CategoricalDistribution;
