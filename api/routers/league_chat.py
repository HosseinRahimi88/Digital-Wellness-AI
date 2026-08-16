"""
api/routers/league_chat.py
--------------------------
League private and group chat (D-1-b, D-1-c, D-1-d).

Every endpoint here derives the caller's rights from stored state on
each request. Two rules make that concrete:

  * Opening a direct conversation asks LeagueService whether the two
    people have an ACCEPTED connection right now. Chat is something
    accepted friends have; it is never a route to a stranger, and the
    check is not cached.
  * Creating a group filters the requested members down to the
    creator's accepted connections. Someone who never agreed to be
    reachable does not become reachable by being named in a list.

Errors are mapped so the client can behave correctly without being told
anything it should not know: a conversation the caller is not in and a
conversation that does not exist both return 404, because a distinct
403 would confirm which ids are real.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query, Response

from api.auth.security import get_current_account
from api.exceptions.errors import BadRequestError, ForbiddenError, NotFoundError
from api.schemas.league_chat import (
    BlockRequest,
    ConversationListResponse,
    ConversationResponse,
    CreateGroupRequest,
    RenameConversationRequest,
    MessageListResponse,
    MessageResponse,
    OpenDirectRequest,
    ReportRequest,
    SendMessageRequest,
)
from services.identity.account_service import Account, AccountService
from api.dependencies.services import get_account_service
from services.social.league_chat_service import (
    ChatBlockedError,
    ChatNotAuthorizedError,
    ChatNotFoundError,
    ChatRateLimitedError,
    ChatValidationError,
    LeagueChatService,
)
from services.social.league_service import LeagueService

router = APIRouter(prefix="/league/chat", tags=["League chat"])


def _chat() -> LeagueChatService:
    return LeagueChatService()


def _league() -> LeagueService:
    return LeagueService()


def _handle(exc: Exception) -> None:
    """One mapping, so no endpoint invents its own status for the same
    condition."""
    if isinstance(exc, ChatRateLimitedError):
        raise BadRequestError(str(exc), error_code="chat_rate_limited")
    if isinstance(exc, ChatBlockedError):
        raise ForbiddenError(str(exc), error_code="chat_blocked")
    if isinstance(exc, ChatNotAuthorizedError):
        raise ForbiddenError(str(exc), error_code="chat_not_authorized")
    if isinstance(exc, ChatNotFoundError):
        raise NotFoundError(str(exc), error_code="chat_not_found")
    if isinstance(exc, ChatValidationError):
        raise BadRequestError(str(exc), error_code="chat_invalid")
    raise exc


@router.get("/conversations", response_model=ConversationListResponse,
            summary="Every open conversation you are a member of")
def list_conversations(account: Account = Depends(get_current_account)) -> ConversationListResponse:
    chat = _chat()
    return ConversationListResponse(
        conversations=[ConversationResponse.from_conversation(c)
                       for c in chat.conversations_for(account.user_id)],
        blocked_user_ids=chat.blocked_ids(account.user_id),
    )


@router.post("/direct", response_model=ConversationResponse,
             summary="Open (or reopen) the private chat with an accepted friend")
def open_direct(
    payload: OpenDirectRequest,
    account: Account = Depends(get_current_account),
    accounts: AccountService = Depends(get_account_service),
) -> ConversationResponse:
    league = _league()
    # The authorization that matters, resolved live rather than trusted
    # from the request.
    connected = league.are_connected(account.user_id, payload.friend_user_id)
    other = accounts.get_by_id(payload.friend_user_id) if connected else None
    try:
        conversation = _chat().open_direct_conversation(
            account.user_id, payload.friend_user_id,
            user_name=account.display_name,
            other_name=(other.display_name if other else ""),
            connection_verified=connected,
        )
    except Exception as exc:  # noqa: BLE001 - mapped, never swallowed
        _handle(exc)
    return ConversationResponse.from_conversation(conversation)


@router.post("/groups", response_model=ConversationResponse,
             summary="Create a group with people who have accepted you")
def create_group(
    payload: CreateGroupRequest,
    account: Account = Depends(get_current_account),
    accounts: AccountService = Depends(get_account_service),
) -> ConversationResponse:
    league = _league()
    verified = {
        member_id for member_id in payload.member_ids
        if league.are_connected(account.user_id, member_id)
    }
    names = {}
    for member_id in verified:
        other = accounts.get_by_id(member_id)
        names[member_id] = other.display_name if other else ""
    try:
        conversation = _chat().create_group(
            account.user_id, account.display_name, payload.title, names,
            verified_member_ids=verified,
        )
    except Exception as exc:  # noqa: BLE001
        _handle(exc)
    return ConversationResponse.from_conversation(conversation)


@router.put("/conversations/{conversation_id}/title", response_model=ConversationResponse,
            summary="Rename a conversation you are a member of")
def rename_conversation(
    conversation_id: str,
    payload: RenameConversationRequest,
    account: Account = Depends(get_current_account),
) -> ConversationResponse:
    """A thread called "Direct chat" four times over is a list nobody
    can navigate. Membership is checked inside the service by the same
    gate every other conversation route uses, so a non-member gets the
    same refusal as for a conversation that does not exist."""
    try:
        conversation = _chat().rename_conversation(
            account.user_id, conversation_id, payload.title)
    except Exception as exc:  # noqa: BLE001
        _handle(exc)
    return ConversationResponse.from_conversation(conversation)


@router.post("/groups/{conversation_id}/leave", status_code=204,
             summary="Leave a group")
def leave_group(conversation_id: str, account: Account = Depends(get_current_account)) -> Response:
    try:
        _chat().leave_group(account.user_id, conversation_id)
    except Exception as exc:  # noqa: BLE001
        _handle(exc)
    return Response(status_code=204)


@router.get("/conversations/{conversation_id}/messages", response_model=MessageListResponse,
            summary="Read a conversation you are a member of")
def read_messages(
    conversation_id: str,
    limit: int = Query(50, ge=1, le=200),
    account: Account = Depends(get_current_account),
) -> MessageListResponse:
    chat = _chat()
    try:
        messages = chat.messages_for(account.user_id, conversation_id, limit=limit)
    except Exception as exc:  # noqa: BLE001
        _handle(exc)
    conversation = next(
        (c for c in chat.conversations_for(account.user_id) if c.conversation_id == conversation_id),
        None,
    )
    return MessageListResponse(
        messages=[MessageResponse.from_message(m) for m in messages],
        conversation=ConversationResponse.from_conversation(conversation) if conversation else None,
    )


@router.post("/conversations/{conversation_id}/messages", response_model=MessageResponse,
             summary="Post a message (rate limited per sender across all conversations)")
def send_message(
    conversation_id: str,
    payload: SendMessageRequest,
    account: Account = Depends(get_current_account),
) -> MessageResponse:
    try:
        message = _chat().send_message(
            account.user_id, conversation_id, payload.body, sender_name=account.display_name,
        )
    except Exception as exc:  # noqa: BLE001
        _handle(exc)
    return MessageResponse.from_message(message)


@router.delete("/messages/{message_id}", status_code=204,
               summary="Retract your own message")
def delete_message(message_id: str, account: Account = Depends(get_current_account)) -> Response:
    try:
        _chat().delete_message(account.user_id, message_id)
    except Exception as exc:  # noqa: BLE001
        _handle(exc)
    return Response(status_code=204)


@router.post("/report", status_code=204, summary="Report a message for a human to review")
def report_message(payload: ReportRequest, account: Account = Depends(get_current_account)) -> Response:
    try:
        _chat().report(account.user_id, payload.message_id, payload.reason, also_block=payload.also_block)
    except Exception as exc:  # noqa: BLE001
        _handle(exc)
    return Response(status_code=204)


@router.post("/block", status_code=204, summary="Block someone; symmetric and immediate")
def block_user(payload: BlockRequest, account: Account = Depends(get_current_account)) -> Response:
    try:
        _chat().block(account.user_id, payload.user_id)
    except Exception as exc:  # noqa: BLE001
        _handle(exc)
    return Response(status_code=204)


@router.post("/unblock", status_code=204, summary="Undo a block")
def unblock_user(payload: BlockRequest, account: Account = Depends(get_current_account)) -> Response:
    try:
        _chat().unblock(account.user_id, payload.user_id)
    except Exception as exc:  # noqa: BLE001
        _handle(exc)
    return Response(status_code=204)
