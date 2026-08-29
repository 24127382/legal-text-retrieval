from legal_chunker.config import HARD_LIMIT, SOFT_LIMIT
from legal_chunker.schemas import ChunkUnit
from legal_chunker.splitters import split_large_unit


def pack_units(units: list[ChunkUnit]) -> list[list[ChunkUnit]]:
    chunks = []
    current = []
    current_length = 0

    for unit in units:
        unit_length = len(unit.text)

        if unit_length > HARD_LIMIT:
            if current:
                chunks.append(current)
                current = []
                current_length = 0

            split_units = split_large_unit(unit)
            for split_unit in split_units:
                chunks.append([split_unit])
            continue

        if not unit.text.strip():
            continue

        if not current:
            current = [unit]
            current_length = unit_length
            continue

        proposed_length = current_length + 2 + unit_length
        if proposed_length <= SOFT_LIMIT:
            current.append(unit)
            current_length = proposed_length
        else:
            chunks.append(current)
            current = [unit]
            current_length = unit_length

    if current:
        chunks.append(current)

    return chunks