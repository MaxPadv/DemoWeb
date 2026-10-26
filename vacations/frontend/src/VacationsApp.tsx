import React, { useCallback, useEffect, useMemo, useState } from 'react';
import {
  VacationRequest,
  createVacation,
  decideVacation,
  fetchDepartmentOverlaps,
  getMe,
  listVacations,
  Overlap,
} from './api';
import './styles.css';

const STATUS_META = {
  pending: { label: 'На согласовании', cls: 'vc-pill--pending' },
  approved: { label: 'Согласован', cls: 'vc-pill--approved' },
  rejected: { label: 'Отклонён', cls: 'vc-pill--rejected' },
} as const;

/* Производственный календарь 2027: нерабочие праздники и переносы (date -> название). */
const HOLIDAYS_2027: Record<string, string> = {
  '2027-01-01': 'Новогодние каникулы',
  '2027-01-02': 'Новогодние каникулы',
  '2027-01-03': 'Новогодние каникулы',
  '2027-01-04': 'Новогодние каникулы',
  '2027-01-05': 'Новогодние каникулы',
  '2027-01-06': 'Новогодние каникулы',
  '2027-01-07': 'Рождество Христово',
  '2027-01-08': 'Новогодние каникулы',
  '2027-02-22': 'Перенесённый выходной',
  '2027-02-23': 'День защитника Отечества',
  '2027-03-08': 'Международный женский день',
  '2027-05-01': 'Праздник Весны и Труда',
  '2027-05-03': 'Перенесённый выходной',
  '2027-05-09': 'День Победы',
  '2027-05-10': 'Перенесённый выходной',
  '2027-06-12': 'День России',
  '2027-06-14': 'Перенесённый выходной',
  '2027-11-04': 'День народного единства',
  '2027-11-05': 'Перенесённый выходной',
  '2027-12-31': 'Перенесённый выходной',
};

function fmtDate(iso: string): string {
  const d = new Date(iso + 'T00:00:00');
  return d.toLocaleDateString('ru-RU', { day: '2-digit', month: '2-digit', year: 'numeric' });
}
/** Tooltip state for a calendar cell. */
interface TooltipState {
  visible: boolean;
  x: number;
  y: number;
  vacations: VacationRequest[];
}

/** Hook to manage tooltip visibility and position on calendar cells. */
function useVacationTooltip() {
  const [tip, setTip] = useState<TooltipState>({
    visible: false,
    x: 0,
    y: 0,
    vacations: [],
  });

  function show(e: React.MouseEvent, vacations: VacationRequest[]) {
    const { clientX: x, clientY: y } = e;
    setTip({ visible: true, x, y, vacations });
  }

  function hide() {
    setTip((prev) => (prev.visible ? { ...prev, visible: false } : prev));
  }

  return { tip, show, hide };
}

/** Portable tooltip rendered on top of the page. */
function VacationTooltip({ tip }: { tip: TooltipState }) {
  if (!tip.visible || tip.vacations.length === 0) return null;

  const { x, y, vacations } = tip;

  /* Compute overlap of all vacation ranges on this day. */
  let overlapStart: string | null = null;
  let overlapEnd: string | null = null;
  for (const v of vacations) {
    if (overlapStart === null || v.start > overlapStart) overlapStart = v.start;
    if (overlapEnd === null || v.end < overlapEnd) overlapEnd = v.end;
  }

  const lines = vacations.map(
    (v) => `${fmtDate(v.start)} — ${fmtDate(v.end)} · ${v.employee}`,
  );
  if (vacations.length >= 2 && overlapStart && overlapEnd) {
    lines.push(`Пересечение: ${fmtDate(overlapStart)} — ${fmtDate(overlapEnd)}`);
  }

  return (
    <div
      ref={(node) => {
        if (!node) return;
        const rect = node.getBoundingClientRect();
        const vw = window.innerWidth;
        const vh = window.innerHeight;
        let left = x + 10;
        let top = y + 10;
        if (left + rect.width > vw - 8) left = x - rect.width - 10;
        if (top + rect.height > vh - 8) top = y - rect.height - 10;
        node.style.left = `${left}px`;
        node.style.top = `${top}px`;
      }}
      className="pc-tooltip"
    >
      {lines.map((line, i) => (
        <div key={i} className={i >= vacations.length ? 'pc-tooltip__overlap' : 'pc-tooltip__row'}>
          {line}
        </div>
      ))}
    </div>
  );
}

