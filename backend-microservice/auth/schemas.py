# app/schemas.py

from pydantic import BaseModel, EmailStr

class UserBase(BaseModel):
    email: EmailStr

class UserCreate(UserBase):
    user_name: str
    password: str
    otp_code: str  # Required during registration

class UserOut(UserBase):
    id: int
    is_active: bool
    user_name: str
    role: str

    class Config:
        from_attributes = True

class LoginRequest(BaseModel):
    email: EmailStr
    password: str
    otp_code: str  # Now required