import { Bot, ShieldCheck, Zap } from 'lucide-react';
import type { LLMStatus } from '../../types/analysis';

const PROVIDER_LABELS: Record<string, string> = {
  ollama: 'Ollama (local)',
  cloudflare: 'Cloudflare Workers AI',
};

const AGENTS = [
  { name: 'Orchestrator', role: 'Understands the question and delegates' },
  { name: 'Statistical', role: 'Aggregations, rankings, outliers' },
  { name: 'Pattern', role: 'Correlation, trends, segments' },
  { name: 'Predictive', role: 'Regression, classification, forecast' },
  { name: 'Insight', role: 'Explains the verified result' },
];

export function AgentStatus({ status }: { status: LLMStatus | null }) {
  return (
    <div className="agent-status">
      <div className="agent-status-head">
        <span className={`mode-badge ${status?.available ? 'live' : 'degraded'}`}>
          {status?.available ? <Zap size={13} /> : <ShieldCheck size={13} />}
          {status?.available ? 'Hybrid mode' : 'Deterministic mode'}
        </span>
        <p>{status?.detail ?? 'Checking the analysis engine…'}</p>
        {status && (
          <dl className="provider-info">
            <dt>Provider</dt>
            <dd>{PROVIDER_LABELS[status.provider] ?? status.provider}</dd>
            {status.model && (<><dt>Model</dt><dd title={status.model}>{status.model}</dd></>)}
          </dl>
        )}
      </div>
      <ul>
        {AGENTS.map((agent) => (
          <li key={agent.name}>
            <span><Bot size={14} /></span>
            <div>
              <b>{agent.name}</b>
              <small>{agent.role}</small>
            </div>
          </li>
        ))}
      </ul>
    </div>
  );
}
