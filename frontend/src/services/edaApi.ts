import { api, postJson } from './api';
import type { Correlation, Distribution, Quality, Statistics } from '../types/eda';
import type { FeatureResult, Overview } from '../types/dataset';

const eda = (id: string, path: string) => `/datasets/${id}/eda/${path}`;

export const getOverview = (id: string): Promise<Overview> => api<Overview>(eda(id, 'overview'));
export const getStatistics = (id: string): Promise<Statistics> => api<Statistics>(eda(id, 'statistics'));
export const getQuality = (id: string): Promise<Quality> => api<Quality>(eda(id, 'quality'));

export const getCorrelation = (id: string, method = 'pearson'): Promise<Correlation> =>
  api<Correlation>(`${eda(id, 'correlation')}?method=${method}`);

export const getDistribution = (id: string, column: string): Promise<Distribution> =>
  api<Distribution>(`${eda(id, 'distribution')}?column=${encodeURIComponent(column)}`);

export const createFeature = (id: string, name: string, expression: string): Promise<FeatureResult> =>
  postJson<FeatureResult>(`/datasets/${id}/features`, { name, expression });

export const transformFeature = (
  id: string,
  column: string,
  transform: string,
  name?: string,
  bins = 4,
): Promise<FeatureResult> =>
  postJson<FeatureResult>(`/datasets/${id}/features/transform`, { column, transform, name: name || null, bins });
