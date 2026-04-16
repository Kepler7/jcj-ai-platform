from typing import Any, List


def normalize_topic_nucleo(value: Any) -> List[str]:
    if value is None:
        return []

    items: List[str] = []

    if isinstance(value, list):
        items = [str(x).strip() for x in value]

    elif isinstance(value, str):
        raw = value.strip()
        if not raw:
            return []

        items = [p.strip() for p in raw.split(",")]

    else:
        s = str(value).strip()
        items = [s] if s else []

    seen = set()
    result: List[str] = []

    for item in items:
        if not item:
            continue

        key = item.lower()
        if key in seen:
            continue

        seen.add(key)
        result.append(item)

        if len(result) >= 10:
            break

    return result
