from app.modules.ai_reports.wizard import (
    select_wizard_questions,
    score_wizard_answers,
)


def test_select_wizard_questions_two_candidates_two_questions_each():
    candidates = [
        {
            "playbook_id": "51",
            "nucleus": "Atención",
            "subskill": "Permanencia en tarea",
            "validation_questions": [
                "Pregunta 51-1",
                "Pregunta 51-2",
                "Pregunta 51-3",
            ],
        },
        {
            "playbook_id": "52",
            "nucleus": "Comprensión",
            "subskill": "Seguimiento de instrucciones",
            "validation_questions": [
                "Pregunta 52-1",
                "Pregunta 52-2",
            ],
        },
    ]

    questions = select_wizard_questions(candidates)

    assert len(questions) == 4

    assert questions[0]["playbook_id"] == "51"
    assert questions[0]["question_id"] == "51-q1"
    assert questions[0]["text"] == "Pregunta 51-1"

    assert questions[1]["playbook_id"] == "51"
    assert questions[1]["question_id"] == "51-q2"
    assert questions[1]["text"] == "Pregunta 51-2"

    assert questions[2]["playbook_id"] == "52"
    assert questions[2]["question_id"] == "52-q1"
    assert questions[2]["text"] == "Pregunta 52-1"

    assert questions[3]["playbook_id"] == "52"
    assert questions[3]["question_id"] == "52-q2"
    assert questions[3]["text"] == "Pregunta 52-2"


def test_select_wizard_questions_two_candidates_one_has_only_one_question():
    candidates = [
        {
            "playbook_id": "51",
            "nucleus": "Atención",
            "subskill": "Permanencia en tarea",
            "validation_questions": [
                "Pregunta 51-1",
                "Pregunta 51-2",
                "Pregunta 51-3",
            ],
        },
        {
            "playbook_id": "52",
            "nucleus": "Comprensión",
            "subskill": "Seguimiento de instrucciones",
            "validation_questions": [
                "Pregunta 52-1",
            ],
        },
    ]

    questions = select_wizard_questions(candidates)

    assert len(questions) == 2

    assert questions[0]["playbook_id"] == "51"
    assert questions[0]["question_id"] == "51-q1"
    assert questions[0]["text"] == "Pregunta 51-1"

    assert questions[1]["playbook_id"] == "52"
    assert questions[1]["question_id"] == "52-q1"
    assert questions[1]["text"] == "Pregunta 52-1"


def test_select_wizard_questions_three_candidates_one_question_each():
    candidates = [
        {
            "playbook_id": "51",
            "nucleus": "Atención",
            "subskill": "Permanencia en tarea",
            "validation_questions": [
                "Pregunta 51-1",
                "Pregunta 51-2",
            ],
        },
        {
            "playbook_id": "52",
            "nucleus": "Comprensión",
            "subskill": "Seguimiento de instrucciones",
            "validation_questions": [
                "Pregunta 52-1",
                "Pregunta 52-2",
            ],
        },
        {
            "playbook_id": "53",
            "nucleus": "Lenguaje",
            "subskill": "Articulación",
            "validation_questions": [
                "Pregunta 53-1",
                "Pregunta 53-2",
            ],
        },
    ]

    questions = select_wizard_questions(candidates)

    assert len(questions) == 3

    assert questions[0]["playbook_id"] == "51"
    assert questions[0]["question_id"] == "51-q1"

    assert questions[1]["playbook_id"] == "52"
    assert questions[1]["question_id"] == "52-q1"

    assert questions[2]["playbook_id"] == "53"
    assert questions[2]["question_id"] == "53-q1"


def test_score_wizard_answers_selects_winner_with_clear_margin():
    candidates = [
        {
            "playbook_id": "51",
            "nucleus": "Atención",
            "subskill": "Permanencia en tarea",
            "score": 0.82,
        },
        {
            "playbook_id": "52",
            "nucleus": "Comprensión",
            "subskill": "Seguimiento de instrucciones",
            "score": 0.79,
        },
    ]

    answers = [
        {"playbook_id": "51", "question_id": "51-q1", "answer": "yes"},
        {"playbook_id": "51", "question_id": "51-q2", "answer": "yes"},
        {"playbook_id": "52", "question_id": "52-q1", "answer": "yes"},
        {"playbook_id": "52", "question_id": "52-q2", "answer": "no"},
    ]

    result = score_wizard_answers(candidates, answers)

    wizard = result["wizard"]

    assert wizard["decision"] == "selected"
    assert wizard["selected_playbook_id"] == "51"
    assert wizard["confidence_after_validation"] == "high"

    assert wizard["candidate_scores"][0]["playbook_id"] == "51"
    assert wizard["candidate_scores"][0]["validation_score"] == 4

    assert wizard["candidate_scores"][1]["playbook_id"] == "52"
    assert wizard["candidate_scores"][1]["validation_score"] == 2


