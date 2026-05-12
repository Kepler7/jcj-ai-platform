from .schemas import GuardrailResult
from .pii import redact_pii
from .sensitive_classifier import classify_with_policy


def run_guardrails(text: str) -> GuardrailResult:
    """
    Ejecuta los guardrails de entrada.

    Flujo actual:
    1. Redacta PII
    2. Clasifica el texto con la política contextual de IHUI
    3. Decide si el sistema puede seguir, restringirse o bloquearse

    Importante:
    - PII sola NO bloquea
    - safeguarding_review NO bloquea, pero sí marca restricción
    - block sí detiene el flujo normal
    """
    flags = []

    # ----------------------------
    # 1) Redacción de PII
    # ----------------------------
    redacted_text, pii_flags = redact_pii(text)
    flags.extend(pii_flags)

    # ----------------------------
    # 2) Clasificación contextual
    # ----------------------------
    classification = classify_with_policy(redacted_text)

    # Si el clasificador detectó prompt attack, lo reflejamos también
    # en flags para mantener compatibilidad con lo que ya veníamos usando.
    if classification.intent == "prompt_attack":
        flags.append("prompt_injection")

    # ----------------------------
    # 3) Riesgo final
    # ----------------------------
    # Regla:
    # - el riesgo principal lo manda la clasificación contextual
    # - pero si solo hubo PII y nada más, elevamos a medium
    risk_level = classification.risk_level
    if classification.risk_level == "low" and pii_flags:
        risk_level = "medium"

    # ----------------------------
    # 4) Seguridad final
    # ----------------------------
    # safe significa que NO estamos en bloqueo duro.
    # safeguarding_review sigue siendo "safe" para continuar en un flujo controlado.
    blocked_reason = classification.blocked_reason
    safe = classification.route != "block"

    return GuardrailResult(
        safe=safe,
        redacted_text=redacted_text,
        risk_level=risk_level,
        flags=flags,
        blocked_reason=blocked_reason,
        classification=classification,
    )
