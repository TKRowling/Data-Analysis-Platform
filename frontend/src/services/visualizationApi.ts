import { postJson } from './api';
import type { ChartRequest, PlotlyFigure } from '../types/chart';

export const createChart = (id: string, request: ChartRequest): Promise<PlotlyFigure> =>
  postJson<PlotlyFigure>(`/datasets/${id}/charts`, request);
