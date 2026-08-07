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


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=1, max_length=256)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class AccountResponse(BaseModel):
    user_id: str
    email: str
    display_name: str
    is_active: bool
    onboarding_complete: bool
    created_at_utc: str
    primary_goal: str | None = None
    main_use_purpose: str | None = None
    schedule_type: str | None = None
    usual_sleep_time: str | None = None
    usual_wake_time: str | None = None
    preferred_effort: str | None = None
    work_screen_required: bool = False

    @staticmethod
    def from_account(account) -> "AccountResponse":
        return AccountResponse(
            user_id=account.user_id,
            email=account.email,
            display_name=account.display_name,
            is_active=account.is_active,
            onboarding_complete=account.onboarding_complete,
            created_at_utc=account.created_at_utc,
            primary_goal=account.primary_goal,
            main_use_purpose=account.main_use_purpose,
            schedule_type=account.schedule_type,
            usual_sleep_time=account.usual_sleep_time,
            usual_wake_time=account.usual_wake_time,
            preferred_effort=account.preferred_effort,
            work_screen_required=account.work_screen_required,
        )


class OnboardingProfileRequest(BaseModel):
    primary_goal: str
    main_use_purpose: str
    schedule_type: str
    usual_sleep_time: str
    usual_wake_time: str
    preferred_effort: str
    work_screen_required: bool = False
