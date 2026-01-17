from __future__ import annotations

from typing import Optional, List
from uuid import UUID
from sqlalchemy.orm import Session

from app.modules.ai_reports.models import AIReport
from app.modules.reports.models import StudentReport
from app.modules.students.models import Student

from app.ai.orchestrator import generate_support

def generate_ai_report(
    *,
    db: Session,
    report_id: UUID,
    user_id: UUID,
    contexts: Optional[List[str]] = None,
) -> AIReport:
    """
    Genera un AIReport para un StudentReport existente y lo guarda en Postgres.

    Importante:
    - NO valida permisos aquí (eso lo hace el endpoint/worker con ensure_same_school).
    - Aquí solo hace: fetch data -> prompt -> LLM -> guardar AIReport.
    """

    # 1) Cargar StudentReport
    report = db.get(StudentReport, report_id)
    if not report:
        raise ValueError("StudentReport not found")

    # 2) Cargar Student (para nombre/edad/grupo)
    student = db.get(Student, report.student_id)
    if not student:
        raise ValueError("Student not found")

    # 3) Armar report_text según tus campos reales
    # Ajusta si tu modelo usa otros nombres
    parts = []
    if getattr(report, "strengths", None):
        parts.append(f"Fortalezas: {report.strengths}")
    if getattr(report, "challenges", None):
        parts.append(f"Retos: {report.challenges}")
    if getattr(report, "notes", None):
        parts.append(f"Notas: {report.notes}")

    report_text = "\n".join(parts).strip() or "Sin observaciones."

    # 4) Generar con IA (RAG incluido si tu orchestrator ya lo tiene)
    support, model_name = generate_support(
        student_name=student.name,
        age=student.age,
        group=getattr(student, "group", "") or "",
        report_text=report_text,
        contexts=contexts,
    )

    # 5) Guardar en ai_reports
    ai_report = AIReport(
        school_id=report.school_id,
        student_id=report.student_id,
        report_id=report.id,
        generated_by_user_id=user_id,
        model_name=model_name,
        teacher_version=support.teacher_version.model_dump(),
        parent_version=support.parent_version.model_dump(),
        signals_detected=support.signals_detected,
        guardrails_passed=True,
        guardrails_notes=None,
    )

    db.add(ai_report)
    db.commit()
    db.refresh(ai_report)
    return ai_report