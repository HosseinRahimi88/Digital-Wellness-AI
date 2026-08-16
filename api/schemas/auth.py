"""
api/schemas/auth.py
----------------------
Request/response models for registration, login, and account info.
Field-level constraints here (min_length, EmailStr) are the FIRST line
of defense (fast, no service call needed for a plainly-malformed
request) - the actual business rule (e.g. minimum password length,
duplicate-email rejection) still lives in AccountService.register()
and is enforced there regardless of what this schema allows through.
"""

from __future__ import annotations

from pydantic import BaseModel, EmailStr, Field


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=1, max_length=256)
    display_name: str = Field(..., min_length=1, max_length=120)
    # The second way back into the account, set here because the moment
    # somebody needs it is the moment they cannot sign in to set it.
    # Optional in the schema so a client written before this exists
    # still registers; the service rejects one half without the other.
    security_question: str | None = Field(default=None, max_length=200)
    security_answer: str | None = Field(default=None, max_length=200)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=1, max_length=256)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    # Long-lived and revocable, so a session survives past the access
    # token's hour without that hour becoming thirty days of
    # un-withdrawable bearer credential. Optional in the schema because
    # a client written before /auth/refresh existed simply ignores it.
    refresh_token: str | None = None
    # Seconds the ACCESS token is good for. Sent so a client can renew
    # before it expires rather than discovering the expiry as a failed
    # request in the middle of something.
    expires_in: int | None = None
    # Whether this account has proved it can read its own address. Not a
    # gate by default - see api/routers/auth.py - but the client shows a
    # quiet reminder, and it must come from the server rather than being
    # guessed from whether a verification screen was ever seen.
    email_verified: bool = True


class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class ForgotPasswordResponse(BaseModel):
    message: str
    # Where the code was SENT - never the code itself.
    #
    # This response used to carry `reset_token`, which meant anyone who
    # knew an email address could ask for that account's reset token and
    # get it. The token now leaves through
    # services/identity/mail_service and this field only says which way
    # it went, so the client can tell the user where to look:
    #
    #   "email"       a mail server accepted it
    #   "server_log"  no mail server is configured; it is in the server
    #                 log, readable by whoever runs the deployment
    #   "none"        delivery failed, or the email matched no account
    #
    # `delivery` is "none" both when the address is unknown and when
    # sending failed, so it cannot be used to enumerate registered
    # addresses either - and `message` is identical in every case.
    delivery: str = "none"


class ResetPasswordRequest(BaseModel):
    reset_token: str
    new_password: str = Field(..., min_length=1, max_length=256)


class SecurityQuestionResponse(BaseModel):
    """The question to put to whoever is claiming an address.

    `question` is null both for an address nobody registered and for an
    account that never set one. Those two must stay indistinguishable,
    or this endpoint becomes a way to list which addresses have accounts.
    """
    question: str | None = None
    # Says whether answering can lead anywhere, without saying why not.
    available: bool = False


class SecurityAnswerResetRequest(BaseModel):
    email: EmailStr
    answer: str = Field(..., min_length=1, max_length=200)
    new_password: str = Field(..., min_length=1, max_length=256)


class SetSecurityQuestionRequest(BaseModel):
    """Setting or replacing the question on an account already signed in.

    The current password is required. Without it, a borrowed session -
    an unlocked laptop, a stolen access token - could rewrite the
    recovery route and lock the real owner out of their own account,
    which turns a recovery feature into a takeover feature.
    """
    question: str = Field(..., min_length=1, max_length=200)
    answer: str = Field(..., min_length=1, max_length=200)
    current_password: str = Field(..., min_length=1, max_length=256)


class VerifyEmailRequest(BaseModel):
    token: str


class VerifyEmailResponse(BaseModel):
    verified: bool
    email: str
    message: str


class ResendVerificationResponse(BaseModel):
    message: str
    # Same three values, same reasoning, as ForgotPasswordResponse.
    delivery: str = "none"
    already_verified: bool = False


class RefreshRequest(BaseModel):
    refresh_token: str


class AccountResponse(BaseModel):
    user_id: str
    email: str
    display_name: str
    is_active: bool
    onboarding_complete: bool
    created_at_utc: str
    # Whether the address has been proved readable. Reported, not
    # enforced - see api/routers/auth.py's REQUIRE_EMAIL_VERIFICATION.
    email_verified: bool = True
    primary_goal: str | None = None
    main_use_purpose: str | None = None
    schedule_type: str | None = None
    usual_sleep_time: str | None = None
    usual_wake_time: str | None = None
    preferred_effort: str | None = None
    work_screen_required: bool = False
    # Whether this account has a recovery question, and what it is. The
    # ANSWER is never exposed anywhere - it is a credential. The
    # question is, because the client has to be able to show the user
    # what they set and offer to change it.
    has_security_question: bool = False
    security_question: str | None = None

    @staticmethod
    def from_account(account) -> "AccountResponse":
        return AccountResponse(
            user_id=account.user_id,
            email=account.email,
            display_name=account.display_name,
            is_active=account.is_active,
            onboarding_complete=account.onboarding_complete,
            created_at_utc=account.created_at_utc,
            # getattr, not attribute access: an Account rebuilt from a
            # record written before this field existed does have the
            # dataclass default, but a test double or a future adapter
            # may not, and a profile endpoint must not 500 over it.
            email_verified=bool(getattr(account, "email_verified", True)),
            primary_goal=account.primary_goal,
            main_use_purpose=account.main_use_purpose,
            schedule_type=account.schedule_type,
            usual_sleep_time=account.usual_sleep_time,
            usual_wake_time=account.usual_wake_time,
            preferred_effort=account.preferred_effort,
            work_screen_required=account.work_screen_required,
            has_security_question=bool(getattr(account, "security_answer_hash", None)),
            security_question=getattr(account, "security_question", None),
        )


class OnboardingProfileRequest(BaseModel):
    primary_goal: str
    main_use_purpose: str
    schedule_type: str
    usual_sleep_time: str
    usual_wake_time: str
    preferred_effort: str
    work_screen_required: bool = False
