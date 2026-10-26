from datetime import date


def _as_date(v):
    """Принимает date или ISO-строку 'YYYY-MM-DD' (данные из БД приходят date-объектами)."""
    return v if isinstance(v, date) else date.fromisoformat(v)


def find_overlaps(vacations: list[dict]) -> list[dict]:
    """Find pairwise vacation overlaps between different employees.

    Одинаковые (employee, start, end) записи учитываются один раз — иначе дубли
    накопившихся записей дают дублирующиеся пересечения.
    """
    seen = set()
    unique = []
    for v in vacations:
        key = (v["employee"], _as_date(v["start"]).isoformat(), _as_date(v["end"]).isoformat())
        if key not in seen:
            seen.add(key)
            unique.append(v)
    vacations = unique

    result: list[dict] = []
    for i in range(len(vacations)):
        for j in range(i + 1, len(vacations)):
            a, b = vacations[i], vacations[j]
            if a["employee"] == b["employee"]:
                continue

            start_a = _as_date(a["start"])
            end_a = _as_date(a["end"])
            start_b = _as_date(b["start"])
            end_b = _as_date(b["end"])

            if start_a <= end_b and start_b <= end_a:
                s = max(start_a, start_b)
                e = min(end_a, end_b)
                days = (e - s).days + 1

                ea, eb = (a["employee"], b["employee"]) if a["employee"] <= b["employee"] else (b["employee"], a["employee"])
                result.append({
                    "employee_a": ea,
                    "employee_b": eb,
                    "start": s.isoformat(),
                    "end": e.isoformat(),
                    "days": days,
                })
    return result
