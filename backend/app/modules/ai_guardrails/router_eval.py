from typing import Any, Dict, List

from app.modules.ai_guardrails.sensitive_classifier import classify_with_policy


def evaluate_router_cases(cases: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Evalúa una lista de casos del router y devuelve un resumen.

    ¿Qué mide?
    - accuracy de intent
    - accuracy de route
    - accuracy de response_mode

    También devuelve mismatches para inspección manual.

    Nota:
    En topics verificamos que los topics esperados estén presentes,
    no exigimos igualdad exacta de listas para no volver la evaluación frágil.
    """
    total_cases = len(cases)

    intent_correct = 0
    route_correct = 0
    response_mode_correct = 0
    fully_correct = 0

    mismatches: List[Dict[str, Any]] = []

    for case in cases:
        result = classify_with_policy(case["input_text"])
        data = result.model_dump()

        intent_ok = data["intent"] == case["expected_intent"]
        route_ok = data["route"] == case["expected_route"]
        response_mode_ok = data["response_mode"] == case["expected_response_mode"]

        topics_ok = True
        missing_topics: List[str] = []
        for expected_topic in case["expected_topics"]:
            if expected_topic not in data["topics"]:
                topics_ok = False
                missing_topics.append(expected_topic)

        if intent_ok:
            intent_correct += 1
        if route_ok:
            route_correct += 1
        if response_mode_ok:
            response_mode_correct += 1

        if intent_ok and route_ok and response_mode_ok and topics_ok:
            fully_correct += 1
        else:
            mismatches.append(
                {
                    "name": case["name"],
                    "input_text": case["input_text"],
                    "expected": {
                        "intent": case["expected_intent"],
                        "topics": case["expected_topics"],
                        "route": case["expected_route"],
                        "response_mode": case["expected_response_mode"],
                    },
                    "actual": {
                        "intent": data["intent"],
                        "topics": data["topics"],
                        "route": data["route"],
                        "response_mode": data["response_mode"],
                    },
                    "checks": {
                        "intent_ok": intent_ok,
                        "route_ok": route_ok,
                        "response_mode_ok": response_mode_ok,
                        "topics_ok": topics_ok,
                        "missing_topics": missing_topics,
                    },
                }
            )

    def _safe_ratio(numerator: int, denominator: int) -> float:
        if denominator == 0:
            return 0.0
        return numerator / denominator

    return {
        "total_cases": total_cases,
        "intent_accuracy": _safe_ratio(intent_correct, total_cases),
        "route_accuracy": _safe_ratio(route_correct, total_cases),
        "response_mode_accuracy": _safe_ratio(response_mode_correct, total_cases),
        "full_case_accuracy": _safe_ratio(fully_correct, total_cases),
        "mismatches": mismatches,
    }
