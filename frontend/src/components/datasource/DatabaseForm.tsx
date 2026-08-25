import { useState } from 'react';
import { Card, Field } from '../common';
import type { DatabaseConfig } from '../../types/dataset';

const DEFAULT: DatabaseConfig = {
  database_type: 'postgresql',
  host: 'localhost',
  port: 5432,
  database: '',
  username: '',
  password: '',
  query: 'SELECT * FROM public.table_name LIMIT 10000',
};

const TEXT_FIELDS: { key: keyof DatabaseConfig; label: string; type: string }[] = [
  { key: 'host', label: 'Host', type: 'text' },
  { key: 'port', label: 'Port', type: 'number' },
  { key: 'database', label: 'Database', type: 'text' },
  { key: 'username', label: 'Username', type: 'text' },
  { key: 'password', label: 'Password', type: 'password' },
];

export function DatabaseForm({ onConnect, busy }: { onConnect: (config: DatabaseConfig) => void; busy: boolean }) {
  const [config, setConfig] = useState<DatabaseConfig>(DEFAULT);
  const update = (key: keyof DatabaseConfig, value: string | number) =>
    setConfig((current) => ({ ...current, [key]: value }));

  const incomplete = !config.host || !config.database || !config.username || !config.query.trim();

  return (
    <Card title="Database connection" sub="Credentials are used for this request only and are never stored.">
      <div className="controls">
        <Field label="Type">
          <select value={config.database_type}
                  onChange={(event) => {
                    const database_type = event.target.value as DatabaseConfig['database_type'];
                    setConfig((current) => ({ ...current, database_type, port: database_type === 'mysql' ? 3306 : 5432 }));
                  }}>
            <option value="postgresql">PostgreSQL</option>
            <option value="mysql">MySQL</option>
          </select>
        </Field>
        {TEXT_FIELDS.map(({ key, label, type }) => (
          <Field key={key} label={label}>
            <input type={type} value={String(config[key])} autoComplete="off"
                   onChange={(event) => update(key, type === 'number' ? Number(event.target.value) : event.target.value)} />
          </Field>
        ))}
      </div>
      <Field label="Read-only query" hint="Only SELECT statements are accepted.">
        <textarea className="query" value={config.query} spellCheck={false}
                  onChange={(event) => update('query', event.target.value)} />
      </Field>
      <button className="primary" onClick={() => onConnect(config)} disabled={busy || incomplete}>
        {busy ? 'Connecting…' : 'Connect and load'}
      </button>
    </Card>
  );
}
