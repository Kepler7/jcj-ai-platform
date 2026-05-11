from typing import Dict, List, Set

from app.modules.ai_guardrails.injection import detect_injection
from app.modules.ai_guardrails.schemas import SensitiveClassificationResult


# ----------------------------
# Contexto de reporte legítimo
# ----------------------------
# Estas pistas sugieren que alguien está reportando
# una observación real de aula/casa, no pidiendo daño.
REPORT_CONTEXT_PATTERNS = [
    "la maestra reporta",
    "el maestro reporta",
    "el padre comenta",
    "la madre comenta",
    "el tutor comenta",
    "se observó",
    "se observo",
    "se detectó",
    "se detecto",
    "el alumno dijo",
    "la alumna dijo",
    "refiere",
    "presenta",
    "durante clase",
    "en casa",
    "en el salón",
    "en el salon",
]


# ----------------------------
# Solicitud legítima de ayuda
# ----------------------------
# Esto NO es peligroso por sí mismo.
# Son frases que sugieren que la persona busca apoyo o guía.
HELP_REQUEST_PATTERNS = [
    "qué hacer",
    "que hacer",
    "cómo apoyar",
    "como apoyar",
    "cómo abordar",
    "como abordar",
    "cómo acompañar",
    "como acompañar",
    "cómo intervenir",
    "como intervenir",
    "cómo hablar con",
    "como hablar con",
    "qué recomendaciones",
    "que recomendaciones",
    "cómo actuar",
    "como actuar",
]


# ----------------------------
# Solicitudes realmente peligrosas
# ----------------------------
# Ojo:
# aquí NO usamos palabras demasiado genéricas como "escribe" o "genera" solas,
# porque eso generaría muchos falsos positivos.
#
# La idea es detectar peticiones claramente peligrosas.
DANGEROUS_REQUEST_PATTERNS = [
    "dime cómo suicidarme",
    "dime como suicidarme",
    "cómo suicidarme",
    "como suicidarme",
    "cómo hacerme daño",
    "como hacerme daño",
    "cómo ocultar abuso",
    "como ocultar abuso",
    "sin que se den cuenta",
    "escribe contenido sexual explícito",
    "escribe contenido sexual explicito",
    "genera pornografía",
    "genera pornografia",
    "cómo lastimar",
    "como lastimar",
    "cómo golpear sin dejar marcas",
    "como golpear sin dejar marcas",
]


# ----------------------------
# Patrones por topic
# ----------------------------
# Esto es una primera aproximación para inferir temas.
# No es perfecto, pero ya está mejor alineado con contexto real.
TOPIC_PATTERNS: Dict[str, List[str]] = {
    "attention_learning": [
        "poner atención",
        "poner atencion",
        "atención",
        "atencion",
        "se distrae",
        "distracción",
        "distraccion",
        "concentrarse",
        "enfocarse",
        "seguir instrucciones",
        "aprendizaje",
    ],
    "behavior_regulation": [
        "berrinche",
        "berrinches",
        "impulsivo",
        "impulsiva",
        "se frustra",
        "desregula",
        "desregulación",
        "desregulacion",
        "conducta",
        "oposicionista",
    ],
    "social_interaction": [
        "socializar",
        "socializa",
        "interacción",
        "interaccion",
        "compañeros",
        "amistades",
        "jugar con otros",
        "turnos",
    ],
    "emotional_distress": [
        "ansiedad",
        "triste",
        "tristeza",
        "miedo",
        "angustia",
        "crisis emocional",
        "llora mucho",
        "nervioso",
        "nerviosa",
    ],
    "self_harm_suicidality": [
        "suicidio",
        "suicida",
        "quiere morir",
        "quiero morir",
        "matarse",
        "autolesión",
        "autolesion",
        "se corta",
        "se lastima",
        "hacerse daño",
        "hacerse dano",
        "hacerme daño",
        "hacerme dano",
    ],
    "sexual_content_exposure": [
        "pornografía",
        "pornografia",
        "contenido sexual",
        "vio porno",
        "vio pornografía",
        "vio pornografia",
        "material sexual",
    ],
    "sexual_abuse": [
        "abuso sexual",
        "tocamientos",
        "tocamiento",
        "acoso sexual",
        "violación",
        "violacion",
        "lo tocaron",
        "la tocaron",
    ],
    "physical_violence": [
        "golpes",
        "golpear",
        "violencia física",
        "violencia fisica",
        "agresión física",
        "agresion fisica",
        "amenaza",
        "amenazas",
        "lo lastimaron",
        "la lastimaron",
    ],
    "abuse_neglect": [
        "maltrato",
        "negligencia",
        "abuso",
        "descuido",
        "lo dejan solo",
        "la dejan sola",
        "sin comer",
    ],
}


# Topics que consideramos sensibles y que deben activar
# safeguarding_review o block según la intención.
SENSITIVE_TOPICS: Set[str] = {
    "self_harm_suicidality",
    "sexual_content_exposure",
    "sexual_abuse",
    "physical_violence",
    "abuse_neglect",
}


def _normalize_text(text: str) -> str:
    """
    Normaliza mínimamente el texto para comparación.

    Nota:
    No hacemos limpieza agresiva porque todavía queremos
    conservar el contenido lo más cercano al original.
    """
    return (text or "").lower().strip()


def _contains_any(text: str, patterns: List[str]) -> bool:
    """
    Devuelve True si encuentra alguno de los patrones en el texto.
    """
    return any(pattern in text for pattern in patterns)


def _infer_topics(text: str) -> List[str]:
    """
    Recorre TOPIC_PATTERNS y devuelve los topics detectados.

    Si no encuentra ninguno, regresa ["none"].
    """
    found_topics: List[str] = []

    for topic, patterns in TOPIC_PATTERNS.items():
        if _contains_any(text, patterns):
            found_topics.append(topic)

    return found_topics if found_topics else ["none"]


