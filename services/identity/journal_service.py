"""
Journal Service
----------------
One short written summary per person per day - the thing the user
types into the book on the About page, in their own words.

Why this is a service and not browser storage
----------------------------------------------
It is the only place in this app where the user writes free text about
their own life, so it is the piece of stored data most worth treating
carefully. Keeping it server-side means it is scoped to an account
(not a browser), it survives a device change, it is included in the
account-deletion path like every other store, and a demo account can
be handed a book that already has pages in it.

Shape
------
One record per (user_id, date). Writing the same date twice edits that
day rather than appending - a diary has one page per day, and a second
"today" would make the book unreadable. `created_at_utc` is kept from
the first write so an edited page still knows when it was first
written.

`text_i18n`
------------
Real users write in one language: their entry is `text`, and
`text_i18n` is empty. Demo entries are the exception - a demo person
has to read naturally to a reviewer in any of the four languages, so
demo pages carry all four and the client picks. This mirrors the
`text_i18n` shape the prediction and plan responses already use.

Storage
--------
Same pattern as services/wellness/commitment_service.py: a flat JSON record
list through JSONFileStorageBackend, one instance per user_id, every
read-modify-write inside a real lock.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date as date_cls, datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Optional

from core import paths
from services.storage.base import StorageBackend
from services.storage.sqlite_storage import backend_for

DEFAULT_STORAGE_PATH = paths.storage_file("journal.json")

# Long enough for a real end-of-day paragraph, short enough that one
# account cannot turn the store into a blob host. Measured against the
# demo bank, whose longest page is ~230 characters.
MAX_TEXT_LENGTH = 2000

# The five moods the book offers. Deliberately a closed set: free-text
# moods cannot be counted, translated, or compared with anything.
MOODS = ("rough", "low", "steady", "good", "great")

SUPPORTED_LANGS = ("en", "fa", "ar", "zh")


class JournalValidationError(ValueError):
    """A page that cannot be written as asked - empty, too long, or
    dated somewhere a day cannot be."""


@dataclass(slots=True)
class JournalEntry:
    date: str                       # ISO date, the page's identity
    text: str
    mood: Optional[str] = None
    created_at_utc: str = ""
    updated_at_utc: str = ""
    # Demo pages only; empty for anything a person actually typed.
    text_i18n: dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "date": self.date,
            "text": self.text,
            "mood": self.mood,
            "created_at_utc": self.created_at_utc,
            "updated_at_utc": self.updated_at_utc,
            "text_i18n": dict(self.text_i18n),
        }


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def normalise_day(value: Any) -> str:
    """The ISO date this page belongs to, or an error saying why not.

    A page may be written for today or any past day - people do catch
    up on yesterday - but never for a day that has not happened. A
    diary entry dated tomorrow is either a typo or a clock problem, and
    either way it would sort ahead of every real page in the book.
    """
    if isinstance(value, date_cls):
        day = value
    else:
        try:
            day = date_cls.fromisoformat(str(value).strip())
        except (TypeError, ValueError):
            raise JournalValidationError("That is not a date the book can open.") from None
    if day > date_cls.today():
        raise JournalValidationError("You cannot write a day that has not happened yet.")
    return day.isoformat()


def normalise_text(value: Any) -> str:
    text = ("" if value is None else str(value)).strip()
    if not text:
        raise JournalValidationError("An empty page is not saved.")
    if len(text) > MAX_TEXT_LENGTH:
        raise JournalValidationError(
            f"A page holds up to {MAX_TEXT_LENGTH} characters; this one is {len(text)}."
        )
    return text


def normalise_mood(value: Any) -> Optional[str]:
    if value in (None, ""):
        return None
    mood = str(value).strip().lower()
    if mood not in MOODS:
        raise JournalValidationError(f"Unknown mood {mood!r}.")
    return mood


class JournalService:
    """Every page one account has written, and the writing of them."""

    def __init__(self, user_id: str, backend: Optional[StorageBackend] = None) -> None:
        self.user_id = user_id
        self._backend = backend or backend_for(DEFAULT_STORAGE_PATH)

    # ---------------------------------------------------------------- read

    @staticmethod
    def _to_entry(record: dict) -> JournalEntry:
        raw_i18n = record.get("text_i18n") or {}
        return JournalEntry(
            date=record.get("date", ""),
            text=record.get("text", ""),
            mood=record.get("mood"),
            created_at_utc=record.get("created_at_utc", ""),
            updated_at_utc=record.get("updated_at_utc", record.get("created_at_utc", "")),
            text_i18n={k: v for k, v in raw_i18n.items() if k in SUPPORTED_LANGS and v},
        )

    def get_all(self, limit: Optional[int] = None) -> list[JournalEntry]:
        """This account's pages, newest first.

        Newest first because the book opens on the most recent page -
        the reader is looking for what they wrote yesterday far more
        often than what they wrote in week one.
        """
        rows = [r for r in self._backend.read_all() if r.get("user_id") == self.user_id]
        rows.sort(key=lambda r: r.get("date", ""), reverse=True)
        if limit is not None:
            rows = rows[: max(0, int(limit))]
        return [self._to_entry(r) for r in rows]

    def get(self, day: Any) -> Optional[JournalEntry]:
        wanted = normalise_day(day)
        for record in self._backend.read_all():
            if record.get("user_id") == self.user_id and record.get("date") == wanted:
                return self._to_entry(record)
        return None

    def count(self) -> int:
        return sum(1 for r in self._backend.read_all() if r.get("user_id") == self.user_id)

    # --------------------------------------------------------------- write

    def save(
        self,
        day: Any,
        text: Any,
        mood: Any = None,
        text_i18n: Optional[dict[str, str]] = None,
    ) -> JournalEntry:
        """Write (or rewrite) one day's page. Upsert by (user, date)."""
        wanted = normalise_day(day)
        body = normalise_text(text)
        chosen_mood = normalise_mood(mood)
        translations = {
            lang: str(value).strip()
            for lang, value in (text_i18n or {}).items()
            if lang in SUPPORTED_LANGS and str(value).strip()
        }

        stamp = _now()
        entry = JournalEntry(
            date=wanted, text=body, mood=chosen_mood,
            created_at_utc=stamp, updated_at_utc=stamp, text_i18n=translations,
        )

        with self._backend.transaction() as records:
            rows = list(records)
            for row in rows:
                if row.get("user_id") == self.user_id and row.get("date") == wanted:
                    # An edit keeps the day's first-written stamp. The
                    # book shows "written on", and rewriting a sentence
                    # should not move a page's date of birth.
                    entry.created_at_utc = row.get("created_at_utc") or stamp
                    row.update(entry.to_dict())
                    self._backend.commit(rows)
                    return entry
            rows.append({"user_id": self.user_id, **entry.to_dict()})
            self._backend.commit(rows)
        return entry

    def save_many(self, pages: Iterable[tuple[Any, str, Optional[str], dict[str, str]]]) -> int:
        """Write a whole book in ONE locked transaction.

        Demo Mode seeds up to twenty-three pages at once. Doing that
        through save() is twenty-three locked rewrites of a file that
        holds every account's journal - the same cost that made demo
        population time out before the history writes were batched
        (services/identity/history_service.py::record_many).

        Every page still goes through the same validation a typed one
        does; a page that fails is skipped, not silently repaired.
        """
        prepared: dict[str, dict[str, Any]] = {}
        stamp = _now()
        for day, text, mood, translations in pages:
            try:
                wanted = normalise_day(day)
                body = normalise_text(text)
                chosen_mood = normalise_mood(mood)
            except JournalValidationError:
                continue
            prepared[wanted] = JournalEntry(
                date=wanted, text=body, mood=chosen_mood,
                created_at_utc=stamp, updated_at_utc=stamp,
                text_i18n={
                    lang: str(value).strip()
                    for lang, value in (translations or {}).items()
                    if lang in SUPPORTED_LANGS and str(value).strip()
                },
            ).to_dict()
        if not prepared:
            return 0

        written = len(prepared)
        with self._backend.transaction() as records:
            rows = list(records)
            for row in rows:
                if row.get("user_id") != self.user_id:
                    continue
                replacement = prepared.pop(row.get("date", ""), None)
                if replacement is not None:
                    replacement["created_at_utc"] = row.get("created_at_utc") or stamp
                    row.update(replacement)
            rows.extend({"user_id": self.user_id, **page} for page in prepared.values())
            self._backend.commit(rows)
        return written

    # -------------------------------------------------------------- delete

    def delete(self, day: Any) -> bool:
        wanted = normalise_day(day)
        removed = False
        with self._backend.transaction() as records:
            remaining = []
            for row in records:
                if row.get("user_id") == self.user_id and row.get("date") == wanted:
                    removed = True
                    continue
                remaining.append(row)
            if removed:
                self._backend.commit(remaining)
        return removed

    def delete_all(self) -> int:
        return self.delete_users([self.user_id])

    def delete_users(self, user_ids: Iterable[str]) -> int:
        """Remove every page belonging to any of `user_ids`, in one pass.

        Same reason HistoryService.delete_users exists: rebuilding a
        ten-friend demo would otherwise rewrite the whole file once per
        user. A row only goes if its OWN user id is in the set, so this
        can never reach another account.
        """
        wanted = {u for u in user_ids if u}
        if not wanted:
            return 0
        removed = 0
        with self._backend.transaction() as records:
            remaining = []
            for row in records:
                if row.get("user_id") in wanted:
                    removed += 1
                    continue
                remaining.append(row)
            if removed:
                self._backend.commit(remaining)
        return removed
