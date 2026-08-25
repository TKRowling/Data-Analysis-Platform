export interface TraceStep {
  step: number;
  stage: 'understand' | 'delegate' | 'compute' | 'narrate';
  agent: string;
  detail: string;
}

export interface AIResult {
  agent: string;
  intent: string;
  answer: string;
  data: Record<string, unknown>;
  suggested_chart: string | null;
  verified: boolean;
  narration_source: 'llm' | 'template';
  trace: TraceStep[];
}

/** A question paired with its answer, as shown in the chat history. */
export interface AIExchange extends AIResult {
  question: string;
}

export interface LLMStatus {
  provider: string;
  model?: string;
  base_url?: string;
  available: boolean;
  mode: 'hybrid' | 'deterministic';
  detail: string;
}
