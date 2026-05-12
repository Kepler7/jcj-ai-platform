from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from typing import List

from app.modules.ihui_3.schemas import IHUI3DictionaryItem, IHUI3KnowledgeItem


@dataclass
class IHUI3MatchResult:
    """
    Resultado interno del matcher IHUI 3.0.

    knowledge_item:
        La fila del conocimiento IHUI 3.0 que mejor coincide con el reporte.

    score:
        Score normalizado entre 0 y 1.

    matched_terms:
        Términos del conocimiento que aparecieron o se parecieron al reporte.

    reason:
        Explicación técnica simple del match.
    """

    knowledge_item: IHUI3KnowledgeItem
    score: float
    matched_terms: list[str]
    reason: str


def normalize_text(value: str) -> str:
    """
    Normaliza texto para comparar mejor:
    - minúsculas
    - sin acentos
    - sin puntuación especial
    - espacios compactados

    Ejemplo:
    "Se distrae rápido." -> "se distrae rapido"
    """
    if not value:
        return ""

    text = value.lower().strip()

    # Quitar acentos
    text = unicodedata.normalize("NFD", text)
    text = "".join(char for char in text if unicodedata.category(char) != "Mn")

    # Reemplazar puntuación por espacios
    text = re.sub(r"[^a-z0-9ñ\s]", " ", text)

    # Compactar espacios
    text = re.sub(r"\s+", " ", text).strip()

    return text


def tokenize(value: str) -> set[str]:
    """
    Convierte texto en tokens útiles.

    Quitamos palabras muy comunes para que no inflen el score.
    """
    normalized = normalize_text(value)

    stopwords = {
        "el",
        "la",
        "los",
        "las",
        "un",
        "una",
        "unos",
        "unas",
        "de",
        "del",
        "al",
        "a",
        "en",
        "con",
        "por",
        "para",
        "y",
        "o",
        "que",
        "se",
        "su",
        "sus",
        "lo",
        "le",
        "les",
        "no",
        "si",
        "es",
        "son",
        "esta",
        "este",
        "esto",
        "muy",
        "mas",
        "menos",
        "cuando",
        "como",
        "pero",
        "tambien",
    }

    return {
        token
        for token in normalized.split()
        if len(token) >= 3 and token not in stopwords
    }


def get_item_terms(item: IHUI3KnowledgeItem) -> list[str]:
    """
    Junta los campos más importantes del conocimiento para comparar.

    No usamos todas las columnas con el mismo peso todavía,
    pero sí incluimos las más útiles para detectar el caso.
    """
    terms: list[str] = []

    terms.extend(item.observable_signals)
    terms.extend(item.observable_triggers)
    terms.extend(item.functional_hypotheses)

    if item.nucleus:
        terms.append(item.nucleus)

    if item.subskill:
        terms.append(item.subskill)

    if item.micro_objective:
        terms.append(item.micro_objective)

    return [term for term in terms if term and term.strip()]


def score_item(report_text: str, item: IHUI3KnowledgeItem) -> tuple[float, list[str]]:
    """
    Calcula un score simple entre el reporte y una fila IHUI 3.0.

    Estrategia:
    - Si una frase completa aparece en el reporte, suma más.
    - Si comparte tokens importantes, suma parcialmente.
    """
    normalized_report = normalize_text(report_text)
    report_tokens = tokenize(report_text)

    terms = get_item_terms(item)

    if not terms:
        return 0.0, []

    total_score = 0.0
    matched_terms: list[str] = []

    for term in terms:
        normalized_term = normalize_text(term)
        term_tokens = tokenize(term)

        if not normalized_term or not term_tokens:
            continue

        # Match fuerte: la frase completa aparece en el reporte.
        if normalized_term in normalized_report:
            total_score += 2.0
            matched_terms.append(term)
            continue

            # Match parcial: overlap de tokens.
        overlap = report_tokens.intersection(term_tokens)

        if overlap:
            overlap_ratio = len(overlap) / max(len(term_tokens), 1)

            # Regla importante:
            # No aceptamos matches parciales por una sola palabra.
            # Ejemplo falso positivo:
            # "trajo su tarea completa" vs "No entiende la tarea"
            #
            # Para evitar eso, pedimos al menos 2 tokens coincidentes
            # o una frase completa exacta, que ya fue detectada arriba.
            if len(overlap) >= 2 and overlap_ratio >= 0.5:
                total_score += overlap_ratio
                matched_terms.append(term)

    # Normalización simple.
    # El máximo teórico depende de cuántos términos tenga cada item.
    # Para este MVP usamos una escala conservadora.
    normalized_score = min(total_score / 5.0, 1.0)

    return normalized_score, matched_terms


