"""Minimal source-preserving representations of competition data."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Final, TypeAlias


class MissingValue:
    """Marker for a JSON field that was absent, rather than present as null."""

    __slots__ = ()

    def __repr__(self) -> str:
        return "MISSING"


MISSING: Final = MissingValue()
RawText: TypeAlias = str | None | MissingValue


@dataclass(slots=True)
class LegalIRSample:
    """One raw LegalIR record; gold document IDs remain JSON strings."""

    sample_id: str
    question: RawText
    answer: list[str] | None | MissingValue

    def to_dict(self) -> dict[str, object]:
        result: dict[str, object] = {}
        if self.question is not MISSING:
            result["question"] = self.question
        if self.answer is not MISSING:
            result["answer"] = self.answer
        return {self.sample_id: result}


@dataclass(slots=True)
class LegalQASample:
    """One raw LegalQA record; a public/test answer may be JSON null."""

    sample_id: str
    question: RawText
    answer: str | None | MissingValue

    def to_dict(self) -> dict[str, object]:
        result: dict[str, object] = {}
        if self.question is not MISSING:
            result["question"] = self.question
        if self.answer is not MISSING:
            result["answer"] = self.answer
        return {self.sample_id: result}


@dataclass(slots=True)
class CorpusDocument:
    """One raw selected-context document.

    The observed corpus stores ``id`` as a JSON integer, while LegalIR labels
    store document IDs as strings. This class intentionally preserves that
    distinction.
    """

    id: int
    passage: RawText
    link: str
    name: RawText = MISSING

    def to_dict(self) -> dict[str, object]:
        result: dict[str, object] = {
            "id": self.id,
            "passage": self.passage,
            "link": self.link,
        }
        if self.passage is MISSING:
            result.pop("passage")
        if self.name is not MISSING:
            result["name"] = self.name
        return result


def is_missing(value: object) -> bool:
    """Return whether ``value`` represents an absent source field."""

    return value is MISSING
