from fastapi import APIRouter, Depends, HTTPException, status, Response
from sqlalchemy.orm import Session
from sqlalchemy import select, desc
from uuid import UUID

from app.db.db import get_db

from app.auth.deps import require_role
from app.auth.roles import Role
from app.modules.users.models import User

from app.modules.reports.models import StudentReport
from app.modules.students.models import Student

from app.modules.ai_reports.models import AIReport
from app.modules.ai_reports.schemas import AIReportOut
from app.modules.ai_reports.schemas import GenerateAIReportRequest

from app.ai.orchestrator import generate_support

router = APIRouter(prefix="/v1/ai-reports", tags=["ai-reports"])


def ensure_same_school(user: User, school_id: UUID):
    # platform_admin puede todo
    if user.role == Role.platform_admin.value:
        return
    if not user.school_id or UUID(str(user.school_id)) != UUID(str(school_id)):
        raise HTTPException(status_code=403, detail="Forbidden (different school)")


def build_report_text(student: Student, report: StudentReport) -> str:
    parts = [
        f"Alumno: {student.full_name}",
        f"Edad: {student.age}",
        f"Grupo: {student.group}",
        "",
        "Observaciones del reporte:",
    ]

    if getattr(report, "mood", None):
        parts.append(f"- Estado de ánimo: {report.mood}")
    if getattr(report, "participation", None):
        parts.append(f"- Participación: {report.participation}")

    if getattr(report, "strengths", None):
        parts.append("")
        parts.append("Fortalezas observadas:")
        parts.append(str(report.strengths))

    if getattr(report, "challenges", None):
        parts.append("")
        parts.append("Retos / dificultades observadas:")
        parts.append(str(report.challenges))

    if getattr(report, "notes", None):
        parts.append("")
        parts.append("Notas adicionales:")
        parts.append(str(report.notes))

    return "\n".join(parts).strip()


@router.post("/generate", response_model=AIReportOut)
def generate_ai_report(
    payload: GenerateAIReportRequest,
    response: Response,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(Role.platform_admin, Role.school_admin, Role.teacher)),
):
    # 1) Buscar el reporte base
    report = db.get(StudentReport, payload.report_id)
    if not report:
        raise HTTPException(status_code=404, detail="StudentReport not found")

    # 2) Buscar alumno
    student = db.get(Student, report.student_id)
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")

    # 3) Permisos por escuela
    ensure_same_school(current_user, UUID(str(student.school_id)))

    # Si ya existe y NO force => devolver el más reciente
    if not payload.force:
        existing = (
            db.execute(
                select(AIReport)
                .where(AIReport.report_id == report.id)
                .order_by(desc(AIReport.created_at))
                .limit(1)
            )
            .scalars()
            .first()
        )
        if existing:
            # 200 OK: no se generó nada nuevo
            response.status_code = status.HTTP_200_OK
            return existing

    # 4) Armar texto de contexto
    report_text = build_report_text(student, report)

    # 5) Generar con IA (valida JSON + guardrails adentro)
    try:
        generated, model_name = generate_support(
            student_name=student.full_name,
            age=student.age,
            group=student.group,
            report_text=report_text,
        )
    except ValueError as e:
        # JSON inválido, guardrails fallaron, etc.
        raise HTTPException(status_code=422, detail=str(e))

    # 6) Guardar en ai_reports
    ai_row = AIReport(
        school_id=student.school_id,
        student_id=student.id,
        report_id=report.id,
        generated_by_user_id=current_user.id,
        model_name=model_name,
        teacher_version=generated.teacher_version.model_dump(),
        parent_version=generated.parent_version.model_dump(),
        signals_detected=generated.teacher_version.signals_detected,  # fuente única
        guardrails_passed=True,
        guardrails_notes=None,
    )

    db.add(ai_row)
    db.commit()
    db.refresh(ai_row)

    response.status_code = status.HTTP_201_CREATED
    return ai_row

