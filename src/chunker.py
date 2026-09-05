from __future__ import annotations
import re
from typing import Any, Dict, List, Optional
from src.schema import ChunkRecord, ChunkUnit

def unique_keep_order(values: List[Any]) -> List[Any]:
    seen = set()
    result = []
    for value in values:
        if value is not None and value not in seen:
            seen.add(value)
            result.append(value)
    return result

def context_at_position(sorted_units: List[Dict[str, Any]], position: int) -> Dict[str, Optional[str]]:
    ctx = {
        "part_number": None, "part_title": None,
        "chapter_number": None, "chapter_title": None,
        "section_number": None, "section_title": None
    }
    for u in sorted_units:
        if u.get("char_start", 0) > position:
            break
        level = u.get("level")
        if level == "part":
            ctx["part_number"] = u.get("number")
            ctx["part_title"] = u.get("title")
        elif level == "chapter":
            ctx["chapter_number"] = u.get("number")
            ctx["chapter_title"] = u.get("title")
            ctx["section_number"] = None
            ctx["section_title"] = None
        elif level == "section":
            ctx["section_number"] = u.get("number")
            ctx["section_title"] = u.get("title")
    return ctx

def make_unit(text: str, start: int, end: int, level: str, articles=None, clauses=None, points=None, context=None, number=None) -> ChunkUnit:
    context = context or {}
    return ChunkUnit(
        level=level,
        number=number,
        text=text[start:end],
        char_start=start,
        char_end=end,
        articles=unique_keep_order(articles or []),
        clauses=unique_keep_order(clauses or []),
        points=unique_keep_order(points or []),
        **context
    )

def hard_char_split(text: str, start: int, end: int, articles: List[str], clauses: List[str], points: List[str], context: Dict[str, Any], target_size: int) -> List[ChunkUnit]:
    out = []
    cursor = start
    while cursor < end:
        nxt = min(cursor + target_size, end)
        num = articles[-1] if articles else (clauses[-1] if clauses else None)
        out.append(make_unit(text, cursor, nxt, "hard_char", articles, clauses, points, context, num))
        cursor = nxt
    return out

def paragraph_split(text: str, start: int, end: int, units_meta: List[Dict[str, Any]], articles: List[str], clauses: List[str], points: List[str], context: Dict[str, Any], target_size: int, hard_limit: int) -> List[ChunkUnit]:
    if start >= end:
        return []
    boundaries = [start]
    for m in re.finditer(r"\n\s*\n|\n", text[start:end]):
        boundaries.append(start + m.end())
    boundaries.append(end)
    boundaries = sorted(set(x for x in boundaries if start <= x <= end))
    
    out = []
    cursor = start
    for b in boundaries[1:]:
        if b <= cursor:
            continue
        seg_len = b - cursor
        num = articles[-1] if articles else (clauses[-1] if clauses else None)
        
        if seg_len > hard_limit:
            out.extend(hard_char_split(text, cursor, b, articles, clauses, points, context, target_size))
        else:
            out.append(make_unit(text, cursor, b, "paragraph", articles, clauses, points, context, num))
        cursor = b

    return out

def decompose_range(text: str, start: int, end: int, level: str, units_meta: List[Dict[str, Any]], parent_articles: List[str], parent_clauses: List[str], parent_points: List[str], context: Dict[str, Any], target_size: int, hard_limit: int) -> List[ChunkUnit]:
    if end <= start:
        return []
    if end - start <= hard_limit:
        num = parent_articles[-1] if parent_articles else (parent_clauses[-1] if parent_clauses else None)
        return [make_unit(text, start, end, level, parent_articles, parent_clauses, parent_points, context, num)]

    next_level = {"document": "clause", "article": "clause", "clause": "paragraph"}.get(level, "hard_char")
    subs = sorted([u for u in units_meta if u.get("level") == next_level and start <= u.get("char_start", -1) < end], key=lambda u: u["char_start"])
    
    if not subs:
        if next_level == "paragraph":
            return paragraph_split(text, start, end, units_meta, parent_articles, parent_clauses, parent_points, context, target_size, hard_limit)
        return hard_char_split(text, start, end, parent_articles, parent_clauses, parent_points, context, target_size)

    out = []
    cursor = start
    for i, u in enumerate(subs):
        u_start = max(cursor, u["char_start"])
        if cursor < u_start:
            out.extend(decompose_range(text, cursor, u_start, next_level, units_meta, parent_articles, parent_clauses, parent_points, context, target_size, hard_limit))
        eff_end = subs[i + 1]["char_start"] if i + 1 < len(subs) else end
        eff_end = max(u_start, min(eff_end, end))
        
        n_art = list(parent_articles)
        n_cls = list(parent_clauses)
        n_pts = list(parent_points)
        num = u.get("number")
        if u.get("level") == "article" and num:
            n_art.append(num)
        if u.get("level") == "clause" and num:
            n_cls.append(num)
        if u.get("level") == "point" and num:
            n_pts.append(num)
            
        out.extend(decompose_range(text, u_start, eff_end, next_level, units_meta, unique_keep_order(n_art), unique_keep_order(n_cls), unique_keep_order(n_pts), context, target_size, hard_limit))
        cursor = eff_end
        
    if cursor < end:
        out.extend(decompose_range(text, cursor, end, next_level, units_meta, parent_articles, parent_clauses, parent_points, context, target_size, hard_limit))
    return out

