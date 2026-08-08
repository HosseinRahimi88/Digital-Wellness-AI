"""api/schemas/league.py"""

from __future__ import annotations

from pydantic import BaseModel, Field


class LeagueMeResponse(BaseModel):
    invite_code: str
    rules_accepted: bool
    friend_count: int
    pending_count: int
    my_rank: int | None = None


class RedeemInviteRequest(BaseModel):
    invite_code: str
    shared_categories: list[str] = Field(default_factory=list)


class RespondRequestBody(BaseModel):
    approve: bool
    shared_categories: list[str] = Field(default_factory=list)


class SharingUpdateRequest(BaseModel):
    shared_categories: list[str] = Field(default_factory=list)


class ConnectionResponse(BaseModel):
    connection_id: str
    other_user_id: str
    other_display_name: str
    status: str
    shared_by_me: list[str]
    visible_to_me: list[str]
    requested_at_utc: str
    responded_at_utc: str = ""
    is_requester: bool


class PendingRequestsResponse(BaseModel):
    requests: list[ConnectionResponse]


class LeagueFriendEntry(BaseModel):
    user_id: str
    display_name: str
    persona: str | None = None
    score: float | None = None
    rank: int | None = None
    plan_focus: str | None = None


class LeagueSelfEntry(BaseModel):
    display_name: str
    persona: str | None = None
    score: float | None = None
    score_7d_ago: float | None = None
    plan_focus: str | None = None


class LeaderboardResponse(BaseModel):
    self_entry: LeagueSelfEntry
    friends: list[LeagueFriendEntry]
    comparison_note: str