def test_score_wizard_answers_selects_winner_with_low_confidence():
    candidates = [
        {
            "playbook_id": "51",
            "nucleus": "Atención",
            "subskill": "Permanencia en tarea",
            "score": 0.82,
        },
        {
            "playbook_id": "52",
            "nucleus": "Comprensión",
            "subskill": "Seguimiento de instrucciones",
            "score": 0.79,
        },
    ]

    answers = [
        {"playbook_id": "51", "question_id": "51-q1", "answer": "yes"},
        {"playbook_id": "51", "question_id": "51-q2", "answer": "sometimes"},
        {"playbook_id": "52", "question_id": "52-q1", "answer": "yes"},
        {"playbook_id": "52", "question_id": "52-q2", "answer": "no"},
    ]

    result = score_wizard_answers(candidates, answers)

    wizard = result["wizard"]

    assert wizard["decision"] == "selected_low_confidence"
    assert wizard["selected_playbook_id"] == "51"
    assert wizard["confidence_after_validation"] == "medium"

    assert wizard["candidate_scores"][0]["playbook_id"] == "51"
    assert wizard["candidate_scores"][0]["validation_score"] == 3

    assert wizard["candidate_scores"][1]["playbook_id"] == "52"
    assert wizard["candidate_scores"][1]["validation_score"] == 2


def test_score_wizard_answers_combines_when_tie_has_same_nucleus():
    candidates = [
        {
            "playbook_id": "51",
            "nucleus": "Atención",
            "subskill": "Permanencia en tarea",
            "score": 0.82,
        },
        {
            "playbook_id": "52",
            "nucleus": "Atención",
            "subskill": "Atención sostenida",
            "score": 0.79,
        },
    ]

    answers = [
        {"playbook_id": "51", "question_id": "51-q1", "answer": "yes"},
        {"playbook_id": "52", "question_id": "52-q1", "answer": "yes"},
    ]

    result = score_wizard_answers(candidates, answers)

    wizard = result["wizard"]

    assert wizard["decision"] == "combined_same_nucleus"
    assert wizard["selected_playbook_id"] is None
    assert wizard["confidence_after_validation"] == "medium"
    assert set(wizard["combined_playbook_ids"]) == {"51", "52"}


def test_score_wizard_answers_pending_review_when_tie_has_different_nucleus():
    candidates = [
        {
            "playbook_id": "51",
            "nucleus": "Atención",
            "subskill": "Permanencia en tarea",
            "score": 0.82,
        },
        {
            "playbook_id": "52",
            "nucleus": "Comprensión",
            "subskill": "Seguimiento de instrucciones",
            "score": 0.79,
        },
    ]

    answers = [
        {"playbook_id": "51", "question_id": "51-q1", "answer": "yes"},
        {"playbook_id": "52", "question_id": "52-q1", "answer": "yes"},
    ]

    result = score_wizard_answers(candidates, answers)

    wizard = result["wizard"]

    assert wizard["decision"] == "pending_human_review"
    assert wizard["selected_playbook_id"] is None
    assert wizard["confidence_after_validation"] == "low"
    assert set(wizard["combined_playbook_ids"]) == {"51", "52"}


def test_score_wizard_answers_pending_review_when_all_scores_are_zero():
    candidates = [
        {
            "playbook_id": "51",
            "nucleus": "Atención",
            "subskill": "Permanencia en tarea",
            "score": 0.82,
        },
        {
            "playbook_id": "52",
            "nucleus": "Comprensión",
            "subskill": "Seguimiento de instrucciones",
            "score": 0.79,
        },
    ]

    answers = [
        {"playbook_id": "51", "question_id": "51-q1", "answer": "no"},
        {"playbook_id": "52", "question_id": "52-q1", "answer": "no"},
    ]

    result = score_wizard_answers(candidates, answers)

    wizard = result["wizard"]

    assert wizard["decision"] == "pending_human_review"
    assert wizard["selected_playbook_id"] is None
    assert wizard["confidence_after_validation"] == "low"
