import os
import sys
from datetime import datetime
from pathlib import Path

from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

import app.db.models_imports  # noqa: F401
from app.modules.schools.models import School
from app.modules.users.models import User
from app.modules.students.models import Student
from app.modules.classes.models import Class, TeacherClass, StudentClass
from app.modules.guardians.models import Guardian


def log_ok(message: str) -> None:
    print(f"✓ {message}")


def log_info(message: str) -> None:
    print(f"- {message}")


def get_database_url() -> str:
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        raise RuntimeError(
            "DATABASE_URL no está definida.\n"
            "Corre este script dentro del contenedor backend:\n"
            "docker compose -f docker-compose.dev.yml exec backend python scripts/smoke/seed_test_data.py"
        )
    return database_url


def get_or_create_school(session) -> School:
    school_name = "Smoke Test School"
    school = session.scalar(select(School).where(School.name == school_name))
    if school:
        log_ok(f"school ya existe: {school.name}")
        return school

    school = School(
        name=school_name,
        legal_name="Smoke Test School Legal Name",
        city="Guadalajara",
        state="Jalisco",
        is_active=True,
    )
    session.add(school)
    session.commit()
    session.refresh(school)
    log_ok(f"school creada: {school.name}")
    return school


def get_or_create_user(
    session, *, email: str, role: str, school_id, password_hash: str = "smoke_test"
) -> User:
    user = session.scalar(select(User).where(User.email == email))
    if user:
        log_ok(f"{role} ya existe: {email}")
        return user

    user = User(
        email=email,
        password_hash=password_hash,
        role=role,
        school_id=school_id,
        is_active=True,
        reset_token_version=0,
    )
    session.add(user)
    session.commit()
    session.refresh(user)
    log_ok(f"{role} creado: {email}")
    return user


def get_or_create_student(session, *, school_id) -> Student:
    full_name = "Alumno Smoke Test"
    student = session.scalar(
        select(Student).where(
            Student.full_name == full_name,
            Student.school_id == school_id,
        )
    )
    if student:
        log_ok(f"student ya existe: {full_name}")
        return student

    student = Student(
        full_name=full_name,
        age=10,
        school_id=school_id,
        group="Smoke",
        notes="Alumno generado automáticamente para smoke tests",
        is_active=True,
    )
    session.add(student)
    session.commit()
    session.refresh(student)
    log_ok(f"student creado: {full_name}")
    return student


def get_or_create_guardian(session, *, school_id, student_id) -> Guardian:
    guardian_name = "Tutor Smoke Test"
    guardian = session.scalar(
        select(Guardian).where(
            Guardian.full_name == guardian_name,
            Guardian.student_id == student_id,
        )
    )
    if guardian:
        log_ok(f"guardian ya existe: {guardian_name}")
        return guardian

    guardian = Guardian(
        school_id=school_id,
        student_id=student_id,
        full_name=guardian_name,
        whatsapp_phone="5213310000000",
        relationship="parent",
        is_primary=True,
        is_active=True,
        receive_whatsapp=True,
        consent_to_contact=True,
        notes="Tutor generado automáticamente para smoke tests",
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )
    session.add(guardian)
    session.commit()
    session.refresh(guardian)
    log_ok(f"guardian creado: {guardian_name}")
    return guardian


def get_or_create_class(session, *, school_id) -> Class:
    class_name = "Clase Smoke A"
    classroom = session.scalar(
        select(Class).where(
            Class.name == class_name,
            Class.school_id == school_id,
        )
    )
    if classroom:
        log_ok(f"class ya existe: {class_name}")
        return classroom

    classroom = Class(
        name=class_name,
        school_id=school_id,
        created_at=datetime.utcnow(),
    )
    session.add(classroom)
    session.commit()
    session.refresh(classroom)
    log_ok(f"class creada: {class_name}")
    return classroom


def ensure_teacher_class(session, *, teacher_id, class_id) -> None:
    relation = session.scalar(
        select(TeacherClass).where(
            TeacherClass.teacher_id == teacher_id,
            TeacherClass.class_id == class_id,
        )
    )
    if relation:
        log_ok("teacher ya estaba asignado a la class")
        return

    relation = TeacherClass(
        teacher_id=teacher_id,
        class_id=class_id,
        created_at=datetime.utcnow(),
    )
    session.add(relation)
    session.commit()
    log_ok("teacher asignado a la class")


def ensure_student_class(session, *, student_id, class_id) -> None:
    relation = session.scalar(
        select(StudentClass).where(
            StudentClass.student_id == student_id,
            StudentClass.class_id == class_id,
        )
    )
    if relation:
        log_ok("student ya estaba asignado a la class")
        return

    relation = StudentClass(
        student_id=student_id,
        class_id=class_id,
        created_at=datetime.utcnow(),
    )
    session.add(relation)
    session.commit()
    log_ok("student asignado a la class")


def main() -> None:
    log_info("Iniciando seed de smoke test data...")

    database_url = get_database_url()
    engine = create_engine(database_url)
    SessionLocal = sessionmaker(bind=engine)

    session = SessionLocal()

    try:
        school = get_or_create_school(session)

        admin = get_or_create_user(
            session,
            email="admin.smoke@jcj.local",
            role="admin",
            school_id=school.id,
        )

        teacher = get_or_create_user(
            session,
            email="teacher.smoke@jcj.local",
            role="teacher",
            school_id=school.id,
        )

        parent = get_or_create_user(
            session,
            email="parent.smoke@jcj.local",
            role="parent",
            school_id=school.id,
        )

        student = get_or_create_student(session, school_id=school.id)
        guardian = get_or_create_guardian(
            session,
            school_id=school.id,
            student_id=student.id,
        )
        classroom = get_or_create_class(session, school_id=school.id)

        ensure_teacher_class(
            session,
            teacher_id=teacher.id,
            class_id=classroom.id,
        )

        ensure_student_class(
            session,
            student_id=student.id,
            class_id=classroom.id,
        )

        print("")
        log_ok("Smoke test seed finalizado")
        print("")
        print("Resumen:")
        print(f"  School   : {school.name}")
        print(f"  Admin    : {admin.email}")
        print(f"  Teacher  : {teacher.email}")
        print(f"  Parent   : {parent.email}")
        print(f"  Student  : {student.full_name}")
        print(f"  Guardian : {guardian.full_name}")
        print(f"  Class    : {classroom.name}")

    finally:
        session.close()


if __name__ == "__main__":
    main()
