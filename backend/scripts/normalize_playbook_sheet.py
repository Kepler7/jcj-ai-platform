import re
import json
import hashlib
from pathlib import Path
from typing import Any, Dict, List, Optional

import pandas as pd


TOPIC_ALLOWED = {
    "Lenguaje/Pronunciacion",
    "Atencion concentracion",
    "Estimulacion Cognitiva",
    "Conducta/Autorregulacion",
    "Regulacion emocional",
    "Habilidades sociales",
    "Motricidad fina",
    "Autonomia y habitos",
    "Regularizacion",
}

CONTEXT_MAP = {
    "casa": ["casa"],
    "aula": ["aula"],
    "otro contexto social": ["otro_contexto_social"],
    "en todas las anteriores": ["casa", "aula", "otro_contexto_social"],
}


def _s(x: Any) -> str:
    return "" if x is None or (isinstance(x, float) and pd.isna(x)) else str(x).strip()


def parse_int(x: Any, field: str, errors: List[str]) -> Optional[int]:
    s = _s(x)
    if not s:
        errors.append(f"Missing {field}")
        return None
    try:
        return int(re.findall(r"-?\d+", s)[0])
    except Exception:
        errors.append(f"Invalid int for {field}: {s}")
        return None


def parse_contexts(raw: Any, errors: List[str]) -> List[str]:
    key = _s(raw).lower()
    if not key:
        errors.append("Missing Contexto")
        return []
    if key not in CONTEXT_MAP:
        errors.append(f"Invalid Contexto: {raw}")
        return []
    return CONTEXT_MAP[key]


EMOJI_RE = re.compile(
    "["
    "\U0001F600-\U0001F64F"
    "\U0001F300-\U0001F5FF"
    "\U0001F680-\U0001F6FF"
    "\U0001F1E0-\U0001F1FF"
    "]+",
    flags=re.UNICODE,
)


def parse_tags_emotion(raw: Any) -> List[str]:
    s = _s(raw)
    if not s:
        return []
    s = EMOJI_RE.sub("", s)
    # Ej: "Positivo/Feliz/firme" -> ["positivo","feliz","firme"]
    s = s.replace("—", " ").replace("-", " ")
    parts = re.split(r"[/,;|]+", s)
    cleaned: List[str] = []
    for p in parts:
        p = p.strip().lower()
        if p:
            cleaned.append(p)
    return cleaned


def split_steps(raw: Any) -> List[str]:
    s = _s(raw)
    if not s:
        return []
    s = s.strip().strip('"').strip("'")

    # Normaliza saltos
    s = s.replace("\r\n", "\n").replace("\r", "\n")

    # Si trae numeración 1. 2. 3.
    numbered = re.split(r"\n?\s*\d+\s*[.)]\s*", s)
    if len(numbered) > 1:
        out = [x.strip(" -\n\t") for x in numbered if x.strip()]
        return out

    # Si trae bullets -
    bullets = re.split(r"\n\s*-\s*", s)
    if len(bullets) > 1:
        out = [x.strip(" -\n\t") for x in bullets if x.strip()]
        return out

    # Fallback: líneas no vacías
    lines = [ln.strip() for ln in s.split("\n") if ln.strip()]
    return lines if len(lines) > 1 else [s]


