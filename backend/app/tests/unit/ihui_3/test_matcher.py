from app.modules.ihui_3.matcher import find_top_matches
from app.modules.ihui_3.schemas import IHUI3KnowledgeItem


def make_item(
    *,
    nucleus: str,
    subskill: str,
    observable_signals: list[str],
    micro_objective: str = "",
) -> IHUI3KnowledgeItem:
    return IHUI3KnowledgeItem(
        row_id=f"{nucleus}-{subskill}",
        nucleus=nucleus,
        subskill=subskill,
        observable_signals=observable_signals,
        observable_triggers=[],
        functional_hypotheses=[],
        validation_questions=["Pregunta 1", "Pregunta 2"],
        micro_objective=micro_objective,
        strategy_steps=[],
        frequency="",
        duration="",
        progress_indicator="",
        escalation="",
    )


def test_find_top_matches_returns_sorted_candidates():
    report_text = (
        "El alumno se distrae rápido, necesita muchos recordatorios "
        "y le cuesta mantenerse en la actividad."
    )

    attention_item = make_item(
        nucleus="Atención",
        subskill="Permanencia en tarea",
        observable_signals=[
            "se distrae rápido",
            "necesita muchos recordatorios",
            "le cuesta mantenerse en la actividad",
        ],
    )

    comprehension_item = make_item(
        nucleus="Comprensión",
        subskill="Seguimiento de instrucciones",
        observable_signals=[
            "necesita que se repita la instrucción",
            "mejora cuando se le explica individualmente",
        ],
    )

    language_item = make_item(
        nucleus="Lenguaje",
        subskill="Articulación",
        observable_signals=[
            "omite sonidos al hablar",
            "sustituye fonemas",
        ],
    )

    results = find_top_matches(
        report_text=report_text,
        knowledge_items=[
            language_item,
            comprehension_item,
            attention_item,
        ],
        dictionary_items=[],
        minimum_score=0.1,
        limit=3,
    )

    assert len(results) >= 1
    assert results[0].knowledge_item.nucleus == "Atención"
    assert results[0].knowledge_item.subskill == "Permanencia en tarea"

    scores = [result.score for result in results]
    assert scores == sorted(scores, reverse=True)
