import { AIChat } from '../../components/ai/AIChat';
import { AgentStatus } from '../../components/ai/AgentStatus';
import { AnalysisResult } from '../../components/ai/AnalysisResult';
import { Empty, ErrorBanner, Loading, Title } from '../../components/common';
import type { AIExchange, LLMStatus } from '../../types/analysis';
import type { Dataset } from '../../types/dataset';

export function AIAnalysisPage({ dataset, history, status, busy, error, onAsk }: {
  dataset: Dataset | null;
  history: AIExchange[];
  status: LLMStatus | null;
  busy: boolean;
  error: string;
  onAsk: (question: string) => void;
}) {
  if (!dataset) return <Empty />;

  return (
    <>
      <Title eyebrow="AI DATA ANALYST" title="Ask your data directly"
             text="Five specialist agents work together: one reads your question and delegates, the others compute. Every number comes from your dataset, never from the model." />

      <div className="ai-grid">
        <div>
          <AIChat onAsk={onAsk} busy={busy} />
          <ErrorBanner message={error} />
          {busy && <Loading label="Agents are working…" />}
          <div className="answers">
            {[...history].reverse().map((result, index) => (
              <AnalysisResult key={history.length - index} result={result} />
            ))}
          </div>
          {!busy && history.length === 0 && (
            <p className="muted-text ai-hint">
              Ask a question above, or pick one of the suggestions to see how the agents route it.
            </p>
          )}
        </div>
        <AgentStatus status={status} />
      </div>
    </>
  );
}
