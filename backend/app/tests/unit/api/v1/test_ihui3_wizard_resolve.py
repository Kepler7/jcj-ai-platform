from uuid import uuid4
from unittest.mock import MagicMock

from fastapi.testclient import TestClient

from app.main import app
from app.db.db import get_db
from app.auth.deps import get_current_user
from app.modules.ai_reports.models import AIReport


def _fake_user():
    return {
        "id": str(uuid4()),
        "role": "teacher",
        "school_id": str(uuid4()),
    }


def _make_ai_report(
    *,
    ai_report_id,
    decision_case="clear_margin",
):
    metadata = {
        "wizard_required": True,
        "ihui3_wizard_candidates": [
            {
                "playbook_id": "51",
                "nucleus": "Atención",
                "subskill": "Permanencia en tarea",
                "score": 0.82,
                "matched_terms": ["se distrae rápido"],
                "reason": "Top candidate 51",
                "validation_questions": [
                    "Pregunta 51-1",
                    "Pregunta 51-2",
                ],
                "micro_objective": "Aumentar permanencia en tarea",
                "strategy_steps": [
                    "Dar instrucciones cortas.",
                    "Usar pausas breves.",
                ],
                "frequency": "Diaria",
                "duration": "10 minutos",
                "progress_indicator": "Permanece más tiempo en actividad",
                "escalation": "Consultar a especialista si persiste",
            },
            {
                "playbook_id": "52",
                "nucleus": "Comprensión",
                "subskill": "Seguimiento de instrucciones",
                "score": 0.79,
                "matched_terms": ["necesita repetir instrucción"],
                "reason": "Top candidate 52",
                "validation_questions": [
                    "Pregunta 52-1",
                    "Pregunta 52-2",
                ],
                "micro_objective": "Mejorar seguimiento de instrucciones",
                "strategy_steps": [
                    "Repetir instrucción en pasos.",
                    "Confirmar comprensión.",
                ],
                "frequency": "Diaria",
                "duration": "10 minutos",
                "progress_indicator": "Sigue instrucciones con menos apoyo",
                "escalation": "Consultar a especialista si persiste",
            },
        ],
        "ihui3_wizard_questions": [
            {
                "playbook_id": "51",
                "nucleus": "Atención",
                "subskill": "Permanencia en tarea",
                "question_id": "51-q1",
                "text": "Pregunta 51-1",
            },
            {
                "playbook_id": "51",
                "nucleus": "Atención",
                "subskill": "Permanencia en tarea",
                "question_id": "51-q2",
                "text": "Pregunta 51-2",
            },
            {
                "playbook_id": "52",
                "nucleus": "Comprensión",
                "subskill": "Seguimiento de instrucciones",
                "question_id": "52-q1",
                "text": "Pregunta 52-1",
            },
            {
                "playbook_id": "52",
                "nucleus": "Comprensión",
                "subskill": "Seguimiento de instrucciones",
                "question_id": "52-q2",
                "text": "Pregunta 52-2",
            },
        ],
    }

    ai_report = AIReport()

    ai_report.id = ai_report_id
    ai_report.report_id = uuid4()
    ai_report.student_id = uuid4()
    ai_report.school_id = uuid4()
    ai_report.engine_version = "ihui_3"
    ai_report.validation_status = "needs_validation_answers"
    ai_report.ai_metadata = metadata

    return ai_report


def _override_db(ai_report):
    db = MagicMock()
    db.get.return_value = ai_report
    db.add.return_value = None
    db.commit.return_value = None
    db.refresh.return_value = None
    return db


def test_submit_validation_answers_selects_candidate_with_clear_margin():
    ai_report_id = uuid4()
    ai_report = _make_ai_report(ai_report_id=ai_report_id)
    db = _override_db(ai_report)

    app.dependency_overrides[get_db] = lambda: db
    app.dependency_overrides[get_current_user] = _fake_user

    client = TestClient(app)

    response = client.post(
        f"/v1/ihui3/reports/{ai_report_id}/validation-answers",
        json={
            "answers": [
                {
                    "playbook_id": "51",
                    "question_id": "51-q1",
                    "answer": "yes",
                },
                {
                    "playbook_id": "51",
                    "question_id": "51-q2",
                    "answer": "yes",
                },
                {
                    "playbook_id": "52",
                    "question_id": "52-q1",
                    "answer": "yes",
                },
                {
                    "playbook_id": "52",
                    "question_id": "52-q2",
                    "answer": "no",
                },
            ]
        },
    )

    app.dependency_overrides.clear()

    assert response.status_code == 200
    body = response.json()

    assert body["ai_report_id"] == str(ai_report_id)
    assert body["validation_status"] == "validated"
    assert body["wizard_required"] is False

    metadata = ai_report.ai_metadata

    assert metadata["wizard_required"] is False
    assert metadata["validation_status"] == "validated"
    assert metadata["review_status"] == "validated"
    assert metadata["ihui3_wizard_result"]["decision"] == "selected"
    assert metadata["ihui3_wizard_result"]["selected_playbook_id"] == "51"
    assert metadata["confidence_after_validation"] == "high"

    assert metadata["ihui3_match"]["playbook_id"] == "51"
    assert metadata["ihui3_match"]["source"] == "wizard_scoring"
    assert metadata["ihui3_strategy"]["status"] == "validated"

    db.add.assert_called_once_with(ai_report)
    db.commit.assert_called_once()
    db.refresh.assert_called_once_with(ai_report)


