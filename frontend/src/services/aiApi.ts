import { api, postJson } from './api';
import type { AIResult, LLMStatus } from '../types/analysis';

export const askQuestion = (id: string, question: string): Promise<AIResult> =>
  postJson<AIResult>(`/datasets/${id}/ai-analysis`, { question });

export const getLLMStatus = (): Promise<LLMStatus> => api<LLMStatus>('/ai/health');
