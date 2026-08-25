import { Activity, BarChart3, Bot, Database, FileText, FlaskConical } from 'lucide-react';
import type { LucideIcon } from 'lucide-react';

export type ModuleId = 'source' | 'eda' | 'ai' | 'visualize' | 'reports';

export const MODULES: { id: ModuleId; label: string; icon: LucideIcon }[] = [
  { id: 'source', label: 'Data source', icon: Database },
  { id: 'eda', label: 'Explore data', icon: FlaskConical },
  { id: 'ai', label: 'AI analysis', icon: Bot },
  { id: 'visualize', label: 'Visualizations', icon: BarChart3 },
  { id: 'reports', label: 'Reports', icon: FileText },
];

export function Sidebar({ active, onSelect, online }: { active: ModuleId; onSelect: (id: ModuleId) => void; online: boolean }) {
  return (
    <aside>
      <div className="brand">
        <span><Activity /></span>
        <b>Datum</b>
      </div>
      <nav>
        {MODULES.map(({ id, label, icon: Icon }) => (
          <button key={id} className={active === id ? 'active' : ''} onClick={() => onSelect(id)}
                  aria-current={active === id ? 'page' : undefined}>
            <Icon size={19} />
            <span>{label}</span>
          </button>
        ))}
      </nav>
      <div className="side-foot">
        <span className={online ? 'pulse' : 'pulse offline'} />
        {online ? 'Analysis engine online' : 'Engine unreachable'}
      </div>
    </aside>
  );
}
