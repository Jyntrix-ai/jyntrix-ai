"""Authentication routes using Supabase Auth."""

import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from src.dependencies import CurrentUser, SupabaseDep, get_supabase
from src.schemas.auth import (
    LoginRequest,
    LoginResponse,
    LogoutResponse,
    PasswordResetRequest,
    PasswordResetResponse,
    PasswordUpdateRequest,
    SignupRequest,
    SignupResponse,
    TokenRefreshRequest,
    TokenRefreshResponse,
    UserResponse,
)
from src.services.auth_service import AuthService

logger = logging.getLogger(__name__)

router = APIRouter()
security = HTTPBearer(auto_error=False)


def get_auth_service(supabase: SupabaseDep) -> AuthService:
    """Get auth service instance."""
    return AuthService(supabase)


@router.post(
    "/signup",
    response_model=SignupResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new user",
    description="Create a new user account with email and password",
)
async def signup(
    request: SignupRequest,
    auth_service: AuthService = Depends(get_auth_service),
) -> SignupResponse:
    """Register a new user."""
    try:
        result = await auth_service.signup(
            email=request.email,
            password=request.password,
            full_name=request.full_name,
            metadata=request.metadata,
        )
        return result
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except Exception as e:
        logger.error(f"Signup error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create account",
        )


@router.post(
    "/login",
    response_model=LoginResponse,
    summary="Login with email and password",
    description="Authenticate user and return JWT tokens",
)
async def login(
    request: LoginRequest,
    auth_service: AuthService = Depends(get_auth_service),
) -> LoginResponse:
    """Authenticate user and return tokens."""
    try:
        result = await auth_service.login(
            email=request.email,
            password=request.password,
        )
        return result
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e),
            headers={"WWW-Authenticate": "Bearer"},
        )
    except Exception as e:
        logger.error(f"Login error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Authentication failed",
        )


@router.post(
    "/logout",
    response_model=LogoutResponse,
    summary="Logout current user",
    description="Invalidate the current session",
)
async def logout(
    current_user: CurrentUser,
    auth_service: AuthService = Depends(get_auth_service),
) -> LogoutResponse:
    """Logout and invalidate session."""
    try:
        await auth_service.logout()
        return LogoutResponse()
    except Exception as e:
        logger.error(f"Logout error: {e}")
        # Still return success to client
        return LogoutResponse()


@router.post(
    "/refresh",
    response_model=TokenRefreshResponse,
    summary="Refresh access token",
    description="Get new access token using refresh token",
)
async def refresh_token(
    request: TokenRefreshRequest,
    auth_service: AuthService = Depends(get_auth_service),
) -> TokenRefreshResponse:
    """Refresh the access token."""
    try:
        result = await auth_service.refresh_token(request.refresh_token)
        return result
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e),
            headers={"WWW-Authenticate": "Bearer"},
        )
    except Exception as e:
        logger.error(f"Token refresh error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to refresh token",
        )


@router.get(
    "/me",
    response_model=UserResponse,
    summary="Get current user",
    description="Get information about the currently authenticated user",
)
async def get_current_user_info(
    current_user: CurrentUser,
) -> UserResponse:
    """Get current user information."""
    return UserResponse(
        id=current_user.id,
        email=current_user.email,
        full_name=current_user.full_name,
        avatar_url=current_user.avatar_url,
        email_verified=True,  # If they got here, they're verified via Supabase
    )


@router.post(
    "/password/reset",
    response_model=PasswordResetResponse,
    summary="Request password reset",
    description="Send password reset email to user",
)
async def request_password_reset(
    request: PasswordResetRequest,
    auth_service: AuthService = Depends(get_auth_service),
) -> PasswordResetResponse:
    """Request a password reset email."""
    try:
        await auth_service.request_password_reset(request.email)
        return PasswordResetResponse()
    except Exception as e:
        logger.error(f"Password reset request error: {e}")
        # Always return success to prevent email enumeration
        return PasswordResetResponse()


@router.post(
    "/password/update",
    response_model=dict[str, Any],
    summary="Update password",
    description="Update password for authenticated user",
)
async def update_password(
    request: PasswordUpdateRequest,
    current_user: CurrentUser,
    auth_service: AuthService = Depends(get_auth_service),
) -> dict[str, Any]:
    """Update user's password."""
    try:
        await auth_service.update_password(
            current_password=request.current_password,
            new_password=request.new_password,
        )
        return {"message": "Password updated successfully"}
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except Exception as e:
        logger.error(f"Password update error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update password",
        )


@router.post(
    "/verify",
    response_model=dict[str, Any],
    summary="Verify authentication token",
    description="Verify if the provided token is valid",
)
async def verify_token(
    supabase: SupabaseDep,
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> dict[str, Any]:
    """Verify if a token is valid."""
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="No token provided",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        response = supabase.auth.get_user(credentials.credentials)
        if response and response.user:
            return {
                "valid": True,
                "user_id": response.user.id,
                "email": response.user.email,
            }
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except Exception as e:
        logger.error(f"Token verification error: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token verification failed",
            headers={"WWW-Authenticate": "Bearer"},
        )


@router.delete(
    "/account",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete account",
    description="Permanently delete user account and all associated data",
)
async def delete_account(
    current_user: CurrentUser,
    auth_service: AuthService = Depends(get_auth_service),
) -> None:
    """Delete user account."""
    try:
        await auth_service.delete_account(current_user.id)
    except Exception as e:
        logger.error(f"Account deletion error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete account",
        )
