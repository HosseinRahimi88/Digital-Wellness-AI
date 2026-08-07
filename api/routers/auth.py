"""
api/routers/auth.py
----------------------
Registration, login, and account info. Every method call here delegates
straight to the existing AccountService - this router's only job is
translating between HTTP/Pydantic and that service's own exceptions.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, status

from api.auth.security import get_current_account
from api.dependencies.services import get_account_service
from api.exceptions.errors import ConflictError, UnauthorizedError, BadRequestError
from api.schemas.auth import (
    AccountResponse,
    LoginRequest,
    OnboardingProfileRequest,
    RegisterRequest,
    TokenResponse,
)
from services.account_service import (
    Account,
    AccountService,
    EmailAlreadyRegisteredError,
    InactiveAccountError,
    InvalidCredentialsError,
)

router = APIRouter(prefix="/auth", tags=["Auth"])


@router.post(
    "/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED,
    summary="Create a new account and return an access token",
)
def register(
    payload: RegisterRequest,
    account_service: AccountService = Depends(get_account_service),
) -> TokenResponse:
    try:
        account = account_service.register(
            email=payload.email, password=payload.password, display_name=payload.display_name,
        )
    except EmailAlreadyRegisteredError as exc:
        raise ConflictError(str(exc), error_code="email_already_registered") from exc
    except ValueError as exc:
        # e.g. password shorter than AccountService.MIN_PASSWORD_LENGTH
        raise BadRequestError(str(exc), error_code="invalid_registration") from exc

    token = account_service.issue_access_token(account)
    return TokenResponse(access_token=token)


@router.post(
    "/login", response_model=TokenResponse,
    summary="Exchange email/password for an access token",
)
def login(
    payload: LoginRequest,
    account_service: AccountService = Depends(get_account_service),
) -> TokenResponse:
    try:
        account = account_service.authenticate(email=payload.email, password=payload.password)
    except (InvalidCredentialsError, InactiveAccountError) as exc:
        raise UnauthorizedError(str(exc), error_code="invalid_credentials") from exc

    token = account_service.issue_access_token(account)
    return TokenResponse(access_token=token)


@router.get("/me", response_model=AccountResponse, summary="The authenticated account's profile")
def get_me(account: Account = Depends(get_current_account)) -> AccountResponse:
    return AccountResponse.from_account(account)


@router.put(
    "/me/onboarding", response_model=AccountResponse,
    summary="Save the onboarding preference profile for the authenticated account",
)
def save_onboarding(
    payload: OnboardingProfileRequest,
    account: Account = Depends(get_current_account),
    account_service: AccountService = Depends(get_account_service),
) -> AccountResponse:
    updated = account_service.save_onboarding_profile(
        account.user_id,
        primary_goal=payload.primary_goal,
        main_use_purpose=payload.main_use_purpose,
        schedule_type=payload.schedule_type,
        usual_sleep_time=payload.usual_sleep_time,
        usual_wake_time=payload.usual_wake_time,
        preferred_effort=payload.preferred_effort,
        work_screen_required=payload.work_screen_required,
    )
    # updated is only None if user_id no longer matches a stored account
    # (e.g. deleted between token issuance and this call) - practically
    # unreachable given get_current_account already resolved the same
    # user_id moments earlier, but handled rather than risking a 500.
    if updated is None:
        raise UnauthorizedError("Account no longer exists.", error_code="account_not_found")
    return AccountResponse.from_account(updated)
