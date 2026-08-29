import re
from legal_chunker.schemas import ChunkUnit
from legal_chunker.utils import get_units_by_level, unique_keep_order


def build_article_units(record: dict) -> list[ChunkUnit]:
    text = record["text"]
    units = record["units"]
    article_units = get_units_by_level(units, "article")

    result = []
    for article in article_units:
        start = article["char_start"]
        end = article["char_end"]
        article_text = text[start:end]
        article_number = article.get("number")

        clauses = [
            u["number"] for u in units
            if start <= u["char_start"] < end and u["level"] == "clause"
        ]
        points = [
            u["number"] for u in units
            if start <= u["char_start"] < end and u["level"] == "point"
        ]

        result.append(
            ChunkUnit(
                level="article",
                number=article_number,
                text=article_text,
                char_start=start,
                char_end=end,
                articles=[article_number] if article_number else [],
                clauses=unique_keep_order(clauses),
                points=unique_keep_order(points),
            )
        )
    return result


def build_clause_units(record: dict) -> list[ChunkUnit]:
    text = record["text"]
    units = record["units"]
    clause_units = get_units_by_level(units, "clause")

    result = []
    for clause in clause_units:
        start = clause["char_start"]
        end = clause["char_end"]
        clause_text = text[start:end]

        points = [
            u["number"] for u in units
            if start <= u["char_start"] < end and u["level"] == "point"
        ]

        result.append(
            ChunkUnit(
                level="clause",
                number=clause.get("number"),
                text=clause_text,
                char_start=start,
                char_end=end,
                articles=[],
                clauses=[clause["number"]] if clause.get("number") else [],
                points=unique_keep_order(points),
            )
        )
    return result


def build_paragraph_units(record: dict) -> list[ChunkUnit]:
    text = record["text"]
    matches = list(re.finditer(r"\S(?:.*?\S)?(?=\n\s*\n|\Z)", text, flags=re.DOTALL))

    result = []
    for match in matches:
        start, end = match.span()
        paragraph = text[start:end]
        if not paragraph.strip():
            continue

        result.append(
            ChunkUnit(
                level="paragraph",
                number=None,
                text=paragraph,
                char_start=start,
                char_end=end,
                articles=[],
                clauses=[],
                points=[],
            )
        )
    return result


def build_packing_units(record: dict) -> list[ChunkUnit]:
    fingerprint = record.get("fingerprint", [])

    if "article" in fingerprint:
        units = build_article_units(record)
        if units:
            return units

    if "clause" in fingerprint:
        units = build_clause_units(record)
        if units:
            return units

    return build_paragraph_units(record)