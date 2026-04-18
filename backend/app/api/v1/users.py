from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import select

from app.db.db import get_db
from app.modules.users.models import User
from app.modules.users.schemas import UserCreate, UserOut
from app.auth.passwords import hash_password
from app.auth.deps import require_role, get_current_user
from app.auth.roles import Role

router = APIRouter(prefix="/v1/users", tags=["users"])

@router.post("", response_model=UserOut, status_code=status.HTTP_201_CREATED)
def create_user(
    payload: UserCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(Role.platform_admin, Role.school_admin)),
):
    if current_user.role == Role.school_admin.value:
        if payload.role != Role.teacher.value:
            raise HTTPException(status_code=403, detail="School admins can only create teachers")
        payload.school_id = current_user.school_id

    # Validar rol permitido
    if payload.role not in [Role.school_admin.value, Role.teacher.value]:
        raise HTTPException(status_code=400, detail="Invalid role")

    # Validar school_id
    if payload.role in [Role.school_admin.value, Role.teacher.value] and not payload.school_id:
        raise HTTPException(status_code=400, detail="school_id is required for this role")

    # Verificar email único
    existing = db.execute(select(User).where(User.email == payload.email)).scalar_one_or_none()
    if existing:
        raise HTTPException(status_code=400, detail="Email already exists")

    user = User(
        email=payload.email,
        password_hash=hash_password(payload.password),
        role=payload.role,
        school_id=payload.school_id,
        is_active=True,
    )

    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@router.get(
    "/by-school/{school_id}/teachers",
    response_model=list[UserOut],
    dependencies=[Depends(require_role(Role.platform_admin, Role.school_admin))],
)
def list_teachers_by_school(
    school_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.role == Role.school_admin.value and current_user.school_id != school_id:
        raise HTTPException(status_code=403, detail="Forbidden")

    q = (
        select(User)
        .where(
            User.school_id == school_id,
            User.role == Role.teacher.value,
            User.is_active == True,  # noqa: E712
        )
        .order_by(User.email.asc())
    )
    return list(db.execute(q).scalars().all())
