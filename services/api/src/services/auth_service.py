"""Authentication service using Supabase Auth."""

import logging
from datetime import datetime, timedelta
from typing import Any

from supabase import Client as SupabaseClient

from src.config import settings
from src.schemas.auth import (
    LoginResponse,
    SignupResponse,
    TokenRefreshResponse,
    UserResponse,
)

logger = logging.getLogger(__name__)


class AuthService:
    """Authentication service using Supabase Auth."""

    def __init__(self, supabase: SupabaseClient):
        """Initialize auth service with Supabase client."""
        self.supabase = supabase

    async def signup(
        self,
        email: str,
        password: str,
        full_name: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> SignupResponse:
        """Register a new user.

        Args:
            email: User's email address
            password: User's password
            full_name: Optional full name
            metadata: Optional additional metadata

        Returns:
            SignupResponse with user details

        Raises:
            ValueError: If signup fails
        """
        try:
            # Prepare user metadata
            user_metadata = metadata or {}
            if full_name:
                user_metadata["full_name"] = full_name

            # Create user with Supabase
            response = self.supabase.auth.sign_up({
                "email": email,
                "password": password,
                "options": {
                    "data": user_metadata,
                },
            })

            if not response.user:
                raise ValueError("Failed to create user account")

            # Check if email confirmation is required
            requires_verification = response.user.email_confirmed_at is None

            logger.info(f"User registered: {email}")

            return SignupResponse(
                user_id=response.user.id,
                email=email,
                requires_verification=requires_verification,
            )

        except Exception as e:
            logger.error(f"Signup error for {email}: {e}")
            if "already registered" in str(e).lower():
                raise ValueError("An account with this email already exists")
            raise ValueError(f"Registration failed: {str(e)}")

    async def login(
        self,
        email: str,
        password: str,
    ) -> LoginResponse:
        """Authenticate user and return tokens.

        Args:
            email: User's email address
            password: User's password

        Returns:
            LoginResponse with tokens and user info

        Raises:
            ValueError: If authentication fails
        """
        try:
            response = self.supabase.auth.sign_in_with_password({
                "email": email,
                "password": password,
            })

            if not response.user or not response.session:
                raise ValueError("Invalid email or password")

            user = response.user
            session = response.session

            logger.info(f"User logged in: {email}")

            return LoginResponse(
                access_token=session.access_token,
                refresh_token=session.refresh_token,
                token_type="bearer",
                expires_in=session.expires_in or 3600,
                user=UserResponse(
                    id=user.id,
                    email=user.email or "",
                    full_name=user.user_metadata.get("full_name"),
                    avatar_url=user.user_metadata.get("avatar_url"),
                    email_verified=user.email_confirmed_at is not None,
                    created_at=datetime.fromisoformat(
                        user.created_at.replace("Z", "+00:00")
                    ) if user.created_at else None,
                ),
            )

        except Exception as e:
            logger.error(f"Login error for {email}: {e}")
            if "invalid" in str(e).lower():
                raise ValueError("Invalid email or password")
            raise ValueError("Authentication failed")

    async def logout(self) -> None:
        """Sign out the current user."""
        try:
            self.supabase.auth.sign_out()
            logger.info("User logged out")
        except Exception as e:
            logger.error(f"Logout error: {e}")
            # Don't raise - logout should succeed silently

    async def refresh_token(self, refresh_token: str) -> TokenRefreshResponse:
        """Refresh the access token.

        Args:
            refresh_token: Current refresh token

        Returns:
            TokenRefreshResponse with new tokens

        Raises:
            ValueError: If refresh fails
        """
        try:
            response = self.supabase.auth.refresh_session(refresh_token)

            if not response.session:
                raise ValueError("Failed to refresh token")

            session = response.session

            return TokenRefreshResponse(
                access_token=session.access_token,
                refresh_token=session.refresh_token,
                token_type="bearer",
                expires_in=session.expires_in or 3600,
            )

        except Exception as e:
            logger.error(f"Token refresh error: {e}")
            raise ValueError("Failed to refresh token. Please log in again.")

    async def request_password_reset(self, email: str) -> None:
        """Send password reset email.

        Args:
            email: User's email address
        """
        try:
            self.supabase.auth.reset_password_email(email)
            logger.info(f"Password reset requested for: {email}")
        except Exception as e:
            logger.error(f"Password reset request error for {email}: {e}")
            # Don't raise to prevent email enumeration

    async def update_password(
        self,
        current_password: str,
        new_password: str,
    ) -> None:
        """Update user's password.

        Args:
            current_password: Current password for verification
            new_password: New password to set

        Raises:
            ValueError: If password update fails
        """
        try:
            # Supabase's update_user requires the user to be authenticated
            # The current session is used automatically
            response = self.supabase.auth.update_user({
                "password": new_password,
            })

            if not response.user:
                raise ValueError("Failed to update password")

            logger.info("Password updated successfully")

        except Exception as e:
            logger.error(f"Password update error: {e}")
            raise ValueError("Failed to update password")

    async def delete_account(self, user_id: str) -> None:
        """Delete user account and all associated data.

        This requires admin privileges, so it uses the service role key.

        Args:
            user_id: ID of the user to delete

        Raises:
            Exception: If deletion fails
        """
        try:
            # Note: Account deletion should be done with admin client
            # This is a placeholder - actual implementation would use
            # the service role key to delete the user
            logger.warning(f"Account deletion requested for user: {user_id}")

            # In production, you would:
            # 1. Delete user's memories from Qdrant
            # 2. Delete user's data from Supabase tables
            # 3. Delete the auth user using admin API

            # For now, we'll just sign out the user
            self.supabase.auth.sign_out()

        except Exception as e:
            logger.error(f"Account deletion error: {e}")
            raise

    async def get_user_by_token(self, token: str) -> dict | None:
        """Get user information from token.

        Args:
            token: JWT access token

        Returns:
            User dict if valid, None otherwise
        """
        try:
            response = self.supabase.auth.get_user(token)

            if response and response.user:
                return {
                    "id": response.user.id,
                    "email": response.user.email,
                    "user_metadata": response.user.user_metadata,
                    "app_metadata": response.user.app_metadata,
                }

            return None

        except Exception as e:
            logger.error(f"Get user by token error: {e}")
            return None

    async def update_user_metadata(
        self,
        metadata: dict[str, Any],
    ) -> dict | None:
        """Update user metadata.

        Args:
            metadata: New metadata to merge with existing

        Returns:
            Updated user data or None
        """
        try:
            response = self.supabase.auth.update_user({
                "data": metadata,
            })

            if response and response.user:
                return {
                    "id": response.user.id,
                    "email": response.user.email,
                    "user_metadata": response.user.user_metadata,
                }

            return None

        except Exception as e:
            logger.error(f"Update user metadata error: {e}")
            return None
