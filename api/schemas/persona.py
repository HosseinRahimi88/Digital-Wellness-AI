"""api/schemas/persona.py"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel


class PersonaRequest(BaseModel):
    user_data: dict[str, float | int | str | bool | None]


class PersonaResponse(BaseModel):
    available: bool
    persona_name: str
    cluster_id: int | None
    confidence: float | None
    runner_up_persona: str | None
    defining_traits: list[dict[str, Any]]
    cluster_size_pct: float | None
    explanation: str

    @staticmethod
    def from_persona_result(r) -> "PersonaResponse":
        return PersonaResponse(**r.to_dict())
