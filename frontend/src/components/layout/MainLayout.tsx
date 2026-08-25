import type { ReactNode } from 'react';
import { Header } from './Header';
import { MODULES, Sidebar } from './Sidebar';
import type { ModuleId } from './Sidebar';
import type { Dataset } from '../../types/dataset';

export function MainLayout({ module, onSelect, dataset, online, children }: {
  module: ModuleId;
  onSelect: (id: ModuleId) => void;
  dataset: Dataset | null;
  online: boolean;
  children: ReactNode;
}) {
  const title = MODULES.find((m) => m.id === module)?.label ?? '';
  return (
    <div className="shell">
      <Sidebar active={module} onSelect={onSelect} online={online} />
      <main>
        <Header title={title} dataset={dataset} />
        <div className="content">{children}</div>
      </main>
    </div>
  );
}
