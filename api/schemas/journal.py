"""
api/schemas/journal.py
-----------------------
Request and response shapes for the daily journal - the book on the
About page.

Note what the request does NOT carry: no user id and no timestamps.
Whose page this is comes from the token, and when it was written comes
from the server clock. A client that could name either would be able
to write into another account's book, or to backdate a page past the
rule that says a day cannot be written before it happens.
"""

from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field

from services.identity.journal_service import MAX_TEXT_LENGTH, MOODS


class JournalEntryResponse(BaseModel):
    date: str
    text: str
    mood: Optional[str] = None
    created_at_utc: str = ""
    updated_at_utc: str = ""
    # Only demo pages carry translations; a page a person typed is in
    # the language they typed it in and stays that way.
    text_i18n: dict[str, str] = {}

    @staticmethod
    def from_entry(entry) -> "JournalEntryResponse":
        return JournalEntryResponse(
            date=entry.date, text=entry.text, mood=entry.mood,
            created_at_utc=entry.created_at_utc, updated_at_utc=entry.updated_at_utc,
            text_i18n=dict(entry.text_i18n),
        )


class JournalListResponse(BaseModel):
    entries: list[JournalEntryResponse] = []
    count: int = 0
    max_length: int = MAX_TEXT_LENGTH
    moods: list[str] = list(MOODS)


class SaveJournalRequest(BaseModel):
    text: str = Field(..., description="The day's summary, in the user's own words.")
    mood: Optional[str] = Field(
        None, description=f"One of {', '.join(MOODS)}, or omitted."
    )
