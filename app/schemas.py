from pydantic import BaseModel, EmailStr
from typing import Optional
from datetime import time as dt_time

# data for register
class UserCreate(BaseModel):
    email: EmailStr
    password: str
    name: str


# data for login
class UserLogin(BaseModel):
    email: EmailStr
    password: str


# data for response
class UserResponse(BaseModel):
    id: int
    email: EmailStr
    name: str
    is_student_verified: bool
    profile_image: Optional[str] = None


class WorkspaceCreate(BaseModel):
    name: str
    description: Optional[str] = None


class WorkspaceResponse(BaseModel):
    id: int
    name: str
    owner_id: int
    description: Optional[str] = None


class ProjectCreate(BaseModel):
    name: str
    description: Optional[str] = None


class ProjectResponse(BaseModel):
    id: int
    name: str
    workspace_id: int


class BoardColumnCreate(BaseModel):
    title: str
    order: Optional[int] = 0


class BoardColumnResponse(BaseModel):
    id: int
    title: str
    order: int
    project_id: int


class CardCreate(BaseModel):
    title: str
    content: Optional[str] = None
    order: Optional[int] = 0


class CardResponse(BaseModel):
    id: int
    title: str
    content: Optional[str] = None
    order: int
    column_id: int
    assignee_id: Optional[int] = None


class CardUpdate(BaseModel):
    title: Optional[str] = None
    content: Optional[str] = None
    column_id: Optional[int] = None
    order: Optional[int] = None


class ScheduleCreate(BaseModel):
    day_of_week: int
    start_time: dt_time
    end_time: dt_time
    description: Optional[str] = None

class ScheduleResponse(BaseModel):
    id: int
    user_id: int
    day_of_week: int
    start_time: dt_time
    end_time: dt_time
    description: Optional[str] = None

class FreeTimeSlot(BaseModel):
    day_of_week: int
    start_time: dt_time
    end_time: dt_time
