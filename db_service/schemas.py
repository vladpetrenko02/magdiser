from pydantic import BaseModel, EmailStr
from datetime import datetime

class UserBase(BaseModel):
    username: str
    email: EmailStr

class UserCreate(UserBase):
    password: str

class UserResponse(UserBase):
    user_id: int
    created_at: datetime

    class Config:
        from_attributes = True

class UserWithToken(BaseModel):
    user: UserResponse
    access_token: str
    token_type: str

class UserActivityCreate(BaseModel):
    user_id: int
    activity_count: float
    activity_recency: float
    activity_interval: float
    activity_intensity: float

class UserLogin(BaseModel):
    email: str
    password: str

class GenreRequest(BaseModel):
    genres: list[str]