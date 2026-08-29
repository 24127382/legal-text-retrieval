def get_context_for_position(record: dict, position: int) -> dict:
    current_part = None
    current_chapter = None
    current_section = None

    for unit in record["units"]:
        if unit["char_start"] > position:
            break

        level = unit.get("level")
        if level == "part":
            current_part = unit
            current_chapter = None
            current_section = None
        elif level == "chapter":
            current_chapter = unit
            current_section = None
        elif level == "section":
            current_section = unit

    return {
        "part_number": current_part["number"] if current_part else None,
        "part_title": current_part.get("title") if current_part else None,
        "chapter_number": current_chapter["number"] if current_chapter else None,
        "chapter_title": current_chapter.get("title") if current_chapter else None,
        "section_number": current_section["number"] if current_section else None,
        "section_title": current_section.get("title") if current_section else None,
    }