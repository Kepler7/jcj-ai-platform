from __future__ import annotations

import json
import hashlib
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import urlparse

import pandas as pd


def is_url(value: str) -> bool:
    parsed = urlparse(value)
    return parsed.scheme in ("http", "https") and bool(parsed.netloc)


def load_csv_source(input_source: str) -> pd.DataFrame:
    """
    Load a CSV from either:
    - a local filesystem path
    - an HTTP/HTTPS URL (e.g. Google Sheets CSV export URL)
    """
    if is_url(input_source):
        return pd.read_csv(input_source)

    path = Path(input_source)
    if not path.exists():
        raise FileNotFoundError(f"Input CSV not found: {input_source}")

    return pd.read_csv(path)


def _s(x: Any) -> str:
    if x is None:
        return ""
    if isinstance(x, float) and pd.isna(x):
        return ""
    return str(x).strip()


def _norm_header(h: str) -> str:
    h = (h or "").replace("\ufeff", "")
    h = h.strip().lower()
    h = re.sub(r"\s+", " ", h)
    return h


def parse_int(x: Any, field: str, errors: List[str]) -> Optional[int]:
    s = _s(x)
    if not s:
        errors.append(f"Missing {field}")
        return None
    m = re.findall(r"-?\d+", s)
    if not m:
        errors.append(f"Invalid int for {field}: {s}")
        return None
    try:
        return int(m[0])
    except Exception:
        errors.append(f"Invalid int for {field}: {s}")
        return None


def split_steps(raw: Any) -> List[str]:
    s = _s(raw)
    if not s:
        return []

    s = s.strip().strip('"').strip("'")
    s = s.replace("\r\n", "\n").replace("\r", "\n")
    s = re.sub(r"[ \t]+", " ", s)

    numbered = re.split(r"(?:^|\n)\s*\d+\s*[\.\)\-]\s*", s)
    if len(numbered) > 1:
        return [x.strip(" \n\t-") for x in numbered if x.strip()]

    bullets = re.split(r"(?:^|\n)\s*[-•]\s*", s)
    if len(bullets) > 1:
        return [x.strip(" \n\t-") for x in bullets if x.strip()]

    lines = [ln.strip(" \t-") for ln in s.split("\n") if ln.strip()]
    if len(lines) > 1:
        return lines

    return [s]


def dedupe_keep_order(items: List[str]) -> List[str]:
    seen = set()
    out = []
    for it in items:
        k = (it or "").strip().lower()
        if not k:
            continue
        if k in seen:
            continue
        seen.add(k)
        out.append(it.strip())
    return out


def make_hash_id(obj: Dict[str, Any]) -> str:
    stable = {
        "topic_nucleo": obj.get("topic_nucleo"),
        "subskill": obj.get("subskill"),
        "signal_observable": obj.get("signal_observable"),
        "age_min": obj.get("age_min"),
        "age_max": obj.get("age_max"),
        "functional_hypothesis": obj.get("functional_hypothesis"),
        "micro_objective": obj.get("micro_objective"),
        "steps": obj.get("steps"),
        "frequency": obj.get("frequency"),
        "duration": obj.get("duration"),
        "progress_indicator": obj.get("progress_indicator"),
        "escalation": obj.get("escalation"),
    }
    raw = json.dumps(stable, ensure_ascii=False, sort_keys=True)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def pick_col(df_cols: List[str], aliases: List[str]) -> Optional[str]:
    if not df_cols:
        return None

    norm_map = {_norm_header(c): c for c in df_cols}
    for a in aliases:
        na = _norm_header(a)
        if na in norm_map:
            return norm_map[na]
    return None


ALIASES: Dict[str, List[str]] = {
    "topic_nucleo": [
        "topic nucleo",
        "topic NUCLEO",
        "núcleo",
        "nucleo",
        "topic",
        "topic_nucleo",
    ],
    "subskill": [
        "subhabilidad",
        "sub habilidad",
        "sub-skill",
        "subskill",
    ],
    "signal_observable": [
        "señal observable",
        "senal observable",
        "señal",
        "senal",
    ],
    "age_min": [
        "age min esperado",
        "edad min esperado",
        "edad mínima",
        "age_min",
        "age min",
    ],
    "age_max": [
        "age max esperado",
        "edad max esperado",
        "edad máxima",
        "age_max",
        "age max",
    ],
    "functional_hypothesis": [
        "hipotesis funcional",
        "hipótesis funcional",
        "hipotesis",
        "hipótesis",
        "hipotesis funcional ",
    ],
    "micro_objective": [
        "microobjetivo",
        "micro objetivo",
        "micro-objetivo",
    ],
    "steps_raw": [
        "estrategias paso a paso",
        "estrategia paso a paso",
        "paso a paso",
        "estrategias",
    ],
    "frequency": [
        "frecuencia",
        "fracuencia",
        "frequency",
    ],
    "duration": [
        "duracion",
        "duración",
        "duration",
    ],
    "progress_indicator": [
        "indicador de avance",
        "indicador",
        "indicador avance",
    ],
    "escalation": [
        "escalamiento",
        "escalamiento ",
        "escalation",
    ],
}

