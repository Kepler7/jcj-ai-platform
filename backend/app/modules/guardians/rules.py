from datetime import datetime
from sqlalchemy import update
from sqlalchemy.orm import Session
from uuid import UUID

from app.modules.guardians.models import Guardian


def unset_other_primaries(
    db: Session,
    *,
    student_id: UUID,
    keep_guardian_id: UUID | None = None,
) -> None:
    """
    Apaga is_primary para otros tutores del alumno (soft delete respetado),
    manteniendo opcionalmente uno como primary.
    """
    q = (
        update(Guardian)
        .where(
            Guardian.student_id == student_id,
            Guardian.is_active == True,
            Guardian.is_primary == True,   # <-- solo los que eran primary
        )
    )

    if keep_guardian_id:
        q = q.where(Guardian.id != keep_guardian_id)

    db.execute(
        q.values(
            is_primary=False,
            updated_at=datetime.utcnow(),
        )
    )
