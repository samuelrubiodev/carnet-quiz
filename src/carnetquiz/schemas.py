from __future__ import annotations

from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, Field, field_validator


class SubtitleType(StrEnum):
    MANUAL = "manual"
    AUTOMATIC = "automatic"
    IMPORTED = "imported_manual"
    LOCAL = "local_transcribed"


class SegmentInput(BaseModel):
    id: int | None = None
    start_seconds: float = Field(ge=0)
    end_seconds: float = Field(gt=0)
    text: str = Field(min_length=1, max_length=3000)
    original_text: str | None = None
    language: str = "es"
    subtitle_type: SubtitleType = SubtitleType.IMPORTED

    @field_validator("end_seconds")
    @classmethod
    def end_after_start(cls, value: float, info: object) -> float:
        start = getattr(info, "data", {}).get("start_seconds", 0)
        if value <= start:
            raise ValueError("end_seconds debe ser mayor que start_seconds")
        return value


class ConceptInput(BaseModel):
    id: str = Field(pattern=r"^[a-z0-9][a-z0-9-]{2,79}$")
    title: str = Field(min_length=3, max_length=180)
    topic: str = Field(min_length=2, max_length=100)
    subtopic: str | None = Field(default=None, max_length=100)
    summary: str = Field(min_length=10, max_length=1000)
    importance: Literal["low", "medium", "high"]
    difficulty: int = Field(ge=1, le=5)
    exam_relevant: bool = True
    source_segment_ids: list[int] = Field(min_length=1, max_length=20)
    source_start: float = Field(ge=0)
    source_end: float = Field(gt=0)


class OptionInput(BaseModel):
    id: str = Field(pattern=r"^[a-z][a-z0-9_-]{0,19}$")
    text: str = Field(min_length=1, max_length=500)


QUESTION_TYPES = {
    "definition", "direct", "practical_case", "comparison", "negative", "priority", "exception",
    "sign_interpretation", "true_false_group",
}


class QuestionInput(BaseModel):
    id: str = Field(pattern=r"^[a-z0-9][a-z0-9-]{2,99}$")
    concept_id: str = Field(pattern=r"^[a-z0-9][a-z0-9-]{2,79}$")
    type: str
    difficulty: int = Field(ge=1, le=5)
    question: str = Field(min_length=8, max_length=700)
    options: list[OptionInput] = Field(min_length=3, max_length=4)
    correct_option: str
    explanation: str = Field(min_length=8, max_length=1000)
    source_segment_ids: list[int] = Field(min_length=1, max_length=20)
    source_start: float = Field(ge=0)
    source_end: float = Field(gt=0)

    @field_validator("type")
    @classmethod
    def valid_type(cls, value: str) -> str:
        if value not in QUESTION_TYPES:
            raise ValueError(f"Tipo no admitido: {value}")
        return value


class ReviewInput(BaseModel):
    reviewed_question_ids: list[str] = Field(default_factory=list)
    rejected_question_ids: list[str] = Field(default_factory=list)
    notes: str = Field(default="", max_length=5000)
    repaired: bool = False


class ValidationIssue(BaseModel):
    level: Literal["error", "warning"]
    code: str
    message: str
    item_id: str | None = None


class ValidationReport(BaseModel):
    job_id: str
    valid_concept_ids: list[str] = Field(default_factory=list)
    valid_question_ids: list[str] = Field(default_factory=list)
    issues: list[ValidationIssue] = Field(default_factory=list)

    @property
    def errors(self) -> list[ValidationIssue]:
        return [issue for issue in self.issues if issue.level == "error"]