REQUIRED_KEYS = [
    "topic_nucleo",
    "subskill",
    "signal_observable",
    "age_min",
    "age_max",
    "functional_hypothesis",
    "micro_objective",
    "steps_raw",
    "frequency",
    "duration",
    "progress_indicator",
    "escalation",
]


def normalize_csv(input_source: str, output_jsonl: Path) -> None:
    df = load_csv_source(input_source)

    col_map: Dict[str, Optional[str]] = {
        key: pick_col(list(df.columns), aliases) for key, aliases in ALIASES.items()
    }

    missing = [k for k in REQUIRED_KEYS if not col_map.get(k)]
    if missing:
        found = "\n- ".join([str(c) for c in df.columns])
        raise RuntimeError(
            "Missing required columns (by key): "
            + ", ".join(missing)
            + "\nFound columns:\n- "
            + found
        )

    print("Resolved columns:")
    for k in REQUIRED_KEYS:
        print(f"  {k} -> {col_map[k]}")

    output_jsonl.parent.mkdir(parents=True, exist_ok=True)

    ok_rows = 0
    bad_rows = 0
    error_samples: List[Tuple[int, List[str]]] = []

    with output_jsonl.open("w", encoding="utf-8") as f:
        for idx, row in df.iterrows():
            errors: List[str] = []

            topic_nucleo = _s(row.get(col_map["topic_nucleo"]))
            subskill = _s(row.get(col_map["subskill"]))
            signal_observable = _s(row.get(col_map["signal_observable"]))
            functional_hypothesis = _s(row.get(col_map["functional_hypothesis"]))
            micro_objective = _s(row.get(col_map["micro_objective"]))
            frequency = _s(row.get(col_map["frequency"]))
            duration = _s(row.get(col_map["duration"]))
            progress_indicator = _s(row.get(col_map["progress_indicator"]))
            escalation = _s(row.get(col_map["escalation"]))

            if not topic_nucleo:
                errors.append("Missing topic_nucleo")
            if not subskill:
                errors.append("Missing subskill")
            if not signal_observable:
                errors.append("Missing signal_observable")
            if not functional_hypothesis:
                errors.append("Missing functional_hypothesis")
            if not micro_objective:
                errors.append("Missing micro_objective")
            if not frequency:
                errors.append("Missing frequency")
            if not duration:
                errors.append("Missing duration")
            if not progress_indicator:
                errors.append("Missing progress_indicator")
            if not escalation:
                errors.append("Missing escalation")

            age_min = parse_int(row.get(col_map["age_min"]), "age_min", errors)
            age_max = parse_int(row.get(col_map["age_max"]), "age_max", errors)

            if age_min is not None and age_max is not None and age_max < age_min:
                errors.append(f"age_max < age_min ({age_max} < {age_min})")

            steps = dedupe_keep_order(split_steps(row.get(col_map["steps_raw"])))

            if not steps:
                errors.append("Missing steps (estrategias paso a paso)")

            if errors:
                bad_rows += 1
                if len(error_samples) < 10:
                    error_samples.append((idx + 2, errors))
                continue

            obj: Dict[str, Any] = {
                "base_row": str(idx + 2),
                "source": "sheet",
                "topic_nucleo": topic_nucleo,
                "subskill": subskill,
                "signal_observable": signal_observable,
                "age_min": int(age_min),
                "age_max": int(age_max),
                "functional_hypothesis": functional_hypothesis,
                "micro_objective": micro_objective,
                "steps": steps,
                "frequency": frequency,
                "duration": duration,
                "progress_indicator": progress_indicator,
                "escalation": escalation,
            }

            obj["id"] = make_hash_id(obj)

            f.write(json.dumps(obj, ensure_ascii=False) + "\n")
            ok_rows += 1

    print(f"✅ Wrote {ok_rows} normalized rows to: {output_jsonl}")
    if bad_rows:
        print(f"⚠️ Skipped {bad_rows} rows with errors.")
        for line_no, errs in error_samples:
            print(f"  - Row {line_no}: {', '.join(errs)}")
