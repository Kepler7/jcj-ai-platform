from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import select

from app.db.db import get_db
from app.modules.schools.models import School
from app.modules.schools.schemas import SchoolCreate, SchoolUpdate, SchoolOut
from app.auth.deps import require_role
from app.auth.roles import Role

router = APIRouter(prefix="/v1/schools", tags=["schools"])

# Placeholder: Jefte implementará auth; por ahora simulamos
def require_platform_admin():
    # Cambiar luego por: requireAuth + requireRole("platform_admin")
    return True

@router.post("", response_model=SchoolOut, status_code=status.HTTP_201_CREATED)
def create_school(payload: SchoolCreate, db: Session = Depends(get_db), _user=Depends(require_role(Role.platform_admin)),):
    school = School(**payload.model_dump())
    db.add(school)
    db.commit()
    db.refresh(school)
    return school

@router.get("", response_model=list[SchoolOut])
def list_schools(db: Session = Depends(get_db), _user=Depends(require_role(Role.platform_admin)),):
    schools = db.execute(select(School)).scalars().all()
    return schools

@router.patch("/{school_id}", response_model=SchoolOut)
def update_school(school_id: str, payload: SchoolUpdate, db: Session = Depends(get_db), _user=Depends(require_role(Role.platform_admin)),):
    school = db.get(School, school_id)
    if not school:
        raise HTTPException(status_code=404, detail="School not found")

    data = payload.model_dump(exclude_unset=True)
    for k, v in data.items():
        setattr(school, k, v)

    db.commit()
    db.refresh(school)
    return school