def make_hash_id(obj: Dict[str, Any]) -> str:
    stable = {
        "problem_title": obj.get("problem_title"),
        "age_min": obj.get("age_min"),
        "age_max": obj.get("age_max"),
        "topic_nucleo": obj.get("topic_nucleo"),
        "contexts": obj.get("contexts"),
        "goal": obj.get("goal"),
        "strategies": obj.get("strategies"),
    }
    raw = json.dumps(stable, ensure_ascii=False, sort_keys=True)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def normalize_csv(input_csv: Path, output_jsonl: Path) -> None:
    df = pd.read_csv(input_csv)

    # ---------------------------
    # Column alias resolution
    # ---------------------------
    ALIASES = {
        # Opcionales
        "base_row": ["Organigrama=base.row", "base.row", "base_row", "organigrama", "organigrama=base.row"],
        "raw_id_name": ["id/ nombre", "id/nombre", "id", "nombre"],

        # Requeridas MVP
        "problem_title": ["titulo/ problema", "título/ problema", "titulo/problema", "título/problema", "titulo", "problema", "titulo problema"],
        "age_min": ["age min esperado", "edad min esperado", "edad min", "age_min", "age min"],
        # age_max NO requerida
        "age_max": ["age max esperado", "edad max esperado", "edad max", "age_max", "age max"],
        "topic": ["topic NUCLEO", "topic nucleo", "topic", "nucleo", "núcleo"],
        "context": ["Contexto", "contexto"],
        "behavior": ["Como se comporta al respecto", "Cómo se comporta al respecto", "comportamiento", "como se comporta", "conducta observada"],
        "goal": ["Que se espera lograr", "Qué se espera lograr", "objetivo", "meta", "se espera lograr"],
        "strategies_1": ["Estrategias para lograrlo", "estrategias", "estrategias para lograr", "estrategias #1"],

        # Opcionales
        "tags_emotion": ["Tags/ emoción", "tags/emoción", "tags", "emocion", "emoción", "tags emoción"],
        "strategies_2": ["#2", "Estrategias #2", "estrategias 2", "estrategias_2"],
        "constraints": ["Notas/Reglas", "reglas", "notas", "restricciones"],
        "extra_notes": ["Observaciones extra", "observaciones", "notas extra"],
    }

    def pick_col(df_cols, keys):
        cols_lower = {c.lower(): c for c in df_cols}
        for k in keys:
            if k in df_cols:
                return k
            lk = k.lower()
            if lk in cols_lower:
                return cols_lower[lk]
        return None

    COL = {key: pick_col(df.columns, aliases) for key, aliases in ALIASES.items()}

    # Requeridas mínimas
    required_keys = ["problem_title", "age_min", "topic", "context", "behavior", "goal", "strategies_1"]
    missing_keys = [k for k in required_keys if COL.get(k) is None]
    if missing_keys:
        raise RuntimeError(
            "Missing required columns (by key): "
            + ", ".join(missing_keys)
            + "\n\nFound columns:\n- "
            + "\n- ".join(df.columns)
        )

    print("Resolved columns:")
    for k, v in COL.items():
        if v:
            print(f"  {k} -> {v}")

    out: List[Dict[str, Any]] = []
    row_errors: List[Dict[str, Any]] = []

    for idx, row in df.iterrows():
        errors: List[str] = []

        base_row = _s(row.get(COL["base_row"])) if COL.get("base_row") else str(idx + 1)
        raw_id_name = _s(row.get(COL["raw_id_name"])) if COL.get("raw_id_name") else ""

        problem_title = _s(row.get(COL["problem_title"]))
        if not problem_title:
            errors.append("Missing problem title")

        age_min = parse_int(row.get(COL["age_min"]), "age min esperado", errors)

        # age_max opcional: si falta, iguala age_min (y si age_min es None, queda None)
        if COL.get("age_max"):
            age_max = parse_int(row.get(COL["age_max"]), "age max esperado", errors)
        else:
            age_max = age_min

        topic = _s(row.get(COL["topic"]))
        if not topic:
            errors.append("Missing topic NUCLEO")
        elif topic not in TOPIC_ALLOWED:
            errors.append(f"Invalid topic NUCLEO: {topic}")

        contexts = parse_contexts(row.get(COL["context"]), errors)

        tags = parse_tags_emotion(row.get(COL["tags_emotion"])) if COL.get("tags_emotion") else []

        behavior = _s(row.get(COL["behavior"]))
        if not behavior:
            errors.append("Missing behavior")

        goal = split_steps(row.get(COL["goal"]))

        strategies_1 = split_steps(row.get(COL["strategies_1"]))
        strategies_2 = split_steps(row.get(COL["strategies_2"])) if COL.get("strategies_2") else []

        strategies = [*strategies_1, *strategies_2]
        if not strategies:
            errors.append("Missing strategies")

        constraints = split_steps(row.get(COL["constraints"])) if COL.get("constraints") else []
        extra_notes = _s(row.get(COL["extra_notes"])) if COL.get("extra_notes") else ""

        # Si hay errores críticos, guardamos el error y saltamos
        if errors:
            row_errors.append(
                {
                    "row_index": int(idx),
                    "base_row": base_row,
                    "raw_id_name": raw_id_name,
                    "problem_title": problem_title,
                    "errors": errors,
                }
            )
            continue

        obj: Dict[str, Any] = {
            "base_row": base_row,
            "raw_id_name": raw_id_name,
            "problem_title": problem_title,
            "age_min": age_min,
            "age_max": age_max,
            "topic_nucleo": topic,
            "contexts": contexts,
            "tags": tags,
            "behavior": behavior,
            "goal": goal,
            "strategies": strategies,
            "constraints": constraints,
            "extra_notes": extra_notes,
        }

        obj["id"] = make_hash_id(obj)
        out.append(obj)

    # Escribir JSONL
    output_jsonl.parent.mkdir(parents=True, exist_ok=True)
    with output_jsonl.open("w", encoding="utf-8") as f:
        for obj in out:
            f.write(json.dumps(obj, ensure_ascii=False) + "\n")

    # Resumen
    print(f"\n✅ Wrote {len(out)} normalized rows to: {output_jsonl}")
    if row_errors:
        print(f"⚠️  Skipped {len(row_errors)} rows with errors.")
        # imprime primeras 10
        for e in row_errors[:10]:
            print(f"- row_index={e['row_index']} base_row={e['base_row']} errors={e['errors']}")

        # también guarda un archivo de errores al lado
        err_path = output_jsonl.with_suffix(".errors.json")
        with err_path.open("w", encoding="utf-8") as ef:
            json.dump(row_errors, ef, ensure_ascii=False, indent=2)
        print(f"🧾 Errors saved to: {err_path}")


if __name__ == "__main__":
    import argparse

    ap = argparse.ArgumentParser()
    ap.add_argument("--input", required=True, help="Path to CSV exported from Google Sheet")
    ap.add_argument("--output", required=True, help="Path to output JSONL")
    args = ap.parse_args()

    normalize_csv(Path(args.input), Path(args.output))

