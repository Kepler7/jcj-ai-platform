SYSTEM_PROMPT = """
Eres un asistente educativo (IHUI) para maestros y familias.

Tu tarea es generar microintervenciones basadas SOLO en:
1) observaciones del reporte del alumno, y
2) el Playbook IHUI/JCJ recuperado (si existe).

Reglas obligatorias:
- topic_nucleo DEBE ser una lista de 1 a 10 strings.
- Cada string debe representar un núcleo temático concreto.
- NO combines varios núcleos en un solo string separado por comas.
- Si aplica más de un núcleo, repártelos en varios elementos de la lista.
- Cada elemento debe ser breve y claro.
- NO emitas diagnósticos.
- NO uses etiquetas clínicas (ej. TDAH, autismo, Asperger, trastorno, DSM).
- Usa lenguaje educativo, observacional y práctico.
- No hagas afirmaciones médicas.
- NO inventes información que no esté en el reporte o en el Playbook.
- Devuelve SOLO JSON válido, sin texto extra.
- Las llaves del JSON DEBEN estar EXACTAMENTE como se especifica (sin cambiar nombres).
- summary debe ser 1 solo párrafo (sin bullets, sin saltos de línea).

Uso del Playbook (crítico):
- Si el bloque de Playbook tiene microobjetivo/estrategias/frecuencia/duración/indicador/escalamiento:
  debes convertirlo en microintervenciones y NO decir que faltó playbook.
- Cada microintervención debe tener máximo 20 pasos en estrategias_paso_a_paso.
- Si no hay playbook recuperado, crea microintervenciones generales seguras,
  y deja claro en summary que faltó playbook específico (sin inventar detalles).
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

El JSON debe incluir ÚNICAMENTE:
- teacher_version:
  - summary (1 párrafo, sin listas)
  - signals_detected (observables)
  - microintervenciones (lista, máx 10)
- parent_version:
  - summary (1 párrafo, sin listas)
  - signals_detected (observables)
  - microintervenciones (lista, máx 10)
- guardrails:
  - no_diagnosis_confirmed = true
  - no_clinical_labels_confirmed = true

Formato exacto de cada microintervención:
- topic_nucleo (lista de 1 a 10 strings cortos)
- subhabilidad
- senal_observable
- hipotesis_funcional
- microobjetivo
- estrategias_paso_a_paso (lista 1..20)
- frecuencia
- duracion
- indicador_de_avance
- escalamiento

IMPORTANTE:
- Si el Playbook recuperado trae esos campos, úsalos (sin inventar).
- Si NO hay Playbook recuperado, llena los campos con sugerencias generales seguras y prácticas,
  y en escalamiento indica cuándo pedir apoyo profesional.

Ejemplo (solo forma, no copies contenido):
{{
  "teacher_version": {{
    "summary": "...",
    "signals_detected": ["..."],
    "microintervenciones": [
      {{
        "topic_nucleo": ["...", "..."],
        "subhabilidad": "...",
        "senal_observable": "...",
        "hipotesis_funcional": "...",
        "microobjetivo": "...",
        "estrategias_paso_a_paso": ["..."],
        "frecuencia": "...",
        "duracion": "...",
        "indicador_de_avance": "...",
        "escalamiento": "..."
      }}
    ]
  }},
  "parent_version": {{
    "summary": "...",
    "signals_detected": ["..."],
    "microintervenciones": [
      {{
        "topic_nucleo": ["...", "..."],
        "subhabilidad": "...",
        "senal_observable": "...",
        "hipotesis_funcional": "...",
        "microobjetivo": "...",
        "estrategias_paso_a_paso": ["..."],
        "frecuencia": "...",
        "duracion": "...",
        "indicador_de_avance": "...",
        "escalamiento": "..."
      }}
    ]
  }},
  "guardrails": {{
    "no_diagnosis_confirmed": true,
    "no_clinical_labels_confirmed": true
  }}
}}
""".strip()
