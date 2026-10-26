export interface Employee {
  id: number;
  name: string;
  position: string;
  department: string;
  manager_id: number | null;
}

export async function listStructure(): Promise<Employee[]> {
  const res = await fetch('/api/structure');
  if (!res.ok) throw new Error(`structure: ${res.status}`);
  return res.json();
}
