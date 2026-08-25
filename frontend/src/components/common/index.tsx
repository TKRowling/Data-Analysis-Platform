import type { ReactNode } from 'react';
import { AlertTriangle, Database } from 'lucide-react';
import { formatCell, humanize } from '../../utils/formatters';

export function Title({ eyebrow, title, text }: { eyebrow: string; title: string; text: string }) {
  return (
    <div className="page-title">
      <span className="title-accent" aria-hidden="true" />
      <div className="title-copy">
        <span className="eyebrow">{eyebrow}</span>
        <h1>{title}</h1>
        <p>{text}</p>
      </div>
    </div>
  );
}

export function Card({ title, sub, action, children }: { title?: string; sub?: string; action?: ReactNode; children: ReactNode }) {
  return (
    <section className="card">
      {(title || action) && (
        <div className="card-head">
          <div>
            {title && <h3>{title}</h3>}
            {sub && <p>{sub}</p>}
          </div>
          {action}
        </div>
      )}
      {children}
    </section>
  );
}

export function Metric({ label, value, note }: { label: string; value: string | number; note?: string }) {
  return (
    <div className="metric">
      <small>{label}</small>
      <b>{value}</b>
      {note && <span>{note}</span>}
    </div>
  );
}

export function Field({ label, hint, children }: { label: string; hint?: string; children: ReactNode }) {
  return (
    <label className="field">
      <span>{label}</span>
      {children}
      {hint && <small className="field-hint">{hint}</small>}
    </label>
  );
}

export function DataTable({ rows, limit = 100, empty = 'No results.' }: { rows: Record<string, unknown>[]; limit?: number; empty?: string }) {
  if (!rows?.length) return <p className="muted-text">{empty}</p>;
  const columns = Object.keys(rows[0]);
  return (
    <div className="table-wrap">
      <table>
        <thead>
          <tr>{columns.map((c) => <th key={c}>{humanize(c)}</th>)}</tr>
        </thead>
        <tbody>
          {rows.slice(0, limit).map((row, index) => (
            <tr key={index}>
              {columns.map((c) => {
                const value = row[c];
                const numeric = typeof value === 'number';
                return <td key={c} className={numeric ? 'numeric-cell' : undefined}>{formatCell(value)}</td>;
              })}
            </tr>
          ))}
        </tbody>
      </table>
      {rows.length > limit && <p className="muted-text table-note">Showing {limit} of {rows.length} rows.</p>}
    </div>
  );
}

export function Empty({ message = 'Connect a dataset first', hint = 'Upload a CSV or Excel file from Data source to begin.' }: { message?: string; hint?: string }) {
  return (
    <div className="empty">
      <Database size={44} />
      <h2>{message}</h2>
      <p>{hint}</p>
    </div>
  );
}

export function Loading({ label = 'Calculating analysis…' }: { label?: string }) {
  return <div className="loading"><span className="spinner" />{label}</div>;
}

export function ErrorBanner({ message, onDismiss }: { message: string; onDismiss?: () => void }) {
  if (!message) return null;
  return (
    <div className="error" role="alert">
      <AlertTriangle size={17} />
      <span>{message}</span>
      {onDismiss && <button type="button" onClick={onDismiss} aria-label="Dismiss">×</button>}
    </div>
  );
}

export function Tabs({ tabs, active, onSelect }: { tabs: string[]; active: string; onSelect: (tab: string) => void }) {
  return (
    <div className="tabs" role="tablist">
      {tabs.map((tab) => (
        <button key={tab} role="tab" aria-selected={active === tab}
                className={active === tab ? 'active' : ''} onClick={() => onSelect(tab)}>
          {tab}
        </button>
      ))}
    </div>
  );
}
