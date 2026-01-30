from sqlalchemy import update
from sqlalchemy.orm import Session
from uuid import UUID

from app.modules.guardians.models import Guardian


def unset_other_primaries(db: Session, *, student_id: UUID, keep_guardian_id: UUID | None = None) -> None:
    """
    Deja is_primary = false para todos los tutores del alumno,
    excepto (opcionalmente) el que se va a mantener como primary.
    """
    q = update(Guardian).where(Guardian.student_id == student_id, Guardian.is_active == True)
    if keep_guardian_id:
        q = q.where(Guardian.id != keep_guardian_id)
    db.execute(q.values(is_primary=False))