/* ===== Holiday tooltip ===== */
/** Tooltip state for a holiday cell (name only). */
interface HolidayTooltipState {
  visible: boolean;
  x: number;
  y: number;
  name: string;
}

/** Hook to manage holiday tooltip visibility/position. */
function useHolidayTooltip() {
  const [tip, setTip] = useState<HolidayTooltipState>({
    visible: false,
    x: 0,
    y: 0,
    name: '',
  });

  function show(e: React.MouseEvent, name: string) {
    const { clientX: x, clientY: y } = e;
    setTip({ visible: true, x, y, name });
  }

  function hide() {
    setTip((prev) => (prev.visible ? { ...prev, visible: false } : prev));
  }

  return { tip, show, hide };
}

/** Portable tooltip for holiday name, styled like the vacation tooltip. */
function HolidayTooltip({ tip }: { tip: HolidayTooltipState }) {
  if (!tip.visible) return null;

  const { x, y, name } = tip;

  return (
    <div
      ref={(node) => {
        if (!node) return;
        const rect = node.getBoundingClientRect();
        const vw = window.innerWidth;
        const vh = window.innerHeight;
        let left = x + 10;
        let top = y + 10;
        if (left + rect.width > vw - 8) left = x - rect.width - 10;
        if (top + rect.height > vh - 8) top = y - rect.height - 10;
        node.style.left = `${left}px`;
        node.style.top = `${top}px`;
      }}
      className="pc-tooltip pc-tooltip--holiday"
    >
      <div className="pc-tooltip__row">{name}</div>
    </div>
  );
}

/* ===== Paper Calendar 2027 helpers ===== */

const RU_MONTHS = [
  'Январь','Февраль','Март','Апрель','Май','Июнь',
  'Июль','Август','Сентябрь','Октябрь','Ноябрь','Декабрь',
];
const RU_WEEKDAYS = ['Пн','Вт','Ср','Чт','Пт','Сб','Вс'];

function getInitials(name: string): string {
  return name
    .split(/\s+/)
    .map((w) => w[0])
    .join('')
    .slice(0, 2)
    .toUpperCase();
}

function datesInRange(start: string, end: string): string[] {
  const dates: string[] = [];
  const s = new Date(start + 'T00:00:00');
  const e = new Date(end + 'T00:00:00');
  const cur = new Date(s);
  const fmt = (d: Date) =>
    `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`;
  while (cur <= e) {
    // ponytail: локальные компоненты (не toISOString), иначе в UTC+3 (MSK) дата сдвигается на день назад
    dates.push(fmt(cur));
    cur.setDate(cur.getDate() + 1);
  }
  return dates;
}

/** Build per-day employee map for 2027 vacations.
 * Result: date string -> list of VacationRequest whose range covers that date. */
function buildVacationMap(vacations: VacationRequest[]): Record<string, VacationRequest[]> {
  const map: Record<string, VacationRequest[]> = {};
  for (const v of vacations) {
    if (!v.start || !v.end) continue;
    const y = parseInt(v.start, 10);
    if (y !== 2027) continue;
    const days = datesInRange(v.start, v.end);
    for (const d of days) {
      (map[d] ??= []).push(v);
    }
  }
  return map;
}

