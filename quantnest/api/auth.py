"""Authentication endpoints: register, login, refresh, profile and wallets."""

from __future__ import annotations

import logging
from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, status
from pydantic import BaseModel, ConfigDict, EmailStr, Field

from quantnest.api.deps import AuthServiceDep, CurrentUserDep

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["auth"])


# ── Schemas ──────────────────────────────────────────────────────────────


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class RegisterRequest(StrictModel):
    email: EmailStr = Field(description="Account email address")
    password: str = Field(
        min_length=8,
        max_length=128,
        description="At least 8 characters",
        examples=["correct-horse-battery"],
    )
    display_name: Optional[str] = Field(default=None, max_length=120)


class LoginRequest(StrictModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=128)


class RefreshRequest(StrictModel):
    refresh_token: str = Field(min_length=1)


class CreateWalletRequest(StrictModel):
    wallet_id: str = Field(
        min_length=1,
        max_length=64,
        pattern=r"^[A-Za-z0-9._\-]{1,64}$",
        description="URL-safe identifier",
    )
    label: Optional[str] = Field(default=None, max_length=120)


class UserProfile(BaseModel):
    user_id: str
    email: str
    display_name: Optional[str] = None
    wallets: List[str] = Field(default_factory=list)


class SessionResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    user: UserProfile


class WalletSummary(BaseModel):
    wallet_id: str
    label: Optional[str] = None
    created_at: datetime


# ── Routes ───────────────────────────────────────────────────────────────


@router.post(
    "/register",
    response_model=SessionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create an account",
)
async def register(request: RegisterRequest, auth: AuthServiceDep) -> SessionResponse:
    """Register a new user and provision their first wallet.

    Returns a token pair so the client is signed in immediately.
    """
    payload = auth.register(
        email=str(request.email),
        password=request.password,
        display_name=request.display_name,
    )
    return SessionResponse(**payload)


@router.post("/login", response_model=SessionResponse, summary="Sign in")
async def login(request: LoginRequest, auth: AuthServiceDep) -> SessionResponse:
    """Exchange email and password for an access and refresh token pair.

    Responds with an identical 401 whether the email is unknown or the
    password is wrong, so the endpoint cannot be used to enumerate accounts.
    """
    payload = auth.login(email=str(request.email), password=request.password)
    return SessionResponse(**payload)


@router.post("/refresh", response_model=SessionResponse, summary="Renew a session")
async def refresh(request: RefreshRequest, auth: AuthServiceDep) -> SessionResponse:
    """Issue a fresh token pair from a valid refresh token."""
    payload = auth.refresh(request.refresh_token)
    return SessionResponse(**payload)


@router.get("/me", response_model=UserProfile, summary="Current user profile")
async def me(current_user: CurrentUserDep, auth: AuthServiceDep) -> UserProfile:
    return UserProfile(
        user_id=current_user.user_id,
        email=current_user.email,
        display_name=current_user.display_name,
        wallets=[w["wallet_id"] for w in auth.list_wallets(current_user)],
    )


@router.get("/wallets", response_model=List[WalletSummary], summary="List your wallets")
async def list_wallets(
    current_user: CurrentUserDep, auth: AuthServiceDep
) -> List[WalletSummary]:
    return [WalletSummary(**wallet) for wallet in auth.list_wallets(current_user)]


@router.post(
    "/wallets",
    response_model=WalletSummary,
    status_code=status.HTTP_201_CREATED,
    summary="Create an additional wallet",
)
async def create_wallet(
    request: CreateWalletRequest,
    current_user: CurrentUserDep,
    auth: AuthServiceDep,
) -> WalletSummary:
    wallet = auth.create_wallet(current_user, request.wallet_id, request.label)
    return WalletSummary(
        wallet_id=wallet.wallet_id,
        label=wallet.label,
        created_at=wallet.created_at,
    )
