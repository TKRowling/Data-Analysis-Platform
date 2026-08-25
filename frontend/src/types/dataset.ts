export type ColumnKind = 'numeric' | 'categorical' | 'datetime' | 'boolean';

export interface Dataset {
  id: string;
  name: string;
  source: string;
  rows: number;
  columns: number;
  column_names: string[];
  preview: Record<string, unknown>[];
}

export interface ColumnProfile {
  name: string;
  type: string;
  kind: ColumnKind;
  non_null: number;
  missing: number;
  unique: number;
  sample: string | null;
}

export interface Overview {
  rows: number;
  columns_count: number;
  memory_bytes: number;
  kinds: Record<ColumnKind, number>;
  columns: ColumnProfile[];
  sample: Record<string, unknown>[];
}

export interface DatabaseConfig {
  database_type: 'postgresql' | 'mysql';
  host: string;
  port: number;
  database: string;
  username: string;
  password: string;
  query: string;
}

export interface FeatureResult {
  name: string;
  type: string;
  created: string[];
  sample: unknown[];
  expression?: string;
  transform?: string;
  column?: string;
}