/** Container that holds the tooltip state shared across all month grids. */
function MonthGridWithTooltip({
  monthIndex,
  vacationMap,
  tip,
  onShow,
  onHide,
  holidayTip,
  onHolidayShow,
  onHolidayHide,
  selectedStart,
  selectedEnd,
  onSelect,
}: {
  monthIndex: number;
  vacationMap: Record<string, VacationRequest[]>;
  tip: TooltipState;
  onShow: (e: React.MouseEvent, vacations: VacationRequest[]) => void;
  onHide: () => void;
  holidayTip: HolidayTooltipState;
  onHolidayShow: (e: React.MouseEvent, name: string) => void;
  onHolidayHide: () => void;
  selectedStart: string | null;
  selectedEnd: string | null;
  onSelect: (date: string) => void;
}) {
  const year = 2027;
  const daysInMonth = new Date(year, monthIndex + 1, 0).getDate();
  const firstWeekday = (new Date(year, monthIndex, 1).getDay() + 6) % 7;

  const cells: { day: number | null; date: string | null }[] = [];
  for (let i = 0; i < firstWeekday; i++) {
    cells.push({ day: null, date: null });
  }
  for (let d = 1; d <= daysInMonth; d++) {
    const dateStr = `${year}-${String(monthIndex + 1).padStart(2, '0')}-${String(d).padStart(2, '0')}`;
    cells.push({ day: d, date: dateStr });
  }
  const remaining = (7 - (cells.length % 7)) % 7;
  for (let i = 0; i < remaining; i++) {
    cells.push({ day: null, date: null });
  }

  const weeks: typeof cells[] = [];
  for (let i = 0; i < cells.length; i += 7) {
    weeks.push(cells.slice(i, i + 7));
  }

  return (
    <div className="pc-month">
      <div className="pc-month__header">{RU_MONTHS[monthIndex]}</div>
      <table>
        <thead>
          <tr>
            {RU_WEEKDAYS.map((w) => (
              <th key={w} className="pc-weekday">{w}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {weeks.map((week, wi) => (
            <tr key={wi}>
              {week.map((cell, ci) => {
                if (cell.date === null) {
                  return <td key={ci} className="pc-cell pc-cell--empty" />;
                }
                const vacations = vacationMap[cell.date] || [];
                const count = vacations.length;
                let cls = 'pc-cell';
                const holidayName = HOLIDAYS_2027[cell.date];
                const dow = new Date(cell.date + 'T00:00:00').getDay();
                // праздник/перенос — красный; иначе сб/вс — серый (рабочие — как сейчас)
                if (holidayName) cls += ' pc-cell--holiday';
                else if (dow === 0 || dow === 6) cls += ' pc-cell--weekend';
                if (count === 1) cls += ' pc-cell--on';
                else if (count >= 2) cls += ' pc-cell--conflict';
                const isStart = selectedStart !== null && selectedStart === cell.date;
                const isEnd = selectedEnd !== null && selectedEnd === cell.date;
                // старт подсвечивается сразу после первого клика (пока конец не выбран)
                const startOnly = isStart && selectedEnd === null;
                const inSel = selectedStart !== null && selectedEnd !== null && cell.date >= selectedStart && cell.date <= selectedEnd;
                if (inSel || startOnly) {
                  cls += ' pc-cell--sel';
                  if (isStart) cls += ' pc-cell--sel-start';
                  if (isEnd) cls += ' pc-cell--sel-end';
                }

                let inits: string | undefined;
                if (count >= 1) {
                  const unique = new Map<string, VacationRequest>();
                  for (const v of vacations) {
                    if (!unique.has(v.employee)) unique.set(v.employee, v);
                  }
                  inits = Array.from(unique.entries())
                    .map(([, v]) => getInitials(v.employee))
                    .join(' ');
                }

                return (
                  <td
                    key={ci}
                    className={cls}
                    title=""
                    onMouseMove={(e) => {
                      if (holidayName) onHolidayShow(e, holidayName);
                      else if (count > 0) onShow(e, vacations);
                    }}
                    onMouseLeave={() => {
                      onHide();
                      onHolidayHide();
                    }}
                    onClick={() => onSelect(cell.date as string)}
                  >
                    <span className="pc-cell__num">{cell.day}</span>
                    {inits && <span className="pc-inits">{inits}</span>}
                  </td>
                );
              })}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

/* ===== Paper Calendar 2027 component ===== */
/** Container that holds tooltip state for all month grids. */
function PaperCalendar2027({
  refreshKey = 0,
  selectedStart = null,
  selectedEnd = null,
  onSelect,
}: {
  refreshKey?: number;
  selectedStart?: string | null;
  selectedEnd?: string | null;
  onSelect: (date: string) => void;
}) {
  const [items, setItems] = useState<VacationRequest[]>([]);
  const [overlaps, setOverlaps] = useState<Overlap[]>([]);
  const [state, setState] = useState<'loading' | 'ready' | 'error'>('loading');
  const [expanded, setExpanded] = useState(false);
  const [overlapsExpanded, setOverlapsExpanded] = useState(false);
  const { tip, show, hide } = useVacationTooltip();
  const { tip: holidayTip, show: showHoliday, hide: hideHoliday } = useHolidayTooltip();

  useEffect(() => {
    fetchDepartmentOverlaps()
      .then(({ vacations, overlaps: ov }) => {
        setItems(vacations);
        setOverlaps(ov);
        setState('ready');
      })
      .catch(() => setState('error'));
  }, [refreshKey]);

  // useMemo вызывается безусловно (до ранних return loading/error) — иначе React #310.
  const vacationMap = useMemo(() => buildVacationMap(items), [items]);

  if (state === 'loading') {
    return (
      <div className="vc-skeleton" aria-label="Загрузка календаря">
        <span className="pc-skeleton" />
        <span className="pc-skeleton" />
        <span className="pc-skeleton" />
      </div>
    );
  }

  if (state === 'error') {
    return (
      <div className="vc-empty" role="alert">
        <p>API отпусков не отвечает.</p>
        <button className="vc-btn vc-btn--ghost" onClick={() => window.location.reload()}>
          Повторить
        </button>
      </div>
    );
  }

  const visibleMonths = expanded ? 12 : 3;
  const remainingMonths = 12 - visibleMonths;

  return (
    <div className="pc-cal">
      <div className="pc-cal__legend">
        <span className="pc-cal__legend-item">
          <span className="pc-cal__legend-swatch pc-cal__legend-swatch--on" />
          Отпуск
        </span>
        <span className="pc-cal__legend-item">
          <span className="pc-cal__legend-swatch pc-cal__legend-swatch--conflict" />
          Пересечение
        </span>
      </div>
      <div className="pc-cal__grid">
        {Array.from({ length: visibleMonths }, (_, i) => (
          <MonthGridWithTooltip
            key={i}
            monthIndex={i}
            vacationMap={vacationMap}
            tip={tip}
            onShow={show}
            onHide={hide}
            holidayTip={holidayTip}
            onHolidayShow={showHoliday}
            onHolidayHide={hideHoliday}
            selectedStart={selectedStart}
            selectedEnd={selectedEnd}
            onSelect={onSelect}
          />
        ))}
      </div>
      {(expanded || remainingMonths > 0) && (
        <div className="pc-collapse-bar">
          <button
            className="vc-btn vc-btn--ghost"
            type="button"
            onClick={() => setExpanded((e) => !e)}
          >
            {expanded ? 'Скрыть' : 'Показать все'}
          </button>
        </div>
      )}
      <div className="pc-overlaps">
        <div className="pc-overlaps__title">Пересечения</div>
        {overlaps.length === 0 ? (
          <div className="pc-overlaps-empty">Пересечений нет</div>
        ) : (
          <>
            {(overlapsExpanded ? overlaps : overlaps.slice(0, 3)).map((o, i) => (
              <div key={i} className="pc-overlap-line">
                {o.employee_a} ↔ {o.employee_b}: {fmtDate(o.start)} — {fmtDate(o.end)} ({o.days} дн.)
              </div>
            ))}
            {overlaps.length > 3 && (
              <button
                className="vc-btn vc-btn--ghost pc-overlaps-toggle"
                type="button"
                onClick={() => setOverlapsExpanded((e) => !e)}
              >
                {overlapsExpanded ? 'Скрыть' : 'Показать все'}
              </button>
            )}
          </>
        )}
      </div>
      <VacationTooltip tip={tip} />
      <HolidayTooltip tip={holidayTip} />
    </div>
  );
}


/* ===== Plan vacations service (existing functionality) ===== */

const PLANNED_TYPE: 'annual' = 'annual';

function PlanVacations() {
  const [items, setItems] = useState<VacationRequest[]>([]);
  const [state, setState] = useState<'loading' | 'ready' | 'error'>('loading');
  const [itemsExpanded, setItemsExpanded] = useState(false);
  const [start, setStart] = useState('');
  const [end, setEnd] = useState('');
  const [comment, setComment] = useState('');
  const [formError, setFormError] = useState<string | null>(null);
  const [formOk, setFormOk] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);
  // ponytail: тик заставляет PaperCalendar перечитать данные после approve/reject/create.
  const [calendarTick, setCalendarTick] = useState(0);
  // интерактивный выбор периода на календаре (старт/конец) + сообщение об ошибке выбора.
  const [selectedStart, setSelectedStart] = useState<string | null>(null);
  const [selectedEnd, setSelectedEnd] = useState<string | null>(null);
  const [selMsg, setSelMsg] = useState<string | null>(null);
  // текущий пользователь — чтобы отличать СВОИ отпуска (блок) от коллег (предупреждение).
  const [me, setMe] = useState<string>('');

  const reload = useCallback(() => {
    setState('loading');
    listVacations()
      .then((data) => {
        setItems(data);
        setState('ready');
      })
      .catch(() => setState('error'));
  }, []);

  useEffect(reload, [reload]);

  useEffect(() => {
    getMe()
      .then((u) => setMe(u.name))
      .catch(() => setMe(''));
  }, []);

  const stats = useMemo(() => {
    const pending = items.filter((i) => i.status === 'pending').length;
    const approvedDays = items
      .filter((i) => i.status === 'approved' && i.type === 'annual')
      .reduce((s, i) => s + i.days, 0);
    return { pending, approvedDays, total: items.length };
  }, [items]);

  // ponytail: блок — только пересечение с СОБСТВЕННЫМИ отпусками (status != 'rejected').
  const ownOverlap = useMemo(() => {
    if (!start || !end || !me) return null;
    return (
      items.find(
        (i) =>
          i.employee === me &&
          i.status !== 'rejected' &&
          i.start <= end &&
          i.end >= start,
      ) || null
    );
  }, [items, start, end, me]);

  // ponytail: пересечение с коллегой отдела — НЕ блокирует, только предупреждение
  // (решает руководитель при согласовании).
  const deptOverlap = useMemo(() => {
    if (!start || !end) return null;
    return (
      items.find(
        (i) =>
          i.employee !== me &&
          i.status !== 'rejected' &&
          i.start <= end &&
          i.end >= start,
      ) || null
    );
  }, [items, start, end, me]);

  // Интерактивный выбор периода на календаре: клик по рабочему дню — старт,
  // второй клик — конец. С выходного старт невозможен; период 1..28 дней.
  function onSelectDate(date: string) {
    const dow = new Date(date + 'T00:00:00').getDay();
    const isWeekend = dow === 0 || dow === 6;
    const isHoliday = date in HOLIDAYS_2027;
    const blocked = isWeekend || isHoliday;
    setSelMsg(null);

    // Уже есть завершённый период — любой клик начинает выбор заново.
    if (selectedStart !== null && selectedEnd !== null) {
      if (blocked) { setSelectedStart(null); setSelectedEnd(null); setStart(''); setEnd(''); }
      else { setSelectedStart(date); setSelectedEnd(null); setStart(date); }
      return;
    }

    // Выбора ещё нет — старт. С выходного (сб/вс) или праздника начинать нельзя.
    if (selectedStart === null) {
      if (blocked) return;
      setSelectedStart(date);
      setStart(date);
      return;
    }

    // Старт есть, конца нет.
    if (date === selectedStart) {
      // повторный клик по старту — сброс и заново
      setSelectedStart(null); setSelectedEnd(null); setStart(''); setEnd('');
      return;
    }
    if (date < selectedStart) {
      // клик раньше старта — новый старт
      if (blocked) { setSelectedStart(null); setSelectedEnd(null); setStart(''); setEnd(''); }
      else { setSelectedStart(date); setStart(date); }
      return;
    }
    // клик после старта — конец периода
    const days = Math.round((new Date(date + 'T00:00:00').getTime() - new Date(selectedStart + 'T00:00:00').getTime()) / 86400000) + 1;
    if (days > 28) { setSelMsg('Период не может быть длиннее 28 дней.'); return; }
    if (days < 1) { setSelMsg('Период должен быть не короче 1 дня.'); return; }
    setSelectedEnd(date);
    setEnd(date);
  }

  function resetSelection() {
    setSelectedStart(null);
    setSelectedEnd(null);
    setStart('');
    setEnd('');
    setSelMsg(null);
  }

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    setFormError(null);
    setFormOk(null);
    if (!start || !end) {
      setFormError('Укажите даты начала и окончания.');
      return;
    }
    if (end < start) {
      setFormError('Дата окончания не может быть раньше даты начала.');
      return;
    }
    if (ownOverlap) {
      setFormError('Период пересекается с уже существующим отпуском.');
      return;
    }
    setSubmitting(true);
    try {
      const created = await createVacation({ start, end, type: PLANNED_TYPE, comment });
      setItems((prev) => [created, ...prev]);
      setStart('');
      setEnd('');
      setComment('');
      setCalendarTick((t) => t + 1);
      setFormOk(`Заявка №${created.id} отправлена на согласование.`);
    } catch (err) {
      setFormError(err instanceof Error ? err.message : 'Не удалось создать заявку.');
    } finally {
      setSubmitting(false);
    }
  }

  async function onDecision(id: number, action: 'approve' | 'reject') {
    setFormError(null);
    try {
      const updated = await decideVacation(id, action);
      setItems((prev) => prev.map((i) => (i.id === id ? updated : i)));
      setCalendarTick((t) => t + 1);
    } catch (err) {
      setFormError(err instanceof Error ? err.message : 'Не удалось сохранить решение.');
      reload();
    }
  }

  return (
    <div className="vc">
      <div className="vc-stats">
        <div className="vc-stat">
          <span className="vc-stat__value">{stats.total}</span>
          <span className="vc-stat__label">всего заявок</span>
        </div>
        <div className="vc-stat">
          <span className="vc-stat__value vc-stat__value--pending">{stats.pending}</span>
          <span className="vc-stat__label">на согласовании</span>
        </div>
        <div className="vc-stat">
          <span className="vc-stat__value vc-stat__value--ok">{stats.approvedDays}</span>
          <span className="vc-stat__label">дней согласовано</span>
        </div>
      </div>

      <section className="vc-card" aria-labelledby="vc-form-title">
        <h2 id="vc-form-title" className="vc-card__title">
          Новая заявка
        </h2>
        <form className="vc-form" onSubmit={onSubmit}>
          <label className="vc-field">
            <span className="vc-field__label">Начало</span>
            <span className="vc-date-wrap">
              <input
                type="date"
                className={start ? '' : 'vc-date-empty'}
                value={start}
                onChange={(e) => setStart(e.target.value)}
                required
                min="2027-01-01"
                max="2027-12-31"
              />
              {!start && <span className="vc-date-placeholder">Начало отпуска</span>}
            </span>
          </label>
          <label className="vc-field">
            <span className="vc-field__label">Конец</span>
            <span className="vc-date-wrap">
              <input type="date" className={end ? '' : 'vc-date-empty'} value={end} onChange={(e) => setEnd(e.target.value)} required min="2027-01-01" max="2027-12-31" />
              {!end && <span className="vc-date-placeholder">Конец отпуска</span>}
            </span>
          </label>
          <label className="vc-field vc-field--comment">
            <span className="vc-field__label">Комментарий</span>
            <textarea
              value={comment}
              onChange={(e) => setComment(e.target.value)}
              placeholder="Например: перенос с декабря"
              maxLength={200}
              rows={1}
            />
          </label>
          <div className="vc-form__actions">
            <button className="vc-btn" type="submit" disabled={submitting || !!ownOverlap}>
              {submitting ? 'Отправка…' : 'Отправить на согласование'}
            </button>
            <button className="vc-btn vc-btn--ghost" type="button" onClick={resetSelection}>
              Сбросить
            </button>
            {ownOverlap && (
              <span className="vc-msg vc-msg--error" role="alert">
                Период пересекается с уже существующим отпуском.
              </span>
            )}
            {deptOverlap && (
              <span className="vc-msg vc-msg--warn" role="status">
                В этот период отпуск уже запланирован у {deptOverlap.employee}. Решение примет руководитель.
              </span>
            )}
            {formError && (
              <span className="vc-msg vc-msg--error" role="alert">
                {formError}
              </span>
            )}
            {formOk && (
              <span className="vc-msg vc-msg--ok" role="status">
                {formOk}
              </span>
            )}
          </div>
        </form>
      </section>

      <section className="vc-card" aria-labelledby="vc-cal-title">
        <h2 id="vc-cal-title" className="vc-card__title">
          Календарь отпусков (отдел)
        </h2>
        <PaperCalendar2027
          refreshKey={calendarTick}
          selectedStart={selectedStart}
          selectedEnd={selectedEnd}
          onSelect={onSelectDate}
        />
        {selMsg && (
          <p className="vc-msg vc-msg--warn" role="alert">
            {selMsg}
          </p>
        )}
      </section>

      <section className="vc-card" aria-labelledby="vc-list-title">
        <div className="vc-card__head">
          <h2 id="vc-list-title" className="vc-card__title">
            Заявки
          </h2>
          <button className="vc-btn vc-btn--ghost" onClick={reload} type="button">
            Обновить
          </button>
        </div>

        {state === 'loading' && (
          <div className="vc-skeleton" aria-label="Загрузка">
            <span className="vc-skeleton__row" />
            <span className="vc-skeleton__row" />
            <span className="vc-skeleton__row" />
          </div>
        )}
        {state === 'error' && (
          <div className="vc-empty" role="alert">
            <p>API отпусков не отвечает.</p>
            <button className="vc-btn vc-btn--ghost" onClick={reload} type="button">
              Повторить
            </button>
          </div>
        )}
        {state === 'ready' && items.length === 0 && (
          <div className="vc-empty">
            <p>Заявок пока нет — создайте первую в форме выше.</p>
          </div>
        )}
        {state === 'ready' && items.length > 0 && (
          <table className="vc-table">
            <thead>
              <tr>
                <th>№</th>
                <th>Сотрудник</th>
                <th>Период</th>
                <th>Дни</th>
                <th>Статус</th>
                <th>Решение (HR)</th>
              </tr>
            </thead>
            <tbody>
              {(itemsExpanded ? items : items.slice(0, 5)).map((i) => (
                <tr key={i.id}>
                  <td className="vc-mono">{i.id}</td>
                  <td>{i.employee}</td>
                  <td className="vc-mono">
                    {fmtDate(i.start)} — {fmtDate(i.end)}
                  </td>
                  <td className="vc-mono">{i.days}</td>
                  <td>
                    <span className={`vc-pill ${STATUS_META[i.status].cls}`}>
                      <span className="vc-pill__dot" aria-hidden="true" />
                      {STATUS_META[i.status].label}
                    </span>
                  </td>
                  <td>
                    {i.status === 'pending' ? (
                      <span className="vc-actions">
                        <button
                          className="vc-btn vc-btn--mini"
                          onClick={() => onDecision(i.id, 'approve')}
                          type="button"
                        >
                          Согласовать
                        </button>
                        <button
                          className="vc-btn vc-btn--mini vc-btn--danger"
                          onClick={() => onDecision(i.id, 'reject')}
                          type="button"
                        >
                          Отклонить
                        </button>
                      </span>
                    ) : (
                      <span className="vc-mono vc-dim">—</span>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
        {state === 'ready' && items.length > 5 && (
          <button
            className="vc-btn vc-btn--ghost vc-table-toggle"
            type="button"
            onClick={() => setItemsExpanded((e) => !e)}
          >
            {itemsExpanded ? 'Скрыть' : 'Показать все'}
          </button>
        )}
      </section>
    </div>
  );
}

/* ===== Stub: оформить отпуск ===== */

function VacationsStub() {
  return (
    <div className="vc">
      <section className="vc-card">
        <h2 className="vc-card__title">Оформить отпуск</h2>
        <div className="vc-empty">
          <p>Функционал в разработке. Отдельный сервис.</p>
        </div>
      </section>
    </div>
  );
}
type ServiceKey = 'plan' | 'order';

const SERVICE_DEFS: { key: ServiceKey; title: string; desc: string; badge: string; badgeCls: string }[] = [
  { key: 'plan', title: 'Запланировать отпуск', desc: 'Планирование отпусков, календарь пересечений, заявки.', badge: 'Действует', badgeCls: 'vc-badge--ok' },
  { key: 'order', title: 'Оформить отпуск', desc: 'Оформление отпуска. Отдельный сервис (в разработке).', badge: 'В разработке', badgeCls: 'vc-badge--dev' },
];

export default function VacationsApp() {
  const [selectedService, setSelectedService] = useState<ServiceKey | null>(null);
  const [faqOpen, setFaqOpen] = useState(false);

  if (selectedService === 'plan') {
    return (
      <div className="vc">
        <div className="vc-header">
          <div className="vc-head-main">
            <button
              className="vc-back"
              type="button"
              onClick={() => setSelectedService(null)}
            >
              ← К выбору сервиса
            </button>
            <div>
              <div className="vc-title-row">
                <h1 className="vc-title">Запланировать отпуск</h1>
                <button
                  type="button"
                  className="vc-faq"
                  aria-label="FAQ Планирования отпусков"
                  aria-expanded={faqOpen}
                  onClick={() => setFaqOpen(true)}
                  onMouseEnter={() => setFaqOpen(true)}
                  onMouseLeave={() => setFaqOpen(false)}
                >
                  ?
                </button>
                {faqOpen && (
                  <div className="vc-faq-tip">
                    <div className="vc-faq-tip__title">FAQ Планирования отпусков:</div>
                    <ul className="vc-faq-tip__list">
                      <li>Посчитайте свои дни.</li>
                      <li>Обсудите с руководителем.</li>
                      <li>Решите, делить ли отпуск на части.</li>
                      <li>Учтите льготы.</li>
                    </ul>
                  </div>
                )}
              </div>
              <p className="vc-sub">Планирование отпусков, календарь пересечений, заявки</p>
            </div>
          </div>
          <span className="vc-ver">vacations@0.1.0</span>
        </div>
        <PlanVacations />
      </div>
    );
  }

  if (selectedService === 'order') {
    return (
      <div className="vc">
        <div className="vc-header">
          <div className="vc-head-main">
            <button
              className="vc-back"
              type="button"
              onClick={() => setSelectedService(null)}
            >
              ← К выбору сервиса
            </button>
            <div>
              <h1 className="vc-title">Оформить отпуск</h1>
              <p className="vc-sub">Оформление отпуска. Отдельный сервис (в разработке)</p>
            </div>
          </div>
          <span className="vc-ver">vacations@0.1.0</span>
        </div>
        <VacationsStub />
      </div>
    );
  }

  return (
    <div className="vc">
      <div className="vc-head">
        <div>
          <h1 className="vc-title">Отпуска</h1>
          <p className="vc-sub">
            Независимый микрофронтенд · деплоится отдельно от оболочки
          </p>
        </div>
      </div>

      <div className="vc-service-grid">
        {SERVICE_DEFS.map((svc) => (
          <div className="vc-service-card" key={svc.key}>
            <div className="vc-service-card__head">
              <h2 className="vc-service-card__title">{svc.title}</h2>
              <span className={`vc-badge ${svc.badgeCls}`}>{svc.badge}</span>
            </div>
            <p className="vc-service-card__desc">{svc.desc}</p>
            <button
              className="vc-service-card__cta vc-btn"
              type="button"
              onClick={() => setSelectedService(svc.key)}
            >
              Открыть →
            </button>
          </div>
        ))}
      </div>
    </div>
  );
}

