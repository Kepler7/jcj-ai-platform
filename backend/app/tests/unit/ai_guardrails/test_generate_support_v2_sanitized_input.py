from app.ai.generate_support_v2 import generate_support_v2


def test_generate_support_v2_uses_sanitized_text_for_retrieval(monkeypatch):
    """
    Este test verifica que, cuando el input NO se bloquea,
    generate_support_v2 usa el texto sanitizado en el retrieval.

    Queremos probar específicamente que un email redactado
    sea el que viaje al siguiente paso del pipeline.
    """

    captured = {
        "report_text_used_in_retrieval": None,
    }

    class FakeClassification:
        def model_dump(self):
            return {
                "category": "safe",
                "confidence": 1.0,
            }

    class FakeInputGuardrailsResult:
        # Texto original con PII
        original_text = "El correo del tutor es test@gmail.com"

        # Texto sanitizado que DEBE usarse después
        sanitized_text = "El correo del tutor es [REDACTED_EMAIL]"

        safe = True
        should_block = False
        should_restrict = False
        risk_level = "medium"
        flags = ["pii_email"]
        blocked_reason = None
        route = "safe"
        response_mode = "normal"
        human_review_required = False
        allow_rag = True
        allow_llm_generation = True
        classification = FakeClassification()

    def fake_run_input_guardrails(_text):
        return FakeInputGuardrailsResult()

    def fake_retrieve_playbooks(store, report_text, n_results):
        """
        Aquí capturamos qué texto recibió el retrieval.
        Si todo está bien, debe ser el texto sanitizado.
        """
        captured["report_text_used_in_retrieval"] = report_text
        return []

    class FakePrediction:
        """
        Simulamos el objeto prediction mínimo que espera el flujo.
        """

        id = "fake-prediction-id"

    def fake_create_prediction(*args, **kwargs):
        return FakePrediction()

    def fake_build_general_fallback_response(report_text, age, prediction_id):
        """
        Simulamos la respuesta fallback final.
        También regresamos el report_text para verificarlo si queremos.
        """
        return {
            "teacher_version": {
                "summary": f"fallback teacher summary: {report_text}",
                "signals_detected": [],
                "microintervenciones": [],
            },
            "parent_version": {
                "summary": f"fallback parent summary: {report_text}",
                "signals_detected": [],
                "microintervenciones": [],
            },
            "guardrails": {
                "no_diagnosis_confirmed": True,
                "no_clinical_labels_confirmed": True,
            },
        }

    # Mock del pipeline de entrada
    monkeypatch.setattr(
        "app.ai.generate_support_v2.run_input_guardrails",
        fake_run_input_guardrails,
    )

    # Mock del retrieval para capturar el texto
    monkeypatch.setattr(
        "app.ai.generate_support_v2.retrieve_playbooks",
        fake_retrieve_playbooks,
    )

    # Mock de creación de prediction
    monkeypatch.setattr(
        "app.ai.generate_support_v2.create_ai_prediction",
        fake_create_prediction,
    )

    # Mock del fallback para no depender del resto del sistema
    monkeypatch.setattr(
        "app.ai.generate_support_v2.build_general_fallback_response",
        fake_build_general_fallback_response,
    )

    result = generate_support_v2(
        db=None,
        report_id="aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
        report_text="El correo del tutor es test@gmail.com",
        age=7,
        student_id="bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb",
        school_id="cccccccc-cccc-cccc-cccc-cccccccccccc",
    )

    # 1) Verificamos que retrieval usó el texto sanitizado
    assert (
        captured["report_text_used_in_retrieval"]
        == "El correo del tutor es [REDACTED_EMAIL]"
    )

    # 2) Verificamos que el meta trae los datos de guardrails
    assert result["meta"]["input_guardrails"]["safe"] is True
    assert result["meta"]["input_guardrails"]["should_block"] is False
    assert result["meta"]["input_guardrails"]["risk_level"] == "medium"
    assert "pii_email" in result["meta"]["input_guardrails"]["flags"]
