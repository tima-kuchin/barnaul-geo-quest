from pydantic import BaseModel, EmailStr, constr
from datetime import datetime

class UserCreate(BaseModel):
    username: constr(regex=r'^[a-zA-Z0-9]+$')
    email: EmailStr
    full_name: str
    map_api_key: str
    password: str
    confirm_password: str

class UserLogin(BaseModel):
    username: str
    password: str

class GameAttemptCreate(BaseModel):
    total_distance: int
    total_points: int
    total_time: str

class UserResponse(BaseModel):
    id: int
    username: str
    email: EmailStr
    full_name: str
    map_api_key: str
    created_at: datetime

    class Config:
        orm_mode = True