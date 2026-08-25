import { useCallback, useState } from 'react';
import { connectDatabase, uploadFile } from '../services/datasourceApi';
import { setActiveDataset, useDatasetStore } from '../store/datasetStore';
import type { DatabaseConfig, Dataset } from '../types/dataset';

interface UseDataset {
  dataset: Dataset | null;
  revision: number;
  busy: boolean;
  error: string;
  clearError: () => void;
  load: (file: File) => Promise<Dataset | null>;
  connect: (config: DatabaseConfig) => Promise<Dataset | null>;
}

export function useDataset(): UseDataset {
  const { dataset, revision } = useDatasetStore();
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');

  const run = useCallback(async (task: () => Promise<Dataset>): Promise<Dataset | null> => {
    setBusy(true);
    setError('');
    try {
      const result = await task();
      setActiveDataset(result);
      return result;
    } catch (cause) {
      setError((cause as Error).message);
      return null;
    } finally {
      setBusy(false);
    }
  }, []);

  return {
    dataset,
    revision,
    busy,
    error,
    clearError: () => setError(''),
    load: (file: File) => run(() => uploadFile(file)),
    connect: (config: DatabaseConfig) => run(() => connectDatabase(config)),
  };
}
