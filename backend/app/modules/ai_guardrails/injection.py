INJECTION_PATTERNS = [
    # English
    "ignore previous instructions",
    "ignore all previous instructions",
    "act as",
    "system prompt",
    "reveal instructions",
    "reveal your instructions",
    "bypass",
    "jailbreak",
    # Spanish
    "ignora instrucciones anteriores",
    "ignora todas las instrucciones anteriores",
    "actua como",
    "actúa como",
    "prompt del sistema",
    "revela las instrucciones",
    "revela tus instrucciones",
    "omite las reglas",
    "saltate las reglas",
    "sáltate las reglas",
]


def detect_injection(text: str):
    text_lower = text.lower()
    flags = []

    for pattern in INJECTION_PATTERNS:
        if pattern in text_lower:
            flags.append("prompt_injection")
            break

    return flags


def detect_injection(text: str):
    text_lower = text.lower()
    flags = []

    for pattern in INJECTION_PATTERNS:
        if pattern in text_lower:
            flags.append("prompt_injection")

    return flags
