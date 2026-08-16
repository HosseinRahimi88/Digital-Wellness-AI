"""
api/routers/auth.py
----------------------
Registration, login, and account info. Every method call here delegates
straight to the existing AccountService - this router's only job is
translating between HTTP/Pydantic and that service's own exceptions.
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, status

from api.auth.security import get_current_account
from api.dependencies.services import get_account_service
from api.exceptions.errors import ConflictError, UnauthorizedError, BadRequestError, TooManyRequestsError
from api.schemas.auth import (
    AccountResponse,
    ForgotPasswordRequest,
    ForgotPasswordResponse,
    LoginRequest,
    OnboardingProfileRequest,
    RefreshRequest,
    RegisterRequest,
    ResendVerificationResponse,
    ResetPasswordRequest,
    SecurityAnswerResetRequest,
    SecurityQuestionResponse,
    SetSecurityQuestionRequest,
    TokenResponse,
    VerifyEmailRequest,
    VerifyEmailResponse,
)
from services.identity.mail_service import get_mail_service
from services.identity.refresh_token_service import RefreshTokenService
from services.identity.account_service import (
    Account,
    AccountService,
    EmailAlreadyRegisteredError,
    InactiveAccountError,
    InvalidCredentialsError,
    LoginRateLimitedError,
    PasswordLoginNotAvailableError,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["Auth"])


def _issue_session(account: Account, account_service: AccountService) -> TokenResponse:
    """One access token, one refresh token, one place.

    Every route that hands out a session goes through here - register,
    login, reset, refresh, OAuth - so there is no path that mints an
    access token without also recording a revocable refresh token
    beside it. A second implementation of this is exactly how one
    login route ends up un-revocable.
    """
    from utils.tokens import DEFAULT_ACCESS_TOKEN_EXPIRE_MINUTES, create_refresh_token

    access_token = account_service.issue_access_token(account)
    refresh_token: str | None = None
    try:
        refresh_token, jti, expires_at = create_refresh_token(subject=account.user_id)
        RefreshTokenService(account.user_id).issue(jti, expires_at)
    except Exception:  # noqa: BLE001
        # A refresh token is an improvement on the hour-long session, not
        # a prerequisite for it. If the store is unwritable the user
        # still gets their access token and the old behaviour; they must
        # not be refused a login over it.
        logger.warning("Could not issue a refresh token for %s", account.user_id, exc_info=True)
        refresh_token = None

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        expires_in=DEFAULT_ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        email_verified=bool(getattr(account, "email_verified", True)),
    )


def _send_verification(account: Account, account_service: AccountService) -> str:
    """Mint and deliver a verification token. Returns the delivery channel.

    Never raises and never returns the token: the caller is a route, and
    a route that can see this value is a route that can leak it.
    """
    token = account_service.issue_email_verification_token(account)
    if token is None:
        return "none"
    delivery = get_mail_service().send(
        to=account.email,
        subject="Verify your Digital Wellness AI email",
        body=(
            f"Hello {account.display_name or ''},\n\n"
            "Use this code to verify your email address:\n\n"
            f"    {token}\n\n"
            "It expires in 24 hours. If you did not create this account, "
            "you can ignore this message.\n"
        ),
    )
    return delivery.channel if delivery.delivered else "none"


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
            security_question=payload.security_question,
            security_answer=payload.security_answer,
        )
    except EmailAlreadyRegisteredError as exc:
        raise ConflictError(str(exc), error_code="email_already_registered") from exc
    except ValueError as exc:
        # e.g. password shorter than AccountService.MIN_PASSWORD_LENGTH
        raise BadRequestError(str(exc), error_code="invalid_registration") from exc

    # Best effort, and deliberately not fatal: an account that exists
    # but whose verification mail bounced is recoverable through
    # /auth/resend-verification. An account that was refused because the
    # mail server was down is not recoverable by the user at all.
    _send_verification(account, account_service)
    return _issue_session(account, account_service)


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
    except LoginRateLimitedError as exc:
        raise TooManyRequestsError(
            str(exc), error_code="login_rate_limited", retry_after_seconds=exc.retry_after_seconds,
        ) from exc
    except PasswordLoginNotAvailableError as exc:
        # Distinct code from bad credentials on purpose: the frontend needs
        # to point the user at the GitHub button rather than let them keep
        # retrying a password that does not exist. Safe to disclose - the
        # provider name is not a secret, and the alternative is a user
        # locked out with no explanation.
        raise UnauthorizedError(str(exc), error_code="provider_login_required") from exc
    except (InvalidCredentialsError, InactiveAccountError) as exc:
        raise UnauthorizedError(str(exc), error_code="invalid_credentials") from exc

    return _issue_session(account, account_service)


@router.post(
    "/forgot-password", response_model=ForgotPasswordResponse,
    summary="Email a password reset code to the address, if it is registered",
)
def forgot_password(
    payload: ForgotPasswordRequest,
    account_service: AccountService = Depends(get_account_service),
) -> ForgotPasswordResponse:
    """Send a reset code to the address. Never return it.

    This route used to answer with the reset token in its body. The
    comment beside it argued that the response text was identical
    whether or not the email matched, so it could not be used to
    enumerate accounts - which was true, and beside the point. Anyone
    who knew a registered address could POST it here, read the token out
    of the JSON, and set that account's password. The flow was an
    account takeover with a login form in front of it.

    The token now goes to services/identity/mail_service and nowhere
    else. What comes back says only WHERE it went, so a user knows
    whether to check their inbox or ask whoever runs the server.
    """
    reset_token = account_service.issue_password_reset_token(payload.email)

    channel = "none"
    if reset_token is not None:
        delivery = get_mail_service().send(
            to=payload.email,
            subject="Your Digital Wellness AI password reset code",
            body=(
                "Somebody asked to reset the password on this account.\n\n"
                "Your reset code:\n\n"
                f"    {reset_token}\n\n"
                "It expires in 15 minutes. If this was not you, ignore this "
                "message - nothing has changed.\n"
            ),
        )
        if delivery.delivered:
            channel = delivery.channel

    # One message for every case: unknown address, provider-only account,
    # delivery failure. `channel` stays "none" for all three, so neither
    # field distinguishes a registered address from an unregistered one.
    return ForgotPasswordResponse(
        message="If that email is registered, a reset code has been sent to it.",
        delivery=channel,
    )


@router.post(
    "/reset-password", response_model=TokenResponse,
    summary="Set a new password using a reset token, and log in with it immediately",
)
def reset_password(
    payload: ResetPasswordRequest,
    account_service: AccountService = Depends(get_account_service),
) -> TokenResponse:
    try:
        account = account_service.reset_password(payload.reset_token, payload.new_password)
    except ValueError as exc:
        raise BadRequestError(str(exc), error_code="invalid_password") from exc
    if account is None:
        raise UnauthorizedError("Invalid or expired reset code.", error_code="invalid_reset_token")

    # A password reset is the response to "somebody else may have my
    # account". Leaving that somebody's existing sessions alive would
    # make the reset cosmetic, so every refresh token this account has
    # is withdrawn and the user continues on a session minted here.
    try:
        RefreshTokenService(account.user_id).revoke_all("password_reset")
    except Exception:  # noqa: BLE001
        logger.warning("Could not revoke sessions after reset for %s", account.user_id, exc_info=True)

    return _issue_session(account, account_service)


@router.post(
    "/security-question", response_model=SecurityQuestionResponse,
    summary="The security question set on an address, if it has one",
)
def security_question(
    payload: ForgotPasswordRequest,
    account_service: AccountService = Depends(get_account_service),
) -> SecurityQuestionResponse:
    """The question to put to whoever is claiming this address.

    A POST rather than a GET, and the address goes in the body rather
    than the query string, because query strings end up in access logs,
    browser history and referrer headers. The address is not a secret,
    but there is no reason to write every attempted one into three
    places that outlive the request.

    Answers "no question" identically for an unregistered address, a
    provider-only account, and an account that never set one. Those are
    different facts and the caller is not entitled to tell them apart -
    the moment it can, this endpoint is a way to test whether an address
    has an account here.
    """
    question = account_service.get_security_question(payload.email)
    return SecurityQuestionResponse(
        question=question, available=question is not None,
    )


@router.post(
    "/reset-password-with-answer", response_model=TokenResponse,
    summary="Set a new password by answering the account's own security question",
)
def reset_password_with_answer(
    payload: SecurityAnswerResetRequest,
    account_service: AccountService = Depends(get_account_service),
) -> TokenResponse:
    """The second route back in, for a deployment with no mail server.

    With `LogTransport` - which is the default, and what this project
    actually ships with - a reset code goes to the server's log. The
    person who needs it cannot read the server's log, so the emailed
    route is, in practice, a dead end for a real user. This is the way
    back that does not depend on somebody else's infrastructure.

    It is also the softest target in the app, because an answer carries
    less entropy than a password. Three things hold it down:

      * the SAME per-address failed-attempt throttle as login, sharing
        the counter, so guessing here also burns the login budget;
      * an unknown address, a missing question and a wrong answer are
        one indistinguishable failure;
      * success withdraws every existing session, exactly as the
        token-based reset does - somebody recovering an account is
        usually recovering it FROM someone.
    """
    email = payload.email.strip().lower()
    try:
        account_service._check_login_rate_limit(email)
    except LoginRateLimitedError as exc:
        raise TooManyRequestsError(
            str(exc), error_code="login_rate_limited",
            retry_after_seconds=exc.retry_after_seconds,
        ) from exc

    try:
        account = account_service.reset_password_with_security_answer(
            payload.email, payload.answer, payload.new_password,
        )
    except ValueError as exc:
        raise BadRequestError(str(exc), error_code="invalid_password") from exc

    if account is None:
        account_service._record_failed_login(email)
        raise UnauthorizedError(
            "That answer does not match.", error_code="invalid_security_answer",
        )

    try:
        RefreshTokenService(account.user_id).revoke_all("security_answer_reset")
    except Exception:  # noqa: BLE001
        logger.warning(
            "Could not revoke sessions after answer reset for %s",
            account.user_id, exc_info=True,
        )

    return _issue_session(account, account_service)


@router.post(
    "/security-question/set", response_model=AccountResponse,
    summary="Set or replace the security question on the authenticated account",
)
def set_security_question(
    payload: SetSecurityQuestionRequest,
    account: Account = Depends(get_current_account),
    account_service: AccountService = Depends(get_account_service),
) -> AccountResponse:
    """Lets an existing account add the recovery route it never had.

    The current password is re-checked here even though the caller is
    already authenticated. An access token is a bearer credential that
    can be an hour old and sitting in somebody else's hands; letting it
    rewrite the recovery answer would mean a borrowed session could lock
    the real owner out. Re-asking for the password is the standard
    treatment for a "change how I get back in" action, and this is one.
    """
    try:
        account_service.authenticate(email=account.email, password=payload.current_password)
    except LoginRateLimitedError as exc:
        raise TooManyRequestsError(
            str(exc), error_code="login_rate_limited",
            retry_after_seconds=exc.retry_after_seconds,
        ) from exc
    except (InvalidCredentialsError, InactiveAccountError,
            PasswordLoginNotAvailableError) as exc:
        raise UnauthorizedError(str(exc), error_code="invalid_credentials") from exc

    try:
        updated = account_service.set_security_question(
            account.user_id, payload.question, payload.answer,
        )
    except ValueError as exc:
        raise BadRequestError(str(exc), error_code="invalid_security_question") from exc
    return AccountResponse.from_account(updated)


@router.post(
    "/refresh", response_model=TokenResponse,
    summary="Exchange a refresh token for a new session (the old refresh token is spent)",
)
def refresh(
    payload: RefreshRequest,
    account_service: AccountService = Depends(get_account_service),
) -> TokenResponse:
    """Renew a session without asking for the password again.

    Two things have to be true, and a valid signature is only the first:
    the token must decode, AND its jti must still be live in this
    server's store. That second check is what makes a thirty-day
    credential withdrawable at all - without it, "log out" would be a
    button that deletes something from localStorage while the token
    keeps working for a month.

    Every refresh spends the token it was given. A token that comes back
    a second time is either a client retrying or somebody replaying a
    stolen copy, and nothing in the request distinguishes them - so the
    store treats it as theft and ends every session this account has.
    Being signed out is recoverable with a password; a quietly shared
    session is not.
    """
    from utils.tokens import TokenValidationError, decode_refresh_token

    try:
        claims = decode_refresh_token(token=payload.refresh_token)
    except TokenValidationError as exc:
        raise UnauthorizedError(str(exc), error_code="invalid_refresh_token") from exc

    user_id = str(claims.get("sub") or "")
    accepted, reason = RefreshTokenService(user_id).consume(str(claims.get("jti") or ""))
    if not accepted:
        # One error code for every rejection. Telling a caller apart
        # "already used" from "never existed" tells an attacker holding
        # a stolen token whether it is worth trying elsewhere.
        raise UnauthorizedError(
            "That session has ended. Please sign in again.",
            error_code="invalid_refresh_token",
        )

    account = account_service.get_by_id(user_id)
    if account is None or not account.is_active:
        raise UnauthorizedError("Account is unavailable.", error_code="invalid_credentials")

    return _issue_session(account, account_service)


@router.post(
    "/logout", status_code=status.HTTP_204_NO_CONTENT,
    summary="End every session for the authenticated account",
)
def logout(
    account: Account = Depends(get_current_account),
) -> None:
    """Withdraw every refresh token this account holds.

    The access token in the caller's hand keeps working until it expires
    - it is a signed bearer token with no server-side state, which is
    precisely why it is only good for an hour. What logout can actually
    guarantee is that nothing renews after that, and it does.
    """
    RefreshTokenService(account.user_id).revoke_all("logout")


@router.post(
    "/verify-email", response_model=VerifyEmailResponse,
    summary="Confirm an email address with the code that was sent to it",
)
def verify_email(
    payload: VerifyEmailRequest,
    account_service: AccountService = Depends(get_account_service),
) -> VerifyEmailResponse:
    """Deliberately unauthenticated.

    The token IS the proof - it is signed, single-purpose, and names both
    the account and the address. Requiring a bearer token on top would
    mean a person who followed the link on their phone, where they are
    not signed in, could not verify at all.
    """
    account = account_service.verify_email(payload.token)
    if account is None:
        raise BadRequestError(
            "That verification code is invalid or has expired.",
            error_code="invalid_verification_token",
        )
    return VerifyEmailResponse(
        verified=True, email=account.email, message="Email verified.",
    )


@router.post(
    "/resend-verification", response_model=ResendVerificationResponse,
    summary="Send the verification code again to the authenticated account's address",
)
def resend_verification(
    account: Account = Depends(get_current_account),
    account_service: AccountService = Depends(get_account_service),
) -> ResendVerificationResponse:
    if getattr(account, "email_verified", False):
        return ResendVerificationResponse(
            message="This address is already verified.",
            delivery="none",
            already_verified=True,
        )
    channel = _send_verification(account, account_service)
    return ResendVerificationResponse(
        message="A new verification code has been sent.", delivery=channel,
    )


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