def find_top_matches(
    *,
    report_text: str,
    knowledge_items: List[IHUI3KnowledgeItem],
    dictionary_items: list[IHUI3DictionaryItem] | None = None,
    minimum_score: float = 0.30,
    limit: int = 3,
) -> list[IHUI3MatchResult]:
    """
    Encuentra los mejores candidatos IHUI 3.0 para un reporte.

    Regresa una lista ordenada de mayor a menor score.
    Solo incluye candidatos que superan minimum_score.

    Esto se usa para el wizard IHUI 3.0:
    - top 2 candidatos -> 2 preguntas por candidato, si ambos tienen suficientes preguntas
    - top 3 candidatos -> 1 pregunta por candidato
    """

    results: list[IHUI3MatchResult] = []

    for item in knowledge_items:
        score, matched_terms = score_item(report_text, item)

        dictionary_boost, dictionary_matches = dictionary_boost_for_item(
            report_text=report_text,
            item=item,
            dictionary_items=dictionary_items,
        )

        score = min(score + dictionary_boost, 1.0)
        matched_terms = matched_terms + [
            f"diccionario:{term}" for term in dictionary_matches
        ]

        if score < minimum_score:
            continue

        reason = (
            f"Se seleccionó '{item.nucleus} / {item.subskill}' "
            f"con score={score:.2f}. "
            f"Términos coincidentes: {', '.join(matched_terms[:5]) or 'ninguno'}."
        )

        results.append(
            IHUI3MatchResult(
                knowledge_item=item,
                score=score,
                matched_terms=matched_terms,
                reason=reason,
            )
        )

    results.sort(key=lambda result: result.score, reverse=True)

    return results[:limit]


def find_best_match(
    *,
    report_text: str,
    knowledge_items: List[IHUI3KnowledgeItem],
    dictionary_items: list[IHUI3DictionaryItem] | None = None,
    minimum_score: float = 0.30,
) -> IHUI3MatchResult | None:
    """
    Encuentra la mejor fila IHUI 3.0 para un reporte.

    Se mantiene para compatibilidad con código existente.
    Internamente usa find_top_matches(limit=1).
    """

    top_matches = find_top_matches(
        report_text=report_text,
        knowledge_items=knowledge_items,
        dictionary_items=dictionary_items,
        minimum_score=minimum_score,
        limit=1,
    )

    if not top_matches:
        return None

    return top_matches[0]


def dictionary_boost_for_item(
    *,
    report_text: str,
    item: IHUI3KnowledgeItem,
    dictionary_items: list[IHUI3DictionaryItem] | None,
) -> tuple[float, list[str]]:
    if not dictionary_items:
        return 0.0, []

    normalized_report = normalize_text(report_text)

    boost = 0.0
    matched_expressions: list[str] = []

    item_nucleus = normalize_text(item.nucleus)
    item_subskill = normalize_text(item.subskill)
    item_terms = tokenize(
        " ".join(
            [
                item.nucleus,
                item.subskill,
                item.micro_objective,
                " ".join(item.observable_signals),
            ]
        )
    )

    for dictionary_item in dictionary_items:
        expression = normalize_text(dictionary_item.expression)

        if not expression:
            continue

        if expression not in normalized_report:
            continue

        dictionary_nucleus = normalize_text(dictionary_item.nucleus)
        dictionary_subskill = normalize_text(dictionary_item.subskill)
        canonical_tokens = tokenize(dictionary_item.canonical_signal)

        same_nucleus = dictionary_nucleus and dictionary_nucleus == item_nucleus
        same_subskill = dictionary_subskill and dictionary_subskill == item_subskill
        canonical_overlap = item_terms.intersection(canonical_tokens)

        if same_nucleus and same_subskill:
            boost += 0.35
            matched_expressions.append(dictionary_item.expression)
        elif same_nucleus:
            boost += 0.20
            matched_expressions.append(dictionary_item.expression)
        elif len(canonical_overlap) >= 2:
            boost += 0.20
            matched_expressions.append(dictionary_item.expression)

    return boost, matched_expressions
