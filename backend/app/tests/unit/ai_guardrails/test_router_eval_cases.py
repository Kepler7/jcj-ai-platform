import pytest

from app.modules.ai_guardrails.sensitive_classifier import classify_with_policy
from app.tests.fixtures.ai_guardrails.router_eval_cases import ROUTER_EVAL_CASES


@pytest.mark.parametrize(
    "case", ROUTER_EVAL_CASES, ids=[case["name"] for case in ROUTER_EVAL_CASES]
)
def test_router_eval_cases(case):
    """
    Recorre el mini dataset del router y valida que la clasificación
    siga alineada con nuestras expectativas.

    ¿Qué valida?
    - intent
    - topics
    - route
    - response_mode

    Nota:
    En topics no exigimos igualdad exacta total del arreglo si luego
    en el futuro hubiera más de un topic. Aquí pedimos al menos que
    estén presentes los topics esperados.
    """
    result = classify_with_policy(case["input_text"])
    data = result.model_dump()

    assert data["intent"] == case["expected_intent"]
    assert data["route"] == case["expected_route"]
    assert data["response_mode"] == case["expected_response_mode"]

    for expected_topic in case["expected_topics"]:
        assert expected_topic in data["topics"]
