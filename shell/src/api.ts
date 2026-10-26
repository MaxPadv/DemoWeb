export interface HrService {
  key: string;
  title: string;
  description: string;
  status: 'active' | 'planned';
  version?: string;
  remote?: { name: string; entry: string; module: string };
}

export interface CurrentUser {
  name: string;
  role: string;
  department: string;
}

export async function fetchServices(): Promise<HrService[]> {
  const res = await fetch('/api/services');
  if (!res.ok) throw new Error(`services: ${res.status}`);
  return res.json();
}

export async function fetchMe(): Promise<CurrentUser> {
  const res = await fetch('/api/me');
  if (!res.ok) throw new Error(`me: ${res.status}`);
  return res.json();
}

export async function logout(): Promise<void> {
  await fetch('/api/auth/logout', { method: 'POST' });
}
