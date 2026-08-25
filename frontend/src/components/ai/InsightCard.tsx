import { ArrowRight } from 'lucide-react';
import type { TraceStep } from '../../types/analysis';
import { titleCase } from '../../utils/formatters';

/** The agent hand-off trail for one answer. */
export function InsightCard({ trace }: { trace: TraceStep[] }) {
  if (!trace?.length) return null;
  return (
    <details className="trace">
      <summary>
        How this was answered
        <span className="trace-agents">
          {trace.map((step, index) => (
            <span key={step.step}>
              {titleCase(step.stage)}
              {index < trace.length - 1 && <ArrowRight size={11} />}
            </span>
          ))}
        </span>
      </summary>
      <ol>
        {trace.map((step) => (
          <li key={step.step}>
            <b>{titleCase(step.stage)}</b>
            <em>{step.agent.replace(/_/g, ' ')}</em>
            <p>{step.detail}</p>
          </li>
        ))}
      </ol>
    </details>
  );
}
