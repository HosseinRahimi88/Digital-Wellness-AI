"""
api/schemas/badges.py
---------------------
Response shapes for the badge catalogue (C-3) and the hall of fame (D-2).

There is no `name` or `description` field anywhere in here, and that is
deliberate. The app ships in four languages; a human-readable string
baked into an API response is the exact bug A-2 describes. The client
renders every string from `id` and substitutes the numbers in `params`.
"""

from __future__ import annotations

from pydantic import BaseModel


class BadgeResponse(BaseModel):
    id: str
    category: str                 # "achievement" | "awareness"
    icon: str
    tier: str | None = None       # achievements only: common | rare | legendary
    # True for every awareness indicator. A client must never place a
    # private badge on a friend-facing surface; the server also refuses
    # to send them on the public endpoint at all.
    private: bool
    earned: bool
    # False = this user's history cannot answer the badge's question yet,
    # which the UI shows as locked rather than as missed.
    evaluable: bool
    progress: float | None = None
    target: float | None = None
    params: dict[str, float] = {}
    # Spent paying for a missed plan day. The history that earned it is
    # still true - badges are derived, not stored - so this is the only
    # way for a miss to have cost anything. Shown as spent rather than
    # as never won.
    revoked: bool = False
    # Earned, but while violations were still outstanding, so it cleared
    # one instead of registering. Kept visible so it does not read as a
    # badge that simply failed to unlock.
    withheld: bool = False


class BadgesResponse(BaseModel):
    badges: list[BadgeResponse] = []
    earned_count: int = 0
    total_count: int = 0
    # Counts per rarity tier, earned only - what the hall of fame shows
    # under each shelf.
    earned_by_tier: dict[str, int] = {}
    # Missed plan days that could not be paid for with a badge. Shown
    # under the Hall of Fame; each newly earned badge clears one, and
    # while any remain new badges are spent rather than registered.
    open_violations: int = 0
    revoked_badges: list[str] = []
    withheld_badges: list[str] = []
