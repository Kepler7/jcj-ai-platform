def looks_like_phone_e164(phone: str) -> bool:
    """
    Validación MVP: no perfecta.
    Acepta:
      - +5213312345678
      - 3312345678
    Rechaza strings muy raros.
    """
    p = phone.strip()
    if p.startswith("+"):
        p = p[1:]
    return p.isdigit() and 8 <= len(p) <= 15
