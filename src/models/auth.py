"""Authentication and user models"""

from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field, EmailStr


class User(BaseModel):
    """User model for responses (no password)"""

    id: Optional[int] = None
    username: str = Field(..., min_length=3, max_length=100)
    email: EmailStr
    full_name: Optional[str] = None
    is_active: bool = True
    is_superuser: bool = False
    groups: List[str] = Field(default_factory=list, description="User's group memberships")
    department: Optional[str] = None
    country: Optional[str] = None
    created_at: Optional[datetime] = None

    class Config:
        json_schema_extra = {
            "example": {
                "username": "john.doe",
                "email": "john.doe@company.com",
                "full_name": "John Doe",
                "groups": ["all-employees", "uk-hr"],
                "department": "HR",
                "country": "UK",
            }
        }


class UserInDB(User):
    """User model with hashed password for database"""

    hashed_password: str


class UserCreate(BaseModel):
    """User creation request"""

    username: str = Field(..., min_length=3, max_length=100)
    email: EmailStr
    password: str = Field(..., min_length=8)
    full_name: Optional[str] = None
    groups: List[str] = Field(default_factory=lambda: ["all-employees"])
    department: Optional[str] = None
    country: Optional[str] = None


class Token(BaseModel):
    """JWT token response"""

    access_token: str
    token_type: str = "bearer"
    expires_in: int = Field(..., description="Token expiration in seconds")


class TokenData(BaseModel):
    """Data encoded in JWT token"""

    username: str
    groups: List[str] = Field(default_factory=list)
    department: Optional[str] = None
    country: Optional[str] = None
    exp: Optional[int] = None


class LoginRequest(BaseModel):
    """Login credentials"""

    username: str
    password: str

    class Config:
        json_schema_extra = {"example": {"username": "john.doe", "password": "password123"}}
