import re


EMAIL_REGEX = r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+"
PHONE_REGEX = r"\b\d{10}\b"


def redact_pii(text: str):
    flags = []

    # Email
    if re.search(EMAIL_REGEX, text):
        text = re.sub(EMAIL_REGEX, "[REDACTED_EMAIL]", text)
        flags.append("pii_email")

    # Phone
    if re.search(PHONE_REGEX, text):
        text = re.sub(PHONE_REGEX, "[REDACTED_PHONE]", text)
        flags.append("pii_phone")

    return text, flags
