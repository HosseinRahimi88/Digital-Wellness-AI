"""
api/schemas/league_chat.py
--------------------------
Request and response shapes for League chat (D-1-b/c/d).

Note what is NOT in the request shapes: no member list on a send, no
conversation membership, no sender id. Everything that decides who may
read or write is resolved server-side from stored records on each call.
A client that could name its own membership would be the whole
authorization model.
"""

from __future__ import annotations

from pydantic import BaseModel, Field


class ConversationResponse(BaseModel):
    conversation_id: str
    kind: str                       # direct | group
    title: str = ""
    member_ids: list[str] = []
    member_names: dict[str, str] = {}
    created_at_utc: str = ""

    @staticmethod
    def from_conversation(c) -> "ConversationResponse":
        return ConversationResponse(
            conversation_id=c.conversation_id, kind=c.kind, title=c.title,
            member_ids=list(c.member_ids), member_names=dict(c.member_names),
            created_at_utc=c.created_at_utc,
        )


class MessageResponse(BaseModel):
    message_id: str
    conversation_id: str
    sender_id: str
    sender_name: str = ""
    body: str = ""
    sent_at_utc: str = ""
    deleted: bool = False

    @staticmethod
    def from_message(m) -> "MessageResponse":
        return MessageResponse(
            message_id=m.message_id, conversation_id=m.conversation_id,
            sender_id=m.sender_id, sender_name=m.sender_name,
            body=m.body, sent_at_utc=m.sent_at_utc, deleted=m.deleted,
        )


class OpenDirectRequest(BaseModel):
    friend_user_id: str = Field(..., description="Must be an accepted League connection; checked server-side.")


class RenameConversationRequest(BaseModel):
    """The name is shared, not per-member: a direct chat renamed by one
    side reads the same to the other. Two people calling one thread by
    different names is worse than neither being able to rename it."""

    title: str = Field(..., min_length=1, max_length=60)


class CreateGroupRequest(BaseModel):
    title: str = Field(..., max_length=60)
    member_ids: list[str] = Field(
        default_factory=list,
        description="Anyone here who is not an accepted connection of yours is dropped, not rejected.",
    )


class SendMessageRequest(BaseModel):
    body: str = Field(..., min_length=1, max_length=2000)


class ReportRequest(BaseModel):
    message_id: str
    reason: str = Field("", max_length=500)
    also_block: bool = False


class BlockRequest(BaseModel):
    user_id: str


class ConversationListResponse(BaseModel):
    conversations: list[ConversationResponse] = []
    blocked_user_ids: list[str] = []


class MessageListResponse(BaseModel):
    messages: list[MessageResponse] = []
    conversation: ConversationResponse | None = None
