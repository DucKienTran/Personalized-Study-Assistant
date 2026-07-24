from datetime import datetime
import re
from typing import List, Optional

from pydantic import (
    BaseModel,
    ConfigDict,
    EmailStr,
    Field,
    field_validator,
    model_validator,
)
from typing_extensions import Self


def validate_strong_password_logic(value: str) -> str:
    if not re.search(r"[A-Z]", value):
        raise ValueError("Password must contain at least one uppercase letter.")
    if not re.search(r"[a-z]", value) or not re.search(r"[0-9]", value):
        raise ValueError("Password must contain both lowercase letters and digits.")
    if not re.search(r"[!@#$%^&*(),.?\":{}|<>]", value):
        raise ValueError("Password must contain at least one special character (!@#$%^&*...).")
    return value


class MessageResponse(BaseModel):
    detail: str


class UserRegister(BaseModel):
    email: EmailStr
    password: str = Field(
        ..., min_length=8, description="Password must be at least 8 characters long."
    )
    confirm_password: str = Field(
        ..., min_length=8, description="Confirmation password must be at least 8 characters long."
    )
    full_name: Optional[str] = None

    @model_validator(mode="after")
    def check_passwords_match(self) -> Self:
        if self.password != self.confirm_password:
            raise ValueError("Passwords do not match.")
        return self

    @field_validator("password")
    @classmethod
    def validate_password(cls, value: str) -> str:
        return validate_strong_password_logic(value)


class VerifyEmailRequest(BaseModel):
    token: str


class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str = Field(
        ..., min_length=8, description="New password must be at least 8 characters long."
    )
    confirm_new_password: str = Field(
        ..., min_length=8, description="Confirmation password must be at least 8 characters long."
    )

    @model_validator(mode="after")
    def check_passwords_match(self) -> Self:
        if self.new_password != self.confirm_new_password:
            raise ValueError("Passwords do not match.")
        return self

    @field_validator("new_password")
    @classmethod
    def validate_new_password(cls, value: str) -> str:
        return validate_strong_password_logic(value)


class ChangePassword(BaseModel):
    old_password: str
    new_password: str = Field(
        ..., min_length=8, description="New password must be at least 8 characters long."
    )
    confirm_new_password: str = Field(
        ..., min_length=8, description="Confirmation password must be at least 8 characters long."
    )

    @model_validator(mode="after")
    def check_passwords_match(self) -> Self:
        if self.new_password != self.confirm_new_password:
            raise ValueError("Passwords do not match.")
        return self

    @field_validator("new_password")
    @classmethod
    def validate_new_password(cls, value: str) -> str:
        return validate_strong_password_logic(value)


class UserStatus(BaseModel):
    user_id: int
    email: str
    role: str
    status: str
    message: str
    last_active: Optional[int] = None


class UserLogin(BaseModel):
    email: EmailStr
    password: str
    remember_me: bool = False


class UserResponse(BaseModel):
    id: int
    email: EmailStr
    role_name: str
    full_name: Optional[str] = None
    is_active: bool
    created_at: datetime
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class CurrentUser(BaseModel):
    id: int
    email: EmailStr
    role: str
    permissions: List[str] = Field(default_factory=list)