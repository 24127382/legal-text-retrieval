import re
from legal_chunker.config import HARD_LIMIT, TARGET_SIZE
from legal_chunker.schemas import ChunkUnit


def split_large_unit(
    unit: ChunkUnit,
    target_size: int = TARGET_SIZE,
) -> list[ChunkUnit]:
    text = unit.text
    if len(text) <= HARD_LIMIT:
        return [unit]

    matches = list(re.finditer(r"\S(?:.*?\S)?(?=\n\s*\n|\Z)", text, flags=re.DOTALL))

    if not matches:
        return _hard_char_split(unit, target_size)

    result = []
    current_matches = []
    current_length = 0

    for match in matches:
        p_text = match.group(0)
        p_len = len(p_text)

        if p_len > target_size:
            if current_matches:
                result.append(_create_sub_unit(unit, text, current_matches))
                current_matches = []
                current_length = 0

            sub_unit_temp = ChunkUnit(
                level=unit.level,
                number=unit.number,
                text=p_text,
                char_start=unit.char_start + match.start(),
                char_end=unit.char_start + match.end(),
                articles=unit.articles.copy(),
                clauses=unit.clauses.copy(),
                points=unit.points.copy(),
            )
            result.extend(_hard_char_split(sub_unit_temp, target_size))
            continue

        added_len = p_len if not current_matches else p_len + 2

        if current_length + added_len > target_size and current_matches:
            result.append(_create_sub_unit(unit, text, current_matches))
            current_matches = [match]
            current_length = p_len
        else:
            current_matches.append(match)
            current_length += added_len

    if current_matches:
        result.append(_create_sub_unit(unit, text, current_matches))

    return result


def _create_sub_unit(parent: ChunkUnit, parent_text: str, matches: list[re.Match]) -> ChunkUnit:
    rel_start = matches[0].start()
    rel_end = matches[-1].end()
    sub_text = parent_text[rel_start:rel_end]

    return ChunkUnit(
        level=parent.level,
        number=parent.number,
        text=sub_text,
        char_start=parent.char_start + rel_start,
        char_end=parent.char_start + rel_end,
        articles=parent.articles.copy(),
        clauses=parent.clauses.copy(),
        points=parent.points.copy(),
    )


def _hard_char_split(unit: ChunkUnit, target_size: int) -> list[ChunkUnit]:
    result = []
    text = unit.text
    for offset in range(0, len(text), target_size):
        part = text[offset : offset + target_size]
        if not part:
            continue
        result.append(
            ChunkUnit(
                level=unit.level,
                number=unit.number,
                text=part,
                char_start=unit.char_start + offset,
                char_end=unit.char_start + offset + len(part),
                articles=unit.articles.copy(),
                clauses=unit.clauses.copy(),
                points=unit.points.copy(),
            )
        )
    return result