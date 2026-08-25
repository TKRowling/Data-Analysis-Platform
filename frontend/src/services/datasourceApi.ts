import { api, postJson } from './api';
import type { DatabaseConfig, Dataset } from '../types/dataset';

export const uploadFile = (file: File): Promise<Dataset> => {
  const form = new FormData();
  form.append('file', file);
  return api<Dataset>('/datasets/upload', { method: 'POST', body: form });
};

export const connectDatabase = (config: DatabaseConfig): Promise<Dataset> =>
  postJson<Dataset>('/datasets/database', config);

export const getDataset = (id: string, limit = 20): Promise<Dataset> =>
  api<Dataset>(`/datasets/${id}?limit=${limit}`);

export const listDatasets = (): Promise<Dataset[]> => api<Dataset[]>('/datasets');
