"""Security utilities for authentication and authorization"""

from datetime import datetime, timedelta

from fastapi import HTTPException, Security, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from passlib.context import CryptContext

from src.core.config import settings
from src.models.auth import TokenData

# Password hashing
# Configure bcrypt with explicit truncation handling for passwords > 72 bytes
pwd_context = CryptContext(
    schemes=["bcrypt"], deprecated="auto", bcrypt__default_rounds=12, bcrypt__default_ident="2b"
)

# JWT token security
security = HTTPBearer()


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash"""
    # Truncate to 72 bytes if needed (bcrypt limitation)
    password_bytes = plain_password.encode("utf-8")[:72].decode("utf-8", errors="ignore")
    return pwd_context.verify(password_bytes, hashed_password)


def get_password_hash(password: str) -> str:
    """Hash a password for storage"""
    # Truncate to 72 bytes if needed (bcrypt limitation)
    password_bytes = password.encode("utf-8")[:72].decode("utf-8", errors="ignore")
    return pwd_context.hash(password_bytes)


def create_access_token(data: dict, expires_delta: timedelta | None = None) -> str:
    """
    Create a JWT access token

    Args:
        data: Payload to encode in the token
        expires_delta: Token expiration time

    Returns:
        Encoded JWT token string
    """
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)

    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)
    return encoded_jwt


def decode_token(token: str) -> TokenData:
    """
    Decode and validate a JWT token

    Args:
        token: JWT token string

    Returns:
        TokenData with user information

    Raises:
        HTTPException: If token is invalid or expired
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        payload = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception

        token_data = TokenData(
            username=username,
            groups=payload.get("groups", []),
            department=payload.get("department"),
            country=payload.get("country"),
            exp=payload.get("exp"),
        )
        return token_data
    except JWTError:
        raise credentials_exception


def get_current_user(credentials: HTTPAuthorizationCredentials = Security(security)) -> TokenData:
    """
    FastAPI dependency to get current authenticated user from JWT token

    Args:
        credentials: HTTP Authorization credentials from request

    Returns:
        TokenData with user information

    Raises:
        HTTPException: If authentication fails
    """
    token = credentials.credentials
    return decode_token(token)


def check_permission(user: TokenData, required_groups: list[str]) -> bool:
    """
    Check if user has required group membership

    Args:
        user: User token data
        required_groups: List of required group names

    Returns:
        True if user is in any of the required groups
    """
    if not required_groups:
        return True

    user_groups = set(user.groups)
    required = set(required_groups)
    return bool(user_groups & required)


def require_groups(required_groups: list[str]):
    """
    Dependency factory to require specific group memberships

    Args:
        required_groups: List of group names, user must be in at least one

    Returns:
        FastAPI dependency function

    Example:
        @app.get("/admin", dependencies=[Depends(require_groups(["admin"]))])
    """

    def _check_groups(user: TokenData = Security(get_current_user)) -> TokenData:
        if not check_permission(user, required_groups):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Requires membership in one of: {', '.join(required_groups)}",
            )
        return user

    return _check_groups
