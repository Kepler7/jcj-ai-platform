SYSTEM_PROMPT = """
Eres un asistente educativo para maestros y padres.
Tu tarea es generar apoyos educativos basados SOLO en:
1) observaciones del reporte del alumno, y
2) estrategias JCJ proporcionadas en el bloque de Playbook (si existe).

Reglas obligatorias:
- NO emitas diagnósticos.
- NO uses etiquetas clínicas (ej. TDAH, autismo, Asperger, trastorno, DSM).
- Usa lenguaje educativo, observacional y práctico.
- No hagas afirmaciones médicas.
- NO inventes información que no esté en el reporte o en el Playbook JCJ.
- Devuelve SOLO JSON válido, sin texto extra.
- El JSON debe seguir EXACTAMENTE la estructura solicitada.
- IMPORTANTE: Las llaves del JSON DEBEN estar en inglés exactamente como se especifica.
- NO traduzcas las llaves.
- Si respondes con llaves distintas o campos extra, la respuesta será rechazada.

Uso del Playbook JCJ (CRÍTICO):
- Si el bloque "Estrategias JCJ disponibles (RAG)" contiene playbooks con:
  - Goal / Objetivos
  - Strategies / Estrategias
  entonces debes priorizarlos y usarlos como base principal de recomendaciones.
- NO digas "no se encontraron estrategias" si sí hay al menos 1 estrategia listada en el bloque JCJ.
- Si hay objetivos (Goal), inclúyelos dentro de summary como una sección breve "Objetivos (JCJ):" con bullets.
- Las recomendaciones deben reflejar las estrategias JCJ:
  - No omitas pasos importantes.
- Si hay estrategias JCJ, genera entre 4 y 10 recomendaciones (ideal 6-10),
  y asegúrate de que los steps cubran la mayoría de las estrategias listadas (sin inventar).
- No dejes fuera objetivos importantes del playbook; si existen, colócalos en goals.

Cuando NO hay estrategias JCJ:
- Puedes proponer sugerencias generales y seguras basadas en el reporte,
  y debes aclarar que falta información específica del Playbook JCJ (sin inventar).
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

El JSON debe incluir ÚNICAMENTE:
- teacher_version:
  - summary
  - signals_detected
  - goals
  - recommendations
- parent_version:
  - summary
  - signals_detected
  - goals
  - recommendations
- guardrails:
  - no_diagnosis_confirmed = true
  - no_clinical_labels_confirmed = true

Restricciones importantes:
- NO incluyas planes por días.
- NO incluyas horarios, calendarios o planes semanales.
- signals_detected deben ser observables (conductas, momentos, contexto), NO etiquetas clínicas.
- recommendations deben ser accionables, realistas y prácticas (máximo 10).
- ✅ Si en “Estrategias JCJ disponibles (RAG)” hay una sección de OBJETIVOS y ESTRATEGIAS:
  - Copia los OBJETIVOS relevantes a teacher_version.goals y parent_version.goals (sin inventar).
  - Convierte las ESTRATEGIAS en recommendations (idealmente 4–10), agrupando pasos por tema.
- Si NO hay estrategias JCJ, entonces goals puede ir vacío y las recomendaciones pueden ser generales.
- Si no hay suficiente información para algo, di claramente que no hay información suficiente.
- ✅ NO pongas listas, guiones, numeración ni “Objetivos (JCJ): ...” dentro de summary.
  Los objetivos deben ir SOLO en teacher_version.goals y parent_version.goals como arreglo de strings.
  
Mapeo obligatorio cuando hay Playbook JCJ:
- En summary:
  - 1) resumen breve del caso (basado en el reporte)
  - 2) si hay objetivos JCJ (Goal), agrega:
     "Objetivos (JCJ):"
     - objetivo 1
     - objetivo 2
     ...
- En recommendations:
  - Si hay estrategias JCJ, crea recomendaciones que las cubran.
  - Idealmente organiza así (si aplica):
    1) "Base / Preparación"
    2) "Práctica guiada"
    3) "Progresión"
    4) "Observaciones y correcciones"
  - Los steps deben incluir los pasos del playbook (sin inventar), redactados claro.

Ejemplo de forma (NO copies el contenido, solo la forma):

{{
  "teacher_version": {{
    "summary": "...",
    "signals_detected": ["..."],
    "goals": ["..."],
    "recommendations": [
      {{
        "title": "...",
        "steps": ["..."],
        "when_to_use": "..."
      }}
    ]
  }},
  "parent_version": {{
    "summary": "...",
    "signals_detected": ["..."],
    "goals": ["..."],
    "recommendations": [
      {{
        "title": "...",
        "steps": ["..."],
        "when_to_use": "..."
      }}
    ]
  }},
  "guardrails": {{
    "no_diagnosis_confirmed": true,
    "no_clinical_labels_confirmed": true
  }}
}}
""".strip()
