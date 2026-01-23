SYSTEM_PROMPT = """
Eres un asistente educativo para maestros y padres.
Tu tarea es generar apoyos educativos basados SOLO en observaciones del reporte del alumno.

Reglas obligatorias:
- NO emitas diagnósticos.
- NO uses etiquetas clínicas (ej. TDAH, autismo, Asperger, trastorno, DSM).
- Usa lenguaje educativo, observacional y práctico.
- No hagas afirmaciones médicas.
- Devuelve SOLO JSON válido, sin texto extra.
- El JSON debe seguir EXACTAMENTE la estructura solicitada.
- IMPORTANTE: Las llaves del JSON DEBEN estar en inglés exactamente como se especifica (teacher_version.summary, signals_detected, recommendations, classroom_plan_7_days, etc.).
- NO traduzcas las llaves.
- Si respondes con llaves distintas, la respuesta será rechazada.
"""

def build_user_prompt(student_name: str, age: int, group: str, report_text: str) -> str:
    return f"""
Alumno: {student_name}
Edad: {age}
Grupo: {group}

Reporte (observaciones):
{report_text}

Tarea:
Devuelve SOLO un objeto JSON válido (sin markdown, sin ```json, sin texto extra).
Las llaves del JSON DEBEN estar en INGLÉS y EXACTAMENTE como en el ejemplo.
NO traduzcas las llaves.

El JSON debe incluir:
- teacher_version: summary, signals_detected, recommendations, classroom_plan_7_days
- parent_version: el nombre {student_name}, summary, signals_detected, recommendations, home_plan_7_days
- guardrails: no_diagnosis_confirmed=true y no_clinical_labels_confirmed=true

Asegúrate de que:
- signals_detected sean observables (conductas, momentos, contexto), no etiquetas clínicas.
- recommendations sean accionables y realistas (máximo 6).
- Los planes de 7 días tengan day 1..7.

Ejemplo de forma (NO copies el contenido, solo la forma):
{{
  "teacher_version": {{
    "summary": "...",
    "signals_detected": ["..."],
    "recommendations": [{{"title":"...","steps":["..."],"when_to_use":"..."}}],
    "classroom_plan_7_days": [{{"day": 1, "focus":"...","activity":"...","success_criteria":"..."}}]
  }},
  "parent_version": {{
    "summary": "...",
    "signals_detected": ["..."],
    "recommendations": [{{"title":"...","steps":["..."],"when_to_use":"..."}}],
    "home_plan_7_days": [{{"day": 1, "focus":"...","activity":"...","success_criteria":"..."}}]
  }},
  "guardrails": {{
    "no_diagnosis_confirmed": true,
    "no_clinical_labels_confirmed": true
  }}
}}
""".strip()

