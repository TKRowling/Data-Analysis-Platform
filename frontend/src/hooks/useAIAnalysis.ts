import { useCallback, useEffect, useState } from 'react';
import { askQuestion, getLLMStatus } from '../services/aiApi';
import type { AIExchange, LLMStatus } from '../types/analysis';

interface UseAIAnalysis {
  history: AIExchange[];
  status: LLMStatus | null;
  busy: boolean;
  error: string;
  ask: (question: string) => Promise<void>;
  clear: () => void;
}

export function useAIAnalysis(datasetId: string | undefined): UseAIAnalysis {
  const [history, setHistory] = useState<AIExchange[]>([]);
  const [status, setStatus] = useState<LLMStatus | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');

  useEffect(() => {
    let cancelled = false;
    getLLMStatus()
      .then((result) => !cancelled && setStatus(result))
      .catch(() => undefined);
    return () => {
      cancelled = true;
    };
  }, []);

  // A new dataset invalidates the conversation.
  useEffect(() => setHistory([]), [datasetId]);

  const ask = useCallback(
    async (question: string) => {
      if (!datasetId || !question.trim()) return;
      setBusy(true);
      setError('');
      try {
        const result = await askQuestion(datasetId, question.trim());
        setHistory((items) => [...items, { ...result, question: question.trim() }]);
      } catch (cause) {
        setError((cause as Error).message);
      } finally {
        setBusy(false);
      }
    },
    [datasetId],
  );

  return { history, status, busy, error, ask, clear: () => setHistory([]) };
}
