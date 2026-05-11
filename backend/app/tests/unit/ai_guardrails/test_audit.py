from app.modules.ai_guardrails.audit import build_guardrail_audit_payload


def test_build_guardrail_audit_payload_for_safeguarding_review():
    """
    Verifica que el payload de auditoría tenga la estructura esperada
    para un caso sensible legítimo.
    """
    input_guardrails_meta = {
        "safe": True,
        "should_block": False,
        "should_restrict": True,
        "risk_level": "high",
        "flags": ["pii_email"],
        "blocked_reason": None,
        "route": "safeguarding_review",
        "response_mode": "restricted_support",
        "human_review_required": True,
        "allow_rag": False,
        "allow_llm_generation": True,
        "classification": {
            "intent": "legitimate_sensitive_report",
            "topics": ["self_harm_suicidality"],
            "risk_level": "high",
            "route": "safeguarding_review",
            "response_mode": "restricted_support",
            "human_review_required": True,
            "allow_rag": False,
            "allow_llm_generation": True,
            "blocked_reason": None,
            "confidence": 0.93,
            "reasons": ["Caso sensible legítimo"],
        },
    }

    payload = build_guardrail_audit_payload(
        report_id="aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
        student_id="bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb",
        school_id="cccccccc-cccc-cccc-cccc-cccccccccccc",
        route="safeguarding_review",
        risk_level="high",
        input_guardrails_meta=input_guardrails_meta,
        sanitized_report_text="La maestra reporta que el alumno dijo que se quiere morir",
    )

    assert payload["event_type"] == "ai_input_guardrails_decision"
    assert payload["route"] == "safeguarding_review"
    assert payload["risk_level"] == "high"
    assert payload["should_block"] is False
    assert payload["should_restrict"] is True
    assert payload["response_mode"] == "restricted_support"
    assert payload["human_review_required"] is True
    assert payload["allow_rag"] is False
    assert payload["allow_llm_generation"] is True
    assert payload["classification_intent"] == "legitimate_sensitive_report"
    assert payload["classification_topics"] == ["self_harm_suicidality"]
    assert payload["classification_confidence"] == 0.93
    assert "se quiere morir" in payload["sanitized_report_preview"]
