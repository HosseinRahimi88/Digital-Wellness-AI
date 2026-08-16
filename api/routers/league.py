"""
api/routers/league.py
------------------------
Friends League: invite codes, two-sided consent, granular per-friend
category sharing, and a leaderboard framed primarily as "you vs. your
own past" with friends shown alongside - never the other way around.
See services/social/league_service.py for the full consent-model rationale.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends

from api.auth.security import get_current_account
from api.dependencies.services import get_account_service
from api.exceptions.errors import BadRequestError, ConflictError, ForbiddenError, NotFoundError
from api.schemas.league import (
    ConnectionResponse,
    LeaderboardResponse,
    LeagueFriendEntry,
    LeagueMeResponse,
    LeagueSelfEntry,
    PendingRequestsResponse,
    RedeemInviteRequest,
    RespondRequestBody,
    SharingUpdateRequest,
)
from services.identity.account_service import Account, AccountService
from services.identity.history_service import HistoryService
from services.social.league_service import (
    AlreadyConnectedError,
    ConnectionNotFoundError,
    InvalidInviteCodeError,
    LeagueConnection,
    LeagueError,
    LeagueService,
    RulesNotAcceptedError,
)
from utils.persona_titles import resolve_identity

router = APIRouter(tags=["Friends League"])


def _service() -> LeagueService:
    return LeagueService()


def _to_connection_response(conn: LeagueConnection, viewer_id: str) -> ConnectionResponse:
    other_id, other_name = conn.other_side(viewer_id)
    return ConnectionResponse(
        connection_id=conn.connection_id, other_user_id=other_id, other_display_name=other_name,
        status=conn.status, shared_by_me=conn.shared_by(viewer_id), visible_to_me=conn.visible_to(viewer_id),
        requested_at_utc=conn.requested_at_utc, responded_at_utc=conn.responded_at_utc,
        is_requester=(viewer_id == conn.requester_id),
    )


def _latest_entry(user_id: str) -> dict:
    try:
        entries = HistoryService(user_id=user_id).get_all(include_excluded=False)
    except Exception:  # noqa: BLE001 - a friend's history must never break the whole leaderboard
        return {}
    return entries[-1] if entries else {}


@router.get("/league/me", response_model=LeagueMeResponse, summary="Your invite code and League status")
def league_me(account: Account = Depends(get_current_account)) -> LeagueMeResponse:
    svc = _service()
    profile = svc.get_or_create_profile(account.user_id, account.display_name or account.email)
    friends = svc.connections_for(account.user_id)
    pending = svc.pending_requests_for(account.user_id)
    return LeagueMeResponse(
        invite_code=profile.invite_code, rules_accepted=profile.rules_accepted,
        friend_count=len(friends), pending_count=len(pending), my_rank=None,
    )


@router.post("/league/rules/accept", response_model=LeagueMeResponse, summary="Explicitly accept the League rules")
def accept_rules(account: Account = Depends(get_current_account)) -> LeagueMeResponse:
    svc = _service()
    profile = svc.accept_rules(account.user_id, account.display_name or account.email)
    friends = svc.connections_for(account.user_id)
    pending = svc.pending_requests_for(account.user_id)
    return LeagueMeResponse(
        invite_code=profile.invite_code, rules_accepted=profile.rules_accepted,
        friend_count=len(friends), pending_count=len(pending),
    )


@router.post("/league/invite/redeem", response_model=ConnectionResponse, summary="Enter a friend's invite code")
def redeem_invite(
    payload: RedeemInviteRequest, account: Account = Depends(get_current_account),
) -> ConnectionResponse:
    svc = _service()
    try:
        conn = svc.redeem_invite(
            account.user_id, account.display_name or account.email, payload.invite_code, payload.shared_categories,
        )
    except RulesNotAcceptedError as exc:
        raise ForbiddenError(str(exc), error_code="league_rules_not_accepted") from exc
    except InvalidInviteCodeError as exc:
        raise NotFoundError(str(exc), error_code="invalid_invite_code") from exc
    except AlreadyConnectedError as exc:
        raise ConflictError(str(exc), error_code="already_connected") from exc
    except ValueError as exc:
        raise BadRequestError(str(exc), error_code="invalid_sharing_categories") from exc
    except LeagueError as exc:
        raise BadRequestError(str(exc), error_code="league_error") from exc
    return _to_connection_response(conn, account.user_id)


@router.get("/league/requests/pending", response_model=PendingRequestsResponse, summary="Requests waiting for your approval")
def pending_requests(account: Account = Depends(get_current_account)) -> PendingRequestsResponse:
    svc = _service()
    requests = svc.pending_requests_for(account.user_id)
    return PendingRequestsResponse(requests=[_to_connection_response(c, account.user_id) for c in requests])


@router.get(
    "/league/requests/sent", response_model=PendingRequestsResponse,
    summary="Requests you have sent that are still awaiting the other side's approval",
)
def sent_requests(account: Account = Depends(get_current_account)) -> PendingRequestsResponse:
    svc = _service()
    requests = svc.sent_requests_for(account.user_id)
    return PendingRequestsResponse(requests=[_to_connection_response(c, account.user_id) for c in requests])


@router.post(
    "/league/requests/{connection_id}/respond", response_model=ConnectionResponse,
    summary="Approve or decline a pending request, choosing what you share back",
)
def respond_to_request(
    connection_id: str, payload: RespondRequestBody, account: Account = Depends(get_current_account),
) -> ConnectionResponse:
    svc = _service()
    try:
        conn = svc.respond_to_request(account.user_id, connection_id, payload.approve, payload.shared_categories)
    except RulesNotAcceptedError as exc:
        raise ForbiddenError(str(exc), error_code="league_rules_not_accepted") from exc
    except ConnectionNotFoundError as exc:
        raise NotFoundError(str(exc), error_code="connection_not_found") from exc
    except ValueError as exc:
        raise BadRequestError(str(exc), error_code="invalid_sharing_categories") from exc
    return _to_connection_response(conn, account.user_id)


@router.get("/league/connections", response_model=list[ConnectionResponse], summary="Your accepted League connections")
def connections(account: Account = Depends(get_current_account)) -> list[ConnectionResponse]:
    svc = _service()
    return [_to_connection_response(c, account.user_id) for c in svc.connections_for(account.user_id)]


@router.put(
    "/league/connections/{connection_id}/sharing", response_model=ConnectionResponse,
    summary="Change exactly what you share with one specific friend",
)
def update_sharing(
    connection_id: str, payload: SharingUpdateRequest, account: Account = Depends(get_current_account),
) -> ConnectionResponse:
    svc = _service()
    try:
        conn = svc.update_sharing(account.user_id, connection_id, payload.shared_categories)
    except ConnectionNotFoundError as exc:
        raise NotFoundError(str(exc), error_code="connection_not_found") from exc
    except ValueError as exc:
        raise BadRequestError(str(exc), error_code="invalid_sharing_categories") from exc
    return _to_connection_response(conn, account.user_id)


@router.delete("/league/connections/{connection_id}", summary="End a League connection (either side can do this)")
def revoke_connection(connection_id: str, account: Account = Depends(get_current_account)) -> dict:
    svc = _service()
    try:
        svc.revoke(account.user_id, connection_id)
    except ConnectionNotFoundError as exc:
        raise NotFoundError(str(exc), error_code="connection_not_found") from exc
    return {"revoked": True}


@router.get(
    "/league/leaderboard", response_model=LeaderboardResponse,
    summary="You vs. your own past, with friends' shared data alongside",
)
def leaderboard(
    account: Account = Depends(get_current_account),
    account_service: AccountService = Depends(get_account_service),
) -> LeaderboardResponse:
    svc = _service()
    history = HistoryService(user_id=account.user_id).get_all(include_excluded=False)
    latest = history[-1] if history else {}
    week_ago = history[-8] if len(history) >= 8 else None

    self_entry = LeagueSelfEntry(
        display_name=account.display_name or account.email,
        persona=(resolve_identity(latest, history=history).primary.title if latest else None),
        score=latest.get("health_score"),
        score_7d_ago=week_ago.get("health_score") if week_ago else None,
        plan_focus=latest.get("top_shap_feature"),
    )

    friend_entries: list[LeagueFriendEntry] = []
    for conn in svc.connections_for(account.user_id):
        other_id, other_name = conn.other_side(account.user_id)
        visible = set(conn.visible_to(account.user_id))
        if not visible:
            continue
        other_latest = _latest_entry(other_id)
        entry = LeagueFriendEntry(user_id=other_id, display_name=other_name)
        if "score" in visible:
            entry.score = other_latest.get("health_score")
        if "persona" in visible and other_latest:
            other_identity = resolve_identity(other_latest, history=[other_latest]).primary
            entry.persona = other_identity.title if other_identity else None
        if "plan_focus" in visible:
            entry.plan_focus = other_latest.get("top_shap_feature")
        friend_entries.append(entry)

    # Rank by real shared score only - a friend who hasn't shared their
    # score is never given a rank (never a fabricated 0/last place).
    scored: list[tuple[str, float]] = []
    if self_entry.score is not None:
        scored.append(("self", self_entry.score))
    for e in friend_entries:
        if e.score is not None:
            scored.append((e.user_id, e.score))
    scored.sort(key=lambda t: t[1], reverse=True)
    rank_of = {uid: i for i, (uid, _) in enumerate(scored, start=1)}
    for e in friend_entries:
        e.rank = rank_of.get(e.user_id)
    my_rank = rank_of.get("self")

    if my_rank is not None:
        comparison_note = (
            f"You're ranked #{my_rank} of {len(scored)} in shared scores right now, but the number that matters "
            "most is your own trend below - friends only appear for categories they've explicitly agreed to share."
        )
    else:
        comparison_note = (
            "Compare yourself against your own past first - friends only appear for the categories they've "
            "explicitly agreed to share, and can never see anything you haven't agreed to share back."
        )

    return LeaderboardResponse(self_entry=self_entry, friends=friend_entries, comparison_note=comparison_note)
