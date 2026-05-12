from app.ai.generate_support_v2 import generate_support_v2


def test_generate_support_v2_logs_router_decision(monkeypatch):
    """
    Verifica que generate_support_v2 emita un log de auditoría
    cuando procesa la decisión del router de entrada.
    """

    logged = {
        "called": False,
        "message": None,
        "payload": None,
    }

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

    def fake_logger_info(message, payload):
        """
        Capturamos los argumentos con los que se llamó logger.info(...)
        """
        logged["called"] = True
        logged["message"] = message
        logged["payload"] = payload

    monkeypatch.setattr(
        "app.ai.generate_support_v2.run_input_guardrails",
        fake_run_input_guardrails,
    )

    monkeypatch.setattr(
        "app.ai.generate_support_v2.logger.info",
        fake_logger_info,
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

    # Verificamos que el logger sí fue llamado
    assert logged["called"] is True

    # Verificamos el mensaje base
    assert logged["message"] == "AI guardrails/router decision: %s"

    # Verificamos que el payload serializado contiene algo clave
    assert "safeguarding_review" in logged["payload"]
    assert "self_harm_suicidality" in logged["payload"]
