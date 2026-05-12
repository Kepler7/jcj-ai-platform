from typing import Any, Dict, List, Literal, Optional
from collections import defaultdict


WizardAnswer = Literal["yes", "no", "sometimes"]


ANSWER_POINTS = {
    "yes": 2,
    "sometimes": 1,
    "no": 0,
}

CLEAR_MARGIN = 2


def select_wizard_questions(
    candidates: List[Dict[str, Any]],
    max_candidates: int = 3,
) -> List[Dict[str, Any]]:
    """
    Selects validation questions for IHUI 3.0 wizard.

    Rules:
    - If there are 2 candidates:
        - Take 2 questions per candidate.
        - Except if one candidate has only 1 question, then take 1 per candidate.
    - If there are 3 candidates:
        - Take 1 question per candidate.
    - Questions are taken in the order defined by Deneb in the spreadsheet.
    - No random selection.
    """

    selected_candidates = candidates[:max_candidates]

    if not selected_candidates:
        return []

    if len(selected_candidates) == 1:
        candidate = selected_candidates[0]
        questions = candidate.get("validation_questions", [])[:2]

        return [
            {
                "playbook_id": candidate.get("playbook_id"),
                "nucleus": candidate.get("nucleus"),
                "subskill": candidate.get("subskill"),
                "question_id": f"{candidate.get('playbook_id')}-q{index + 1}",
                "text": question,
            }
            for index, question in enumerate(questions)
        ]

    if len(selected_candidates) == 2:
        first_questions = selected_candidates[0].get("validation_questions", [])
        second_questions = selected_candidates[1].get("validation_questions", [])

        questions_per_candidate = 2

        if len(first_questions) <= 1 or len(second_questions) <= 1:
            questions_per_candidate = 1

        return _build_questions(selected_candidates, questions_per_candidate)

    # 3 candidates
    return _build_questions(selected_candidates[:3], questions_per_candidate=1)


def _build_questions(
    candidates: List[Dict[str, Any]],
    questions_per_candidate: int,
) -> List[Dict[str, Any]]:
    """
    Builds normalized wizard question objects.
    """

    wizard_questions = []

    for candidate in candidates:
        playbook_id = candidate.get("playbook_id")
        questions = candidate.get("validation_questions", [])[:questions_per_candidate]

        for index, question in enumerate(questions):
            wizard_questions.append(
                {
                    "playbook_id": playbook_id,
                    "nucleus": candidate.get("nucleus"),
                    "subskill": candidate.get("subskill"),
                    "question_id": f"{playbook_id}-q{index + 1}",
                    "text": question,
                }
            )

    return wizard_questions


def score_wizard_answers(
    candidates: List[Dict[str, Any]],
    answers: List[Dict[str, str]],
) -> Dict[str, Any]:
    """
    Scores wizard answers and returns an auditable decision.

    Scoring:
    - yes = 2
    - sometimes = 1
    - no = 0

    Decision:
    - margin >= 2: selected / high
    - margin == 1: selected_low_confidence / medium
    - tie same nucleus/subskill: combined_same_nucleus / medium
    - tie different nucleus: pending_human_review / low
    - all zero: pending_human_review / low
    """

    candidate_map = {
        str(candidate.get("playbook_id")): candidate for candidate in candidates
    }

    scores = defaultdict(int)
    normalized_answers = []

    for answer_item in answers:
        playbook_id = str(answer_item.get("playbook_id"))
        question_id = answer_item.get("question_id")
        answer = answer_item.get("answer")

        points = ANSWER_POINTS.get(answer, 0)
        scores[playbook_id] += points

        normalized_answers.append(
            {
                "playbook_id": playbook_id,
                "question_id": question_id,
                "answer": answer,
                "points": points,
            }
        )

    candidate_scores = []

    for index, candidate in enumerate(candidates):
        playbook_id = str(candidate.get("playbook_id"))

        candidate_scores.append(
            {
                "playbook_id": playbook_id,
                "initial_rank": index + 1,
                "initial_score": candidate.get("score"),
                "validation_score": scores.get(playbook_id, 0),
                "final_score": scores.get(playbook_id, 0),
                "nucleus": candidate.get("nucleus"),
                "subskill": candidate.get("subskill"),
            }
        )

    candidate_scores.sort(
        key=lambda item: item["validation_score"],
        reverse=True,
    )

    decision_payload = _decide(candidate_scores)

    return {
        "wizard": {
            "required": True,
            "decision": decision_payload["decision"],
            "selected_playbook_id": decision_payload.get("selected_playbook_id"),
            "combined_playbook_ids": decision_payload.get("combined_playbook_ids", []),
            "confidence_after_validation": decision_payload[
                "confidence_after_validation"
            ],
            "decision_reason": decision_payload["decision_reason"],
            "scoring_rules": {
                "yes": 2,
                "sometimes": 1,
                "no": 0,
                "clear_margin": CLEAR_MARGIN,
            },
            "candidate_scores": candidate_scores,
            "answers": normalized_answers,
        }
    }


def _decide(candidate_scores: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Applies IHUI 3.0 decision rules.
    """

    if not candidate_scores:
        return {
            "decision": "pending_human_review",
            "selected_playbook_id": None,
            "confidence_after_validation": "low",
            "decision_reason": "No candidates were available after wizard scoring.",
        }

    top_score = candidate_scores[0]["validation_score"]

    if top_score == 0:
        return {
            "decision": "pending_human_review",
            "selected_playbook_id": None,
            "confidence_after_validation": "low",
            "decision_reason": "All candidates scored 0 after wizard answers.",
        }

    tied_candidates = [
        candidate
        for candidate in candidate_scores
        if candidate["validation_score"] == top_score
    ]

    if len(tied_candidates) > 1:
        same_nucleus = _all_same_value(tied_candidates, "nucleus")
        same_subskill = _all_same_value(tied_candidates, "subskill")

        if same_nucleus or same_subskill:
            return {
                "decision": "combined_same_nucleus",
                "selected_playbook_id": None,
                "combined_playbook_ids": [
                    candidate["playbook_id"] for candidate in tied_candidates
                ],
                "confidence_after_validation": "medium",
                "decision_reason": "Candidates tied but belong to the same nucleus or subskill.",
            }

        return {
            "decision": "pending_human_review",
            "selected_playbook_id": None,
            "combined_playbook_ids": [
                candidate["playbook_id"] for candidate in tied_candidates
            ],
            "confidence_after_validation": "low",
            "decision_reason": "Candidates tied across different nucleus/subskill areas.",
        }

    winner = candidate_scores[0]

    if len(candidate_scores) == 1:
        return {
            "decision": "selected",
            "selected_playbook_id": winner["playbook_id"],
            "confidence_after_validation": "high",
            "decision_reason": "Only one candidate was available and it received validation points.",
        }

    second_score = candidate_scores[1]["validation_score"]
    margin = winner["validation_score"] - second_score

    if margin >= CLEAR_MARGIN:
        return {
            "decision": "selected",
            "selected_playbook_id": winner["playbook_id"],
            "confidence_after_validation": "high",
            "decision_reason": f"Winner passed clear margin threshold. Margin: {margin}.",
        }

    return {
        "decision": "selected_low_confidence",
        "selected_playbook_id": winner["playbook_id"],
        "confidence_after_validation": "medium",
        "decision_reason": f"Winner had only a small margin. Margin: {margin}.",
    }


def _all_same_value(items: List[Dict[str, Any]], key: str) -> bool:
    """
    Returns True when all items have the same non-empty value for a key.
    """

    values = {item.get(key) for item in items if item.get(key)}

    return len(values) == 1
