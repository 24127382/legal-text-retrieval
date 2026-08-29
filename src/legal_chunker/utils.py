def unique_keep_order(values: list) -> list:
    seen = set()
    result = []
    for value in values:
        if value is None:
            continue
        if value not in seen:
            seen.add(value)
            result.append(value)
    return result


def get_units_by_level(units: list[dict], level: str) -> list[dict]:
    return [u for u in units if u.get("level") == level]