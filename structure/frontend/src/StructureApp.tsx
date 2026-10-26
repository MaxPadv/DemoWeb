import React, { useCallback, useEffect, useMemo, useState } from 'react';
import { Employee, listStructure } from './api';
import './styles.css';

type DeptNode = {
  department: string;
  members: Employee[];
  children: DeptNode[];
};

// Группируем сотрудников по отделам вложенно. Родительский отдел определяется по
// отделу непосредственного руководителя (по иерархии manager_id): если у всех
// членов отдела руководители из одного другого отдела — этот отдел является
// родительским. Отделы без единственного родителя — корни дерева.
function buildDeptTree(employees: Employee[]): DeptNode[] {
  const byId = new Map<number, Employee>();
  employees.forEach((e) => byId.set(e.id, e));

  const byDept = new Map<string, Employee[]>();
  employees.forEach((e) => {
    const d = e.department || '—';
    if (!byDept.has(d)) byDept.set(d, []);
    byDept.get(d)!.push(e);
  });

  const parent = new Map<string, string | null>();
  byDept.forEach((members, dept) => {
    const managers: string[] = [];
    members.forEach((m) => {
      const mgr = m.manager_id != null ? byId.get(m.manager_id) : undefined;
      if (mgr && mgr.department && mgr.department !== dept) managers.push(mgr.department);
    });
    const uniq = [...new Set(managers)];
    parent.set(dept, uniq.length === 1 ? uniq[0] : null);
  });

  const nodes = new Map<string, DeptNode>();
  byDept.forEach((members, dept) => nodes.set(dept, { department: dept, members, children: [] }));

  const roots: DeptNode[] = [];
  nodes.forEach((node) => {
    const p = parent.get(node.department);
    if (p && nodes.has(p)) nodes.get(p)!.children.push(node);
    else roots.push(node);
  });
  return roots;
}

export default function StructureApp() {
  const [items, setItems] = useState<Employee[]>([]);
  const [state, setState] = useState<'loading' | 'ready' | 'error'>('loading');

  const reload = useCallback(() => {
    setState('loading');
    listStructure()
      .then((data) => {
        setItems(data);
        setState('ready');
      })
      .catch(() => setState('error'));
  }, []);

  useEffect(() => {
    reload();
  }, [reload]);

  const tree = useMemo(() => buildDeptTree(items), [items]);

  return (
    <div className="st">
      <div className="st-head">
        <div>
          <h1 className="st-title">Структура компании</h1>
          <p className="st-sub">
            Независимый микрофронтенд · деплоится отдельно от оболочки
          </p>
        </div>
        <span className="st-ver">structure@0.1.0</span>
      </div>

      <section className="st-card" aria-labelledby="st-list-title">
        <div className="st-card__head">
          <h2 id="st-list-title" className="st-card__title">
            Сотрудники
          </h2>
          <button className="st-btn st-btn--ghost" onClick={reload} type="button">
            Обновить
          </button>
        </div>

        {state === 'loading' && (
          <div className="st-skeleton" aria-label="Загрузка">
            <span className="st-skeleton__row" />
            <span className="st-skeleton__row" />
            <span className="st-skeleton__row" />
          </div>
        )}
        {state === 'error' && (
          <div className="st-empty" role="alert">
            <p>API структуры не отвечает.</p>
            <button className="st-btn st-btn--ghost" onClick={reload} type="button">
              Повторить
            </button>
          </div>
        )}
        {state === 'ready' && items.length === 0 && (
          <div className="st-empty">
            <p>Сотрудников пока нет.</p>
          </div>
        )}
        {state === 'ready' && items.length > 0 && (
          <div className="st-tree">
            {tree.map((dept) => (
              <DeptGroup key={dept.department} node={dept} />
            ))}
          </div>
        )}
      </section>
    </div>
  );
}

// Отдел: заголовок, сотрудники отдела и вложенные под-отделы.
function DeptGroup({ node }: { node: DeptNode }) {
  const [collapsed, setCollapsed] = useState(false);

  return (
    <div className="st-dept">
      <button
        type="button"
        className="st-dept__head"
        aria-expanded={!collapsed}
        aria-label={node.department}
        onClick={() => setCollapsed((c) => !c)}
      >
        <span className="st-dept__name">{node.department}</span>
        <span className={`st-dept__chevron${collapsed ? ' st-dept__chevron--right' : ''}`}>
          ▾
        </span>
      </button>
      {!collapsed && (
        <>
          <div className="st-dept__members">
            {node.members.map((m) => (
              <div key={m.id} className="st-row">
                <div>
                  <div className="st-row__name">{m.name}</div>
                  <div className="st-row__pos">{m.position}</div>
                </div>
              </div>
            ))}
          </div>
          {node.children.length > 0 && (
            <div className="st-dept__children">
              {node.children.map((c) => (
                <DeptGroup key={c.department} node={c} />
              ))}
            </div>
          )}
        </>
      )}
    </div>
  );
}
