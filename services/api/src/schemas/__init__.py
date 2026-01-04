"""Request and response schemas for the API."""

from src.schemas.auth import (
    LoginRequest,
    LoginResponse,
    SignupRequest,
    SignupResponse,
    TokenRefreshRequest,
    TokenRefreshResponse,
    TokenResponse,
)
from src.schemas.chat import (
    ConversationCreate,
    ConversationResponse,
    ConversationUpdate,
    MessageResponse,
    SendMessageRequest,
)
from src.schemas.memory import (
    MemoryCreate,
    MemoryResponse,
    MemorySearchRequest,
    MemorySearchResponse,
    MemoryUpdate,
)

__all__ = [
    # Auth schemas
    "LoginRequest",
    "LoginResponse",
    "SignupRequest",
    "SignupResponse",
    "TokenResponse",
    "TokenRefreshRequest",
    "TokenRefreshResponse",
    # Chat schemas
    "SendMessageRequest",
    "MessageResponse",
    "ConversationCreate",
    "ConversationUpdate",
    "ConversationResponse",
    # Memory schemas
    "MemoryCreate",
    "MemoryUpdate",
    "MemoryResponse",
    "MemorySearchRequest",
    "MemorySearchResponse",
]
