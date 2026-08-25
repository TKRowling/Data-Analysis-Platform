import { BarChart3, Bot, Database, FileText, FlaskConical } from 'lucide-react';
import type { LucideIcon } from 'lucide-react';

export type ModuleId = 'source' | 'eda' | 'ai' | 'visualize' | 'reports';

export const MODULES: { id: ModuleId; label: string; icon: LucideIcon }[] = [
  { id: 'source', label: 'Data Sources', icon: Database },
  { id: 'eda', label: 'Exploratory Analysis', icon: FlaskConical },
  { id: 'ai', label: 'AI Analysis', icon: Bot },
  { id: 'visualize', label: 'Visualizations', icon: BarChart3 },
  { id: 'reports', label: 'Reports', icon: FileText },
];

export function Sidebar({ active, onSelect, online }: { active: ModuleId; onSelect: (id: ModuleId) => void; online: boolean }) {
  return (
    <aside>
      <div className="brand">
        <span className="brand-mark">◎</span>
        <b>Data Analytics<br />Platform</b>
      </div>
      <div className="side-rule" />
      <small className="nav-label">Navigation</small>
      <nav>
        {MODULES.map(({ id, label, icon: Icon }) => (
          <button key={id} className={active === id ? 'active' : ''} onClick={() => onSelect(id)}
                  aria-current={active === id ? 'page' : undefined}>
            <i className="nav-radio" />
            <Icon size={16} />
            <span>{label}</span>
          </button>
        ))}
      </nav>
      <div className="side-foot">
        {online ? 'Analysis engine online' : 'Engine unreachable'}
      </div>
    </aside>
  );
}
