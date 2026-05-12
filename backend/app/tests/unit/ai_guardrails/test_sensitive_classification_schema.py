import pytest
from pydantic import ValidationError

from app.modules.ai_guardrails.schemas import SensitiveClassificationResult


def test_sensitive_classification_schema_accepts_valid_normal_case():
    """
    Verifica que un caso normal válido pase correctamente.
    """
    result = SensitiveClassificationResult(
        intent="normal_educational_request",
        topics=["attention_learning"],
        risk_level="low",
        route="normal",
        response_mode="full_support",
        human_review_required=False,
        allow_rag=True,
        allow_llm_generation=True,
        blocked_reason=None,
        confidence=0.92,
        reasons=["Caso educativo normal sin señales sensibles."],
    )

    data = result.model_dump()

    assert data["intent"] == "normal_educational_request"
    assert data["topics"] == ["attention_learning"]
    assert data["route"] == "normal"
    assert data["response_mode"] == "full_support"
    assert data["allow_rag"] is True
    assert data["allow_llm_generation"] is True


def test_sensitive_classification_schema_accepts_valid_safeguarding_case():
    """
    Verifica que un caso sensible legítimo también pase.
    """
    result = SensitiveClassificationResult(
        intent="legitimate_sensitive_report",
        topics=["self_harm_suicidality"],
        risk_level="high",
        route="safeguarding_review",
        response_mode="restricted_support",
        human_review_required=True,
        allow_rag=False,
        allow_llm_generation=True,
        blocked_reason=None,
        confidence=0.95,
        reasons=[
            "El texto parece un reporte legítimo.",
            "Se detecta un tema de alto riesgo.",
        ],
    )

    data = result.model_dump()

    assert data["intent"] == "legitimate_sensitive_report"
    assert data["topics"] == ["self_harm_suicidality"]
    assert data["route"] == "safeguarding_review"
    assert data["response_mode"] == "restricted_support"
    assert data["human_review_required"] is True
    assert data["allow_rag"] is False
    assert data["allow_llm_generation"] is True


def test_sensitive_classification_schema_accepts_valid_block_case():
    """
    Verifica que un caso peligroso/bloqueado sea válido.
    """
    result = SensitiveClassificationResult(
        intent="dangerous_request",
        topics=["sexual_content_exposure"],
        risk_level="high",
        route="block",
        response_mode="no_generation",
        human_review_required=False,
        allow_rag=False,
        allow_llm_generation=False,
        blocked_reason="sexual_content_request_detected",
        confidence=0.97,
        reasons=["El texto solicita contenido peligroso o impropio."],
    )

    data = result.model_dump()

    assert data["route"] == "block"
    assert data["response_mode"] == "no_generation"
    assert data["allow_rag"] is False
    assert data["allow_llm_generation"] is False
    assert data["blocked_reason"] == "sexual_content_request_detected"


def test_sensitive_classification_schema_rejects_invalid_intent():
    """
    No debe aceptar intents inventados.
    """
    with pytest.raises(ValidationError):
        SensitiveClassificationResult(
            intent="random_intent",
            topics=["attention_learning"],
            risk_level="low",
            route="normal",
            response_mode="full_support",
            human_review_required=False,
            allow_rag=True,
            allow_llm_generation=True,
            blocked_reason=None,
            confidence=0.80,
            reasons=[],
        )


def test_sensitive_classification_schema_rejects_invalid_topic():
    """
    No debe aceptar topics fuera de la taxonomía.
    """
    with pytest.raises(ValidationError):
        SensitiveClassificationResult(
            intent="normal_educational_request",
            topics=["made_up_topic"],
            risk_level="low",
            route="normal",
            response_mode="full_support",
            human_review_required=False,
            allow_rag=True,
            allow_llm_generation=True,
            blocked_reason=None,
            confidence=0.80,
            reasons=[],
        )


def test_sensitive_classification_schema_rejects_confidence_out_of_range():
    """
    confidence debe estar entre 0 y 1.
    """
    with pytest.raises(ValidationError):
        SensitiveClassificationResult(
            intent="normal_educational_request",
            topics=["attention_learning"],
            risk_level="low",
            route="normal",
            response_mode="full_support",
            human_review_required=False,
            allow_rag=True,
            allow_llm_generation=True,
            blocked_reason=None,
            confidence=1.5,
            reasons=[],
        )
