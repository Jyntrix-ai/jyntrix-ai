"""Authentication schemas."""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, EmailStr, Field, field_validator


class LoginRequest(BaseModel):
    """Request schema for user login."""

    email: EmailStr = Field(..., description="User's email address")
    password: str = Field(..., min_length=8, description="User's password")

    @field_validator("email")
    @classmethod
    def lowercase_email(cls, v: str) -> str:
        """Normalize email to lowercase."""
        return v.lower()


class LoginResponse(BaseModel):
    """Response schema for successful login."""

    access_token: str = Field(..., description="JWT access token")
    refresh_token: str = Field(..., description="JWT refresh token")
    token_type: str = Field(default="bearer")
    expires_in: int = Field(..., description="Token expiry in seconds")
    user: "UserResponse" = Field(..., description="User information")


class SignupRequest(BaseModel):
    """Request schema for user registration."""

    email: EmailStr = Field(..., description="User's email address")
    password: str = Field(
        ...,
        min_length=8,
        max_length=128,
        description="User's password (min 8 characters)"
    )
    full_name: str | None = Field(
        default=None,
        max_length=100,
        description="User's full name"
    )
    metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="Additional user metadata"
    )

    @field_validator("email")
    @classmethod
    def lowercase_email(cls, v: str) -> str:
        """Normalize email to lowercase."""
        return v.lower()

    @field_validator("password")
    @classmethod
    def validate_password(cls, v: str) -> str:
        """Validate password strength."""
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters")
        if not any(c.isupper() for c in v):
            raise ValueError("Password must contain at least one uppercase letter")
        if not any(c.islower() for c in v):
            raise ValueError("Password must contain at least one lowercase letter")
        if not any(c.isdigit() for c in v):
            raise ValueError("Password must contain at least one digit")
        return v


class SignupResponse(BaseModel):
    """Response schema for successful registration."""

    message: str = Field(
        default="Registration successful. Please check your email to verify your account."
    )
    user_id: str = Field(..., description="Created user ID")
    email: str = Field(..., description="Registered email")
    requires_verification: bool = Field(
        default=True,
        description="Whether email verification is required"
    )


class TokenResponse(BaseModel):
    """JWT token response."""

    access_token: str = Field(..., description="JWT access token")
    refresh_token: str = Field(..., description="JWT refresh token")
    token_type: str = Field(default="bearer")
    expires_in: int = Field(..., description="Token expiry in seconds")
    expires_at: datetime = Field(..., description="Token expiry timestamp")


class TokenRefreshRequest(BaseModel):
    """Request schema for token refresh."""

    refresh_token: str = Field(..., description="Current refresh token")


class TokenRefreshResponse(BaseModel):
    """Response schema for token refresh."""

    access_token: str = Field(..., description="New JWT access token")
    refresh_token: str = Field(..., description="New JWT refresh token")
    token_type: str = Field(default="bearer")
    expires_in: int = Field(..., description="Token expiry in seconds")


class UserResponse(BaseModel):
    """User information in auth responses."""

    id: str = Field(..., description="User ID")
    email: str = Field(..., description="User's email")
    full_name: str | None = Field(default=None, description="User's full name")
    avatar_url: str | None = Field(default=None, description="Avatar URL")
    email_verified: bool = Field(default=False)
    created_at: datetime | None = Field(default=None)

    class Config:
        """Pydantic configuration."""

        from_attributes = True


class PasswordResetRequest(BaseModel):
    """Request schema for password reset."""

    email: EmailStr = Field(..., description="Email address to send reset link")


class PasswordResetResponse(BaseModel):
    """Response schema for password reset request."""

    message: str = Field(
        default="If an account exists with this email, a password reset link has been sent."
    )


class PasswordUpdateRequest(BaseModel):
    """Request schema for password update."""

    current_password: str = Field(..., description="Current password")
    new_password: str = Field(
        ...,
        min_length=8,
        max_length=128,
        description="New password"
    )

    @field_validator("new_password")
    @classmethod
    def validate_password(cls, v: str) -> str:
        """Validate password strength."""
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters")
        if not any(c.isupper() for c in v):
            raise ValueError("Password must contain at least one uppercase letter")
        if not any(c.islower() for c in v):
            raise ValueError("Password must contain at least one lowercase letter")
        if not any(c.isdigit() for c in v):
            raise ValueError("Password must contain at least one digit")
        return v


class LogoutResponse(BaseModel):
    """Response schema for logout."""

    message: str = Field(default="Successfully logged out")