def get_continuous_units(record: Dict[str, Any], target_size: int = 5000, hard_limit: int = 6000) -> List[ChunkUnit]:
    text = record["text"]
    doc_len = len(text)
    if not text:
        return []
    meta = sorted(record.get("units", []), key=lambda u: u.get("char_start", 0))
    
    hard_boundaries = {
        u["char_start"] for u in meta 
        if u.get("level") in ("part", "chapter", "section") and 0 < u.get("char_start", 0) < doc_len
    }
    
    fingerprint = record.get("fingerprint", [])
    primary = "article" if "article" in fingerprint else ("clause" if "clause" in fingerprint else "paragraph")
    prim = [u for u in meta if u.get("level") == primary]
    
    cut_points = sorted({0, doc_len} | hard_boundaries | {u["char_start"] for u in prim if 0 < u["char_start"] < doc_len})

    out = []
    for i in range(len(cut_points) - 1):
        start = cut_points[i]
        end = cut_points[i + 1]
        if start >= end:
            continue
        
        ctx = context_at_position(meta, start)
        matching_units = [u for u in prim if u["char_start"] <= start < u.get("char_end", doc_len)]
        arts = [matching_units[0].get("number")] if matching_units and primary == "article" and matching_units[0].get("number") else []
        cls = [matching_units[0].get("number")] if matching_units and primary == "clause" and matching_units[0].get("number") else []
        
        out.extend(decompose_range(text, start, end, primary, meta, arts, cls, [], ctx, target_size, hard_limit))

    return out

def same_structural_context(a: ChunkUnit, b: ChunkUnit) -> bool:
    return a.context_key == b.context_key

def pack_units(units: List[ChunkUnit], hard_boundaries: set[int], soft_limit: int = 5000, hard_limit: int = 6000) -> List[List[ChunkUnit]]:
    chunks = []
    current = []
    start = None
    
    for unit in units:
        if unit.char_end <= unit.char_start:
            continue
        if not current:
            current = [unit]
            start = unit.char_start
            continue
            
        proposed = unit.char_end - start
        is_at_hard_boundary = unit.char_start in hard_boundaries
        context_changed = not same_structural_context(current[-1], unit)
        
        if is_at_hard_boundary or context_changed:
            chunks.append(current)
            current = [unit]
            start = unit.char_start
            continue
            
        if proposed <= soft_limit:
            current.append(unit)
        elif proposed <= hard_limit:
            current.append(unit)
            chunks.append(current)
            current = []
            start = None
        else:
            chunks.append(current)
            current = [unit]
            start = unit.char_start
            
    if current:
        chunks.append(current)
    return chunks

def build_chunk_record(record: Dict[str, Any], chunk_units: List[ChunkUnit], index: int) -> ChunkRecord:
    source = record["text"]
    start = chunk_units[0].char_start
    end = chunk_units[-1].char_end
    articles = unique_keep_order([v for u in chunk_units for v in u.articles])
    clauses = unique_keep_order([v for u in chunk_units for v in u.clauses])
    points = unique_keep_order([v for u in chunk_units for v in u.points])
    levels = unique_keep_order([u.level for u in chunk_units if u.level not in ("preamble", "text")])
    
    return ChunkRecord(
        document_id=record["document_id"],
        chunk_id=f'{record["document_id"]}_chunk_{index:04d}',
        chunk_index=index,
        document_title=record.get("document_title"),
        document_link=record.get("document_link"),
        part_number=chunk_units[0].part_number,
        part_title=chunk_units[0].part_title,
        chapter_number=chunk_units[0].chapter_number,
        chapter_title=chunk_units[0].chapter_title,
        section_number=chunk_units[0].section_number,
        section_title=chunk_units[0].section_title,
        articles=articles,
        clauses=clauses,
        points=points,
        char_start=start,
        char_end=end,
        char_length=end - start,
        chunk_type=levels[0] if levels else "general",
        is_split=any(u.level in ("paragraph", "hard_char") for u in chunk_units),
        text=source[start:end]
    )

def mark_split_chunks(chunks: List[ChunkRecord]) -> None:
    groups = {}
    for c in chunks:
        for article in c.articles:
            groups.setdefault(("article", article), []).append(c)
        if not c.articles:
            for clause in c.clauses:
                groups.setdefault(("clause", clause), []).append(c)
    for group in groups.values():
        if len(group) > 1:
            for c in group:
                c.is_split = True

def chunk_document(record: Dict[str, Any], target_size: int = 5000, soft_limit: int = 5000, hard_limit: int = 6000) -> List[ChunkRecord]:
    units = get_continuous_units(record, target_size, hard_limit)
    if not units:
        return []
    
    meta = record.get("units", [])
    hard_boundaries = {
        u["char_start"] for u in meta 
        if u.get("level") in ("part", "chapter", "section") and u.get("char_start") is not None
    }
    
    chunks = [build_chunk_record(record, us, i) for i, us in enumerate(pack_units(units, hard_boundaries, soft_limit, hard_limit))]
    mark_split_chunks(chunks)
    
    source = record["text"]
    assert chunks[0].char_start == 0, f"Doc {record['document_id']} does not start at 0"
    assert chunks[-1].char_end == len(source), f"Doc {record['document_id']} end does not match text length"
    for a, b in zip(chunks, chunks[1:]):
        assert a.char_end == b.char_start, f"Discontinuity between chunks in doc {record['document_id']}"
    for c in chunks:
        assert c.text == source[c.char_start:c.char_end], f"Text slice mismatch in chunk {c.chunk_id}"
        
    return chunks