def _is_sensitive_topic_present(topics: List[str]) -> bool:
    """
    Indica si dentro de los topics detectados hay alguno sensible.
    """
    return any(topic in SENSITIVE_TOPICS for topic in topics)


def _looks_like_question_or_help_request(text: str) -> bool:
    """
    Heurística simple para detectar que el texto parece
    una solicitud legítima de ayuda o pregunta.

    Esto NO vuelve peligroso al texto.
    Solo nos ayuda a distinguir entre:
    - reporte
    - solicitud legítima de ayuda
    """
    if "?" in text or "¿" in text:
        return True

    return _contains_any(text, HELP_REQUEST_PATTERNS)


def classify_with_policy(text: str) -> SensitiveClassificationResult:
    """
    Clasificador contextual v1 para IHUI.

    Orden de decisión:
    1. prompt_attack -> block
    2. inferir topics
    3. distinguir si hay tema sensible
    4. decidir si es:
       - normal_educational_request
       - legitimate_sensitive_report
       - legitimate_sensitive_help_request
       - dangerous_request
       - prompt_attack

    Regla importante:
    Una frase como "cómo hacer" NO es peligrosa por sí sola.
    Solo nos preocupa de verdad cuando coexiste con un tema sensible
    y con una intención claramente riesgosa.
    """
    normalized_text = _normalize_text(text)

    # ----------------------------
    # 1) Prompt attack
    # ----------------------------
    injection_flags = detect_injection(normalized_text)
    if injection_flags:
        return SensitiveClassificationResult(
            intent="prompt_attack",
            topics=["none"],
            risk_level="high",
            route="block",
            response_mode="no_generation",
            human_review_required=False,
            allow_rag=False,
            allow_llm_generation=False,
            blocked_reason="prompt_injection_detected",
            confidence=0.99,
            reasons=[
                "Se detectó un intento de manipular las instrucciones del sistema."
            ],
        )

    # ----------------------------
    # 2) Inferir topics
    # ----------------------------
    topics = _infer_topics(normalized_text)
    has_sensitive_topic = _is_sensitive_topic_present(topics)

    has_report_context = _contains_any(normalized_text, REPORT_CONTEXT_PATTERNS)
    has_help_request_context = _looks_like_question_or_help_request(normalized_text)

    # Ojo:
    # solo nos interesa esta señal como verdaderamente peligrosa
    # cuando ya existe un tema sensible.
    has_dangerous_request_context = has_sensitive_topic and _contains_any(
        normalized_text, DANGEROUS_REQUEST_PATTERNS
    )

    # ----------------------------
    # 3) Solicitud peligrosa
    # ----------------------------
    if has_dangerous_request_context:
        return SensitiveClassificationResult(
            intent="dangerous_request",
            topics=topics,
            risk_level="high",
            route="block",
            response_mode="no_generation",
            human_review_required=False,
            allow_rag=False,
            allow_llm_generation=False,
            blocked_reason="dangerous_sensitive_request_detected",
            confidence=0.96,
            reasons=[
                "Se detectó un tema sensible.",
                "La intención parece pedir instrucciones o contenido peligroso.",
            ],
        )

    # ----------------------------
    # 4) Casos sensibles legítimos
    # ----------------------------
    if has_sensitive_topic:
        # Si parece pregunta o búsqueda de guía legítima,
        # lo tratamos como ayuda legítima.
        if has_help_request_context and not has_report_context:
            return SensitiveClassificationResult(
                intent="legitimate_sensitive_help_request",
                topics=topics,
                risk_level="high",
                route="safeguarding_review",
                response_mode="restricted_support",
                human_review_required=True,
                allow_rag=False,
                allow_llm_generation=True,
                blocked_reason=None,
                confidence=0.90,
                reasons=[
                    "Se detectó un tema sensible.",
                    "El texto parece buscar apoyo legítimo, no instrucciones dañinas.",
                ],
            )

        # Si parece reporte observacional, lo tratamos como reporte legítimo.
        if has_report_context:
            return SensitiveClassificationResult(
                intent="legitimate_sensitive_report",
                topics=topics,
                risk_level="high",
                route="safeguarding_review",
                response_mode="restricted_support",
                human_review_required=True,
                allow_rag=False,
                allow_llm_generation=True,
                blocked_reason=None,
                confidence=0.93,
                reasons=[
                    "Se detectó un tema sensible.",
                    "El texto parece un reporte legítimo de aula/casa.",
                ],
            )

        # Regla conservadora:
        # si hay tema sensible pero el contexto no es totalmente claro,
        # preferimos safeguarding_review en vez de bloquear.
        return SensitiveClassificationResult(
            intent="legitimate_sensitive_report",
            topics=topics,
            risk_level="high",
            route="safeguarding_review",
            response_mode="restricted_support",
            human_review_required=True,
            allow_rag=False,
            allow_llm_generation=True,
            blocked_reason=None,
            confidence=0.75,
            reasons=[
                "Se detectó un tema sensible.",
                "No hay evidencia suficiente de misuse; se prefiere revisión humana.",
            ],
        )

    # ----------------------------
    # 5) Caso normal educativo
    # ----------------------------
    return SensitiveClassificationResult(
        intent="normal_educational_request",
        topics=topics,
        risk_level="low" if topics != ["none"] else "medium",
        route="normal",
        response_mode="full_support",
        human_review_required=False,
        allow_rag=True,
        allow_llm_generation=True,
        blocked_reason=None,
        confidence=0.90 if topics != ["none"] else 0.65,
        reasons=[
            "No se detectaron temas sensibles de safeguarding.",
            "El texto parece corresponder a una solicitud educativa normal.",
        ],
    )
