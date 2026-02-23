from __future__ import annotations

import math
import re
from collections import Counter
from typing import List, Tuple

_TOKEN_RE = re.compile(r"[a-záéíóúñü0-9]+", re.IGNORECASE)

_STOPWORDS_ES = {
    "a",
    "al",
    "algo",
    "algunas",
    "algunos",
    "ante",
    "antes",
    "como",
    "con",
    "contra",
    "cual",
    "cuales",
    "cuando",
    "de",
    "del",
    "desde",
    "donde",
    "dos",
    "el",
    "ella",
    "ellas",
    "ellos",
    "en",
    "entre",
    "es",
    "esa",
    "esas",
    "ese",
    "eso",
    "esos",
    "esta",
    "estaba",
    "estaban",
    "estan",
    "estar",
    "estas",
    "este",
    "esto",
    "estos",
    "fue",
    "ha",
    "hace",
    "hacen",
    "hacer",
    "hacia",
    "han",
    "hasta",
    "hay",
    "he",
    "hemos",
    "la",
    "las",
    "le",
    "les",
    "lo",
    "los",
    "mas",
    "me",
    "mi",
    "mis",
    "mucha",
    "muchas",
    "mucho",
    "muchos",
    "muy",
    "no",
    "nos",
    "o",
    "os",
    "otra",
    "otras",
    "otro",
    "otros",
    "para",
    "pero",
    "por",
    "porque",
    "que",
    "quien",
    "quienes",
    "se",
    "sea",
    "ser",
    "si",
    "sin",
    "sobre",
    "su",
    "sus",
    "tambien",
    "te",
    "ti",
    "tiene",
    "tienen",
    "todo",
    "todos",
    "tu",
    "tus",
    "un",
    "una",
    "uno",
    "unos",
    "unas",
    "y",
    "ya",
    "alumno",
    "alumna",
    "grupo",
    "años",
    "anio",
    "pre",
    "k",
    "prek",
    "pre-k",
    "fortalezas",
    "retos",
    "notas",
    "señales",
    "senales",
    "observables",
    "opcional",
}


def _tokenize(text: str) -> List[str]:
    if not text:
        return []
    toks = _TOKEN_RE.findall(text.lower())
    out: List[str] = []
    for t in toks:
        if t in _STOPWORDS_ES:
            continue
        if len(t) <= 2:
            continue
        out.append(t)
    return out


def bm25_rank(
    query: str,
    docs: List[str],
    *,
    k1: float = 1.5,
    b: float = 0.75,
    top_k: int | None = None,
) -> List[Tuple[int, float]]:
    if not docs:
        return []

    q_tokens = _tokenize(query)
    if not q_tokens:
        out = [(i, 0.0) for i in range(len(docs))]
        return out[:top_k] if top_k else out

    doc_tokens = [_tokenize(d) for d in docs]
    doc_lens = [len(toks) for toks in doc_tokens]
    avgdl = (sum(doc_lens) / max(1, len(doc_lens))) or 1.0

    df = Counter()
    for toks in doc_tokens:
        for term in set(toks):
            df[term] += 1

    N = len(docs)

    def idf(term: str) -> float:
        n_q = df.get(term, 0)
        return math.log(1 + (N - n_q + 0.5) / (n_q + 0.5))

    q_counts = Counter(q_tokens)
    scores: List[Tuple[int, float]] = []

    for i, toks in enumerate(doc_tokens):
        if not toks:
            scores.append((i, 0.0))
            continue

        tf = Counter(toks)
        dl = doc_lens[i] or 1
        score = 0.0

        for term, qf in q_counts.items():
            f = tf.get(term, 0)
            if f == 0:
                continue
            term_idf = idf(term)
            denom = f + k1 * (1 - b + b * (dl / avgdl))
            score += (term_idf * (f * (k1 + 1) / denom)) * qf

        scores.append((i, score))

    scores.sort(key=lambda x: x[1], reverse=True)
    return scores[:top_k] if top_k else scores


def bm25_coverage(query: str, doc: str) -> float:
    q = set(_tokenize(query))
    if not q:
        return 0.0
    d = set(_tokenize(doc))
    return len(q & d) / len(q)
