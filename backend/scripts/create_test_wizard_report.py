from uuid import uuid4
import json

from sqlalchemy import text

from app.db.db import SessionLocal


"""
Este script crea ai_report_id real que tenga wizard_required = true
para ejecutarlo en docker:
docker compose -f docker-compose.dev.yml exec backend \
sh -lc "PYTHONPATH=. python scripts/create_test_wizard_report.py"
"""


def main():
    db = SessionLocal()

    try:
        ai_report_id = uuid4()
        existing_report = (
            db.execute(
                text(
                    """
                SELECT
                    id,
                    school_id,
                    student_id
                FROM student_reports
                ORDER BY created_at DESC
                LIMIT 1
                """
                )
            )
            .mappings()
            .first()
        )

        if not existing_report:
            raise RuntimeError(
                "No hay student_reports en la base local. Crea primero un reporte de maestro desde la UI."
            )

        report_id = existing_report["id"]
        school_id = existing_report["school_id"]
        student_id = existing_report["student_id"]

        metadata = {
            "engine_version": "ihui_3",
            "wizard_required": True,
            "fallback_used": False,
            "review_status": "pending_validation",
            "validation_status": "needs_validation_answers",
            "query_text": (
                "El alumno se distrae rápido, necesita recordatorios frecuentes "
                "y también requiere que se le repitan instrucciones."
            ),
            "ihui3_wizard_candidates": [
                {
                    "playbook_id": "51",
                    "nucleus": "Atención",
                    "subskill": "Permanencia en tarea",
                    "score": 0.82,
                    "matched_terms": [
                        "se distrae rápido",
                        "necesita recordatorios frecuentes",
                    ],
                    "reason": "Candidato de prueba 51",
                    "validation_questions": [
                        "¿Le cuesta mantenerse en la actividad sin recordatorios?",
                        "¿Necesita pausas breves para volver a enfocarse?",
                    ],
                    "micro_objective": "Aumentar la permanencia en tarea.",
                    "strategy_steps": [
                        "Dar una instrucción breve y concreta.",
                        "Usar pausas cortas antes de retomar la actividad.",
                    ],
                    "frequency": "Diaria",
                    "duration": "10 minutos",
                    "progress_indicator": (
                        "Permanece más tiempo en la actividad con menos recordatorios."
                    ),
                    "escalation": "Si no hay mejora, revisar con especialista.",
                },
                {
                    "playbook_id": "52",
                    "nucleus": "Comprensión",
                    "subskill": "Seguimiento de instrucciones",
                    "score": 0.79,
                    "matched_terms": [
                        "requiere que se le repitan instrucciones",
                    ],
                    "reason": "Candidato de prueba 52",
                    "validation_questions": [
                        "¿Mejora cuando se le explica individualmente?",
                        "¿Necesita que se le repita la instrucción más de una vez?",
                    ],
                    "micro_objective": "Mejorar el seguimiento de instrucciones.",
                    "strategy_steps": [
                        "Dividir la instrucción en pasos pequeños.",
                        "Pedirle que repita con sus palabras lo que debe hacer.",
                    ],
                    "frequency": "Diaria",
                    "duration": "10 minutos",
                    "progress_indicator": (
                        "Sigue instrucciones con menos apoyo adulto."
                    ),
                    "escalation": "Si persiste la dificultad, validar con especialista.",
                },
            ],
            "ihui3_wizard_questions": [
                {
                    "playbook_id": "51",
                    "nucleus": "Atención",
                    "subskill": "Permanencia en tarea",
                    "question_id": "51-q1",
                    "text": "¿Le cuesta mantenerse en la actividad sin recordatorios?",
                },
                {
                    "playbook_id": "51",
                    "nucleus": "Atención",
                    "subskill": "Permanencia en tarea",
                    "question_id": "51-q2",
                    "text": "¿Necesita pausas breves para volver a enfocarse?",
                },
                {
                    "playbook_id": "52",
                    "nucleus": "Comprensión",
                    "subskill": "Seguimiento de instrucciones",
                    "question_id": "52-q1",
                    "text": "¿Mejora cuando se le explica individualmente?",
                },
                {
                    "playbook_id": "52",
                    "nucleus": "Comprensión",
                    "subskill": "Seguimiento de instrucciones",
                    "question_id": "52-q2",
                    "text": "¿Necesita que se le repita la instrucción más de una vez?",
                },
            ],
            "wizard": {
                "questions": [
                    {
                        "playbook_id": "51",
                        "nucleus": "Atención",
                        "subskill": "Permanencia en tarea",
                        "question_id": "51-q1",
                        "text": "¿Le cuesta mantenerse en la actividad sin recordatorios?",
                    },
                    {
                        "playbook_id": "51",
                        "nucleus": "Atención",
                        "subskill": "Permanencia en tarea",
                        "question_id": "51-q2",
                        "text": "¿Necesita pausas breves para volver a enfocarse?",
                    },
                    {
                        "playbook_id": "52",
                        "nucleus": "Comprensión",
                        "subskill": "Seguimiento de instrucciones",
                        "question_id": "52-q1",
                        "text": "¿Mejora cuando se le explica individualmente?",
                    },
                    {
                        "playbook_id": "52",
                        "nucleus": "Comprensión",
                        "subskill": "Seguimiento de instrucciones",
                        "question_id": "52-q2",
                        "text": "¿Necesita que se le repita la instrucción más de una vez?",
                    },
                ],
                "allowed_answers": ["yes", "no", "sometimes"],
            },
            "ihui3_match": {
                "playbook_id": "51",
                "nucleus": "Atención",
                "subskill": "Permanencia en tarea",
                "score": 0.82,
                "matched_terms": [
                    "se distrae rápido",
                    "necesita recordatorios frecuentes",
                ],
                "reason": "Candidato inicial de prueba.",
            },
            "ihui3_strategy": {
                "micro_objective": "Aumentar la permanencia en tarea.",
                "steps": [
                    "Dar una instrucción breve y concreta.",
                    "Usar pausas cortas antes de retomar la actividad.",
                ],
                "frequency": "Diaria",
                "duration": "10 minutos",
                "progress_indicator": (
                    "Permanece más tiempo en la actividad con menos recordatorios."
                ),
                "escalation": "Si no hay mejora, revisar con especialista.",
                "status": "requires_validation",
            },
        }

        db.execute(
            text(
                """
                INSERT INTO ai_reports (
                    id,
                    school_id,
                    student_id,
                    report_id,
                    model_name,
                    teacher_version,
                    parent_version,
                    signals_detected,
                    guardrails_passed,
                    guardrails_notes,
                    engine_version,
                    validation_status,
                    ai_metadata,
                    created_at
                )
                VALUES (
                    :id,
                    :school_id,
                    :student_id,
                    :report_id,
                    :model_name,
                    CAST(:teacher_version AS jsonb),
                    CAST(:parent_version AS jsonb),
                    CAST(:signals_detected AS jsonb),
                    :guardrails_passed,
                    :guardrails_notes,
                    :engine_version,
                    :validation_status,
                    CAST(:ai_metadata AS jsonb),
                    NOW()
                )
                """
            ),
            {
                "id": str(ai_report_id),
                "school_id": str(school_id),
                "student_id": str(student_id),
                "report_id": str(report_id),
                "model_name": "test-wizard-model",
                "teacher_version": json.dumps(
                    {
                        "summary": ("Reporte de prueba para validar wizard IHUI 3.0."),
                        "signals_detected": [
                            "Se distrae rápido",
                            "Necesita recordatorios frecuentes",
                        ],
                        "microintervenciones": [
                            {
                                "title": "Estrategia pendiente de validación",
                                "objective": "Validar hipótesis mediante wizard.",
                                "steps": [
                                    "Responder preguntas cerradas del wizard.",
                                ],
                                "frequency": "Diaria",
                                "duration": "10 minutos",
                                "progress_indicator": "Pendiente de validación.",
                            }
                        ],
                    }
                ),
                "parent_version": json.dumps(
                    {
                        "summary": (
                            "Este es un reporte de prueba para validar preguntas cerradas."
                        ),
                        "signals_detected": [
                            "Necesita apoyo para mantenerse en actividad.",
                        ],
                        "microintervenciones": [
                            {
                                "title": "Apoyo en casa pendiente de validación",
                                "objective": "Validar qué estrategia aplicar.",
                                "steps": [
                                    "Responder las preguntas del wizard.",
                                ],
                                "frequency": "Diaria",
                                "duration": "10 minutos",
                                "progress_indicator": "Pendiente de validación.",
                            }
                        ],
                    }
                ),
                "signals_detected": json.dumps(
                    [
                        "Se distrae rápido",
                        "Necesita recordatorios frecuentes",
                        "Requiere repetición de instrucciones",
                    ]
                ),
                "guardrails_passed": True,
                "guardrails_notes": None,
                "engine_version": "ihui_3",
                "validation_status": "needs_validation_answers",
                "ai_metadata": json.dumps(metadata),
            },
        )

        db.commit()

        print("Created test wizard AI report")
        print(f"ai_report_id={ai_report_id}")
        print(f"school_id={school_id}")
        print(f"student_id={student_id}")
        print(f"report_id={report_id}")

    finally:
        db.close()


if __name__ == "__main__":
    main()
