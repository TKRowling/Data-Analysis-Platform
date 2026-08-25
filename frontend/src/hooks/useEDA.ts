import { useEffect, useState } from 'react';

interface AsyncData<T> {
  data: T | null;
  loading: boolean;
  error: string;
  reload: () => void;
}

/**
 * Fetch one EDA resource for the active dataset.
 * `fetcher` is called whenever the dataset id, the revision, or a dependency changes.
 */
export function useEDA<T>(
  datasetId: string | undefined,
  fetcher: (id: string) => Promise<T>,
  deps: unknown[] = [],
): AsyncData<T> {
  const [data, setData] = useState<T | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [nonce, setNonce] = useState(0);

  useEffect(() => {
    if (!datasetId) {
      setData(null);
      return;
    }
    let cancelled = false;
    setLoading(true);
    setError('');
    fetcher(datasetId)
      .then((result) => {
        if (!cancelled) setData(result);
      })
      .catch((cause: Error) => {
        if (!cancelled) {
          setError(cause.message);
          setData(null);
        }
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [datasetId, nonce, ...deps]);

  return { data, loading, error, reload: () => setNonce((n) => n + 1) };
}
