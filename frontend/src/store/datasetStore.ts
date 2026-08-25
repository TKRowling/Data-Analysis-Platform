import { useSyncExternalStore } from 'react';
import type { Dataset } from '../types/dataset';

/**
 * The active dataset, shared by every module. A tiny external store rather than context so
 * that non-component code (API clients, hooks) can read it without a provider wrapper.
 */
interface DatasetState {
  dataset: Dataset | null;
  /** Bumped whenever columns change, so dependent views refetch. */
  revision: number;
}

let state: DatasetState = { dataset: null, revision: 0 };
const listeners = new Set<() => void>();

function emit(next: DatasetState): void {
  state = next;
  listeners.forEach((listener) => listener());
}

function subscribe(listener: () => void): () => void {
  listeners.add(listener);
  return () => listeners.delete(listener);
}

export const setActiveDataset = (dataset: Dataset | null): void =>
  emit({ dataset, revision: state.revision + 1 });

/** Record that the dataset gained columns, so open views reload their analysis. */
export const markDatasetChanged = (newColumns: string[] = []): void => {
  const dataset = state.dataset
    ? { ...state.dataset, column_names: [...state.dataset.column_names, ...newColumns] }
    : null;
  emit({ dataset, revision: state.revision + 1 });
};

export const getActiveDataset = (): Dataset | null => state.dataset;

export const useDatasetStore = (): DatasetState => useSyncExternalStore(subscribe, () => state, () => state);
