export const formatInteger = (value: number): string => value.toLocaleString();

export const formatBytes = (bytes: number): string => {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1048576) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / 1048576).toFixed(2)} MB`;
};

export const formatNumber = (value: unknown, digits = 2): string => {
  if (value === null || value === undefined || value === '') return '—';
  if (typeof value === 'number') {
    if (!Number.isFinite(value)) return '—';
    return Number.isInteger(value) ? value.toLocaleString() : value.toLocaleString(undefined, {
      minimumFractionDigits: digits,
      maximumFractionDigits: digits,
    });
  }
  return String(value);
};

export const formatPercent = (value: number, digits = 1): string => `${value.toFixed(digits)}%`;

export const formatCell = (value: unknown): string => {
  if (value === null || value === undefined) return '—';
  if (typeof value === 'number') return formatNumber(value);
  if (typeof value === 'boolean') return value ? 'true' : 'false';
  if (typeof value === 'object') return JSON.stringify(value);
  return String(value);
};

export const titleCase = (value: string): string =>
  value.replace(/[_-]/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase());

export const humanize = (value: string): string => value.replace(/[_-]/g, ' ');