def test_submit_validation_answers_selects_candidate_with_low_confidence():
    ai_report_id = uuid4()
    ai_report = _make_ai_report(ai_report_id=ai_report_id)
    db = _override_db(ai_report)

    app.dependency_overrides[get_db] = lambda: db
    app.dependency_overrides[get_current_user] = _fake_user

    client = TestClient(app)

    response = client.post(
        f"/v1/ihui3/reports/{ai_report_id}/validation-answers",
        json={
            "answers": [
                {
                    "playbook_id": "51",
                    "question_id": "51-q1",
                    "answer": "yes",
                },
                {
                    "playbook_id": "51",
                    "question_id": "51-q2",
                    "answer": "sometimes",
                },
                {
                    "playbook_id": "52",
                    "question_id": "52-q1",
                    "answer": "yes",
                },
                {
                    "playbook_id": "52",
                    "question_id": "52-q2",
                    "answer": "no",
                },
            ]
        },
    )

    app.dependency_overrides.clear()

    assert response.status_code == 200

    metadata = ai_report.ai_metadata

    assert metadata["ihui3_wizard_result"]["decision"] == "selected_low_confidence"
    assert metadata["ihui3_wizard_result"]["selected_playbook_id"] == "51"
    assert metadata["confidence_after_validation"] == "medium"
    assert metadata["validation_status"] == "validated"
    assert metadata["review_status"] == "validated"
    assert metadata["ihui3_match"]["playbook_id"] == "51"


def test_submit_validation_answers_combines_candidates_with_same_nucleus_tie():
    ai_report_id = uuid4()
    ai_report = _make_ai_report(ai_report_id=ai_report_id)

    ai_report.ai_metadata["ihui3_wizard_candidates"][1]["nucleus"] = "Atención"
    ai_report.ai_metadata["ihui3_wizard_candidates"][1][
        "subskill"
    ] = "Atención sostenida"

    ai_report.ai_metadata["ihui3_wizard_questions"][2]["nucleus"] = "Atención"
    ai_report.ai_metadata["ihui3_wizard_questions"][2][
        "subskill"
    ] = "Atención sostenida"

    ai_report.ai_metadata["ihui3_wizard_questions"][3]["nucleus"] = "Atención"
    ai_report.ai_metadata["ihui3_wizard_questions"][3][
        "subskill"
    ] = "Atención sostenida"

    db = _override_db(ai_report)

    app.dependency_overrides[get_db] = lambda: db
    app.dependency_overrides[get_current_user] = _fake_user

    client = TestClient(app)

    response = client.post(
        f"/v1/ihui3/reports/{ai_report_id}/validation-answers",
        json={
            "answers": [
                {
                    "playbook_id": "51",
                    "question_id": "51-q1",
                    "answer": "yes",
                },
                {
                    "playbook_id": "52",
                    "question_id": "52-q1",
                    "answer": "yes",
                },
            ]
        },
    )

    app.dependency_overrides.clear()

    assert response.status_code == 200

    metadata = ai_report.ai_metadata

    assert metadata["ihui3_wizard_result"]["decision"] == "combined_same_nucleus"
    assert set(metadata["ihui3_wizard_result"]["combined_playbook_ids"]) == {
        "51",
        "52",
    }
    assert metadata["validation_status"] == "validated_combined"
    assert metadata["review_status"] == "validated"
    assert metadata["ihui3_strategy"]["status"] == "validated_combined"
    assert metadata["ihui3_match"]["source"] == "wizard_scoring"
    assert metadata["ihui3_match"]["combined_playbook_ids"] == ["51", "52"]


def test_submit_validation_answers_sends_to_human_review_when_different_nucleus_tie():
    ai_report_id = uuid4()
    ai_report = _make_ai_report(ai_report_id=ai_report_id)
    db = _override_db(ai_report)

    app.dependency_overrides[get_db] = lambda: db
    app.dependency_overrides[get_current_user] = _fake_user

    client = TestClient(app)

    response = client.post(
        f"/v1/ihui3/reports/{ai_report_id}/validation-answers",
        json={
            "answers": [
                {
                    "playbook_id": "51",
                    "question_id": "51-q1",
                    "answer": "yes",
                },
                {
                    "playbook_id": "52",
                    "question_id": "52-q1",
                    "answer": "yes",
                },
            ]
        },
    )

    app.dependency_overrides.clear()

    assert response.status_code == 200

    metadata = ai_report.ai_metadata

    assert metadata["ihui3_wizard_result"]["decision"] == "pending_human_review"
    assert metadata["validation_status"] == "pending_human_review"
    assert metadata["review_status"] == "pending_human_review"
    assert metadata["fallback_used"] is True
    assert metadata["fallback_reason"] == "ihui3_wizard_unresolved"
    assert metadata["confidence_after_validation"] == "low"
    assert metadata["ihui3_strategy"]["status"] == "pending_human_review"
    assert metadata["ihui3_strategy"]["steps"] == []
    assert metadata["ihui3_match"]["source"] == "wizard_scoring"
    assert metadata["ihui3_match"]["playbook_id"] is None
