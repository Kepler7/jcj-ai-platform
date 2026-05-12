from app.ai.generate_support_v2 import generate_support_v2


def test_generate_support_v2_returns_early_for_safeguarding_review(monkeypatch):
    """
    Verifica que si el input cae en safeguarding_review:
    - generate_support_v2 NO entra al flujo normal
    - devuelve respuesta restringida
    - no intenta retrieval
    """

    class FakeClassification:
        def __init__(self):
            self.intent = "legitimate_sensitive_report"
            self.topics = ["self_harm_suicidality"]
            self.risk_level = "high"
            self.route = "safeguarding_review"
            self.response_mode = "restricted_support"
            self.human_review_required = True
            self.allow_rag = False
            self.allow_llm_generation = True
            self.blocked_reason = None
            self.confidence = 0.93
            self.reasons = ["Caso sensible legítimo"]

        def model_dump(self):
            return {
                "intent": self.intent,
                "topics": self.topics,
                "risk_level": self.risk_level,
                "route": self.route,
                "response_mode": self.response_mode,
                "human_review_required": self.human_review_required,
                "allow_rag": self.allow_rag,
                "allow_llm_generation": self.allow_llm_generation,
                "blocked_reason": self.blocked_reason,
                "confidence": self.confidence,
                "reasons": self.reasons,
            }

    class FakeInputGuardrailsResult:
        original_text = "La maestra reporta que el alumno dijo que se quiere morir"
        sanitized_text = "La maestra reporta que el alumno dijo que se quiere morir"
        safe = True
        should_block = False
        should_restrict = True
        risk_level = "high"
        flags = []
        blocked_reason = None
        route = "safeguarding_review"
        response_mode = "restricted_support"
        human_review_required = True
        allow_rag = False
        allow_llm_generation = True
        classification = FakeClassification()

    def fake_run_input_guardrails(_text):
        return FakeInputGuardrailsResult()

    def fake_retrieve_playbooks(*args, **kwargs):
        raise AssertionError(
            "retrieve_playbooks no debería ejecutarse en safeguarding_review"
        )

    monkeypatch.setattr(
        "app.ai.generate_support_v2.run_input_guardrails",
        fake_run_input_guardrails,
    )

    monkeypatch.setattr(
        "app.ai.generate_support_v2.retrieve_playbooks",
        fake_retrieve_playbooks,
    )

    result = generate_support_v2(
        db=None,
        report_id="aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
        report_text="La maestra reporta que el alumno dijo que se quiere morir",
        age=7,
        student_id="bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb",
        school_id="cccccccc-cccc-cccc-cccc-cccccccccccc",
    )

    assert result["status"] == "safeguarding_review"
    assert result["prediction_id"] is None
    assert result["meta"]["prediction_status"] == "safeguarding_review"
    assert result["meta"]["input_guardrails"]["should_restrict"] is True
    assert result["meta"]["input_guardrails"]["route"] == "safeguarding_review"
    assert result["meta"]["input_guardrails"]["response_mode"] == "restricted_support"

    support = result["support"]
    assert support.teacher_version.microintervenciones == []
    assert support.parent_version.microintervenciones == []
    assert "self_harm_suicidality" in support.teacher_version.signals_detected
