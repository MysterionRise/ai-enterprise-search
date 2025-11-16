"""Authentication endpoints"""

from datetime import timedelta
from fastapi import APIRouter, HTTPException, status, Security
from typing import Annotated

from src.models.auth import LoginRequest, Token, User, UserCreate, TokenData
from src.core.config import settings
from src.core.security import (
    verify_password,
    get_password_hash,
    create_access_token,
    get_current_user,
)
from src.core.database import get_user_by_username, create_user, get_user_by_email

router = APIRouter()


@router.post("/login", response_model=Token)
async def login(credentials: LoginRequest):
    """
    Authenticate user and return JWT access token

    This endpoint validates username/password and returns a JWT token
    containing user identity and group memberships for authorization.

    Demo users (password: 'password123'):
    - john.doe (UK, HR)
    - jane.smith (US, Engineering)
    - admin (US, IT, Admin)
    """
    # Get user from database
    user_record = get_user_by_username(credentials.username)

    if not user_record:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Verify password
    if not verify_password(credentials.password, user_record["hashed_password"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Check if user is active
    if not user_record.get("is_active", True):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="User account is inactive"
        )

    # Create access token with user context
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    token_data = {
        "sub": user_record["username"],
        "groups": user_record.get("groups", []),
        "department": user_record.get("department"),
        "country": user_record.get("country"),
    }
    access_token = create_access_token(data=token_data, expires_delta=access_token_expires)

    return Token(
        access_token=access_token,
        token_type="bearer",
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )


@router.post("/register", response_model=User, status_code=status.HTTP_201_CREATED)
async def register(user_data: UserCreate):
    """
    Register a new user account

    Creates a new user with the provided details. All new users
    are automatically added to the 'all-employees' group.
    """
    # Check if username already exists
    existing_user = get_user_by_username(user_data.username)
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Username already registered"
        )

    # Check if email already exists
    existing_email = get_user_by_email(user_data.email)
    if existing_email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Email already registered"
        )

    # Hash password
    hashed_password = get_password_hash(user_data.password)

    # Ensure all-employees group is included
    groups = list(set(user_data.groups + ["all-employees"]))

    # Create user in database
    user_record = create_user(
        username=user_data.username,
        email=user_data.email,
        hashed_password=hashed_password,
        full_name=user_data.full_name,
        groups=groups,
        department=user_data.department,
        country=user_data.country,
    )

    return User(
        id=user_record["id"],
        username=user_record["username"],
        email=user_record["email"],
        full_name=user_record["full_name"],
        groups=user_record["groups"],
        department=user_record["department"],
        country=user_record["country"],
        created_at=user_record["created_at"],
        is_active=True,
        is_superuser=False,
    )


@router.get("/me", response_model=User)
async def get_current_user_info(current_user: Annotated[TokenData, Security(get_current_user)]):
    """
    Get current authenticated user information

    Returns user profile including group memberships and department/country
    which are used for personalized search results.
    """
    # Get full user details from database
    user_record = get_user_by_username(current_user.username)

    if not user_record:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    return User(
        id=user_record["id"],
        username=user_record["username"],
        email=user_record["email"],
        full_name=user_record.get("full_name"),
        groups=user_record.get("groups", []),
        department=user_record.get("department"),
        country=user_record.get("country"),
        created_at=user_record.get("created_at"),
        is_active=user_record.get("is_active", True),
        is_superuser=user_record.get("is_superuser", False),
    )


@router.post("/refresh", response_model=Token)
async def refresh_token(current_user: Annotated[TokenData, Security(get_current_user)]):
    """
    Refresh JWT access token

    Generates a new token with extended expiration for the current user.
    """
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    token_data = {
        "sub": current_user.username,
        "groups": current_user.groups,
        "department": current_user.department,
        "country": current_user.country,
    }
    access_token = create_access_token(data=token_data, expires_delta=access_token_expires)

    return Token(
        access_token=access_token,
        token_type="bearer",
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )
