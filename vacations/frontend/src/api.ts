export type VacationStatus = 'pending' | 'approved' | 'rejected';
export type VacationType = 'annual' | 'unpaid' | 'study';

export interface VacationRequest {
  id: number;
  employee: string;
  start: string;
  end: string;
  days: number;
  type: VacationType;
  status: VacationStatus;
  comment: string;
  created_at: string;
}

export interface Overlap {
  employee_a: string;
  employee_b: string;
  start: string;
  end: string;
  days: number;
}

export interface Me {
  name: string;
  role: string;
  department: string;
}

export async function getMe(): Promise<Me> {
  const res = await fetch('/api/me');
  if (!res.ok) {
    throw new Error(`me: ${res.status}`);
  }
  return res.json();
}

export const TYPE_LABELS: Record<VacationType, string> = {
  annual: 'Ежегодный',
  unpaid: 'Без сохранения',
  study: 'Учебный',
};

export async function listVacations(): Promise<VacationRequest[]> {
  const res = await fetch('/api/vacations');
  if (!res.ok) throw new Error(`vacations: ${res.status}`);
  return res.json();
}

export async function createVacation(payload: {
  start: string;
  end: string;
  type: VacationType;
  comment: string;
}): Promise<VacationRequest> {
  const res = await fetch('/api/vacations', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(body.detail || `create: ${res.status}`);
  }
  return res.json();
}

export async function decideVacation(
  id: number,
  action: 'approve' | 'reject'
): Promise<VacationRequest> {
  const res = await fetch(`/api/vacations/${id}/decision`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ action }),
  });
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(body.detail || `decision: ${res.status}`);
  }
  return res.json();
}

export interface CalendarData {
  days: string[];
  employees: { name: string; days: string[] }[];
  conflict_days: string[];
}

export async function fetchDepartmentCalendar(
  start: string,
  months: number = 4
): Promise<CalendarData> {
  const res = await fetch(`/api/vacations/department/calendar?start=${start}&months=${months}`);
  if (!res.ok) throw new Error(`department/calendar: ${res.status}`);
  return res.json();
}

export async function fetchDepartment(): Promise<VacationRequest[]> {
  const res = await fetch('/api/vacations/department');
  if (!res.ok) throw new Error(`department: ${res.status}`);
  return res.json();
}
export async function fetchDepartmentOverlaps(): Promise<{
  vacations: VacationRequest[];
  overlaps: Overlap[];
}> {
  const res = await fetch('/api/vacations/department/overlaps');
  if (!res.ok) throw new Error(`department/overlaps: ${res.status}`);
  return res.json();
}
