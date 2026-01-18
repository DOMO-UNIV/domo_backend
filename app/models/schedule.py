from typing import Optional
from datetime import time, datetime
from sqlmodel import SQLModel, Field


class Schedule(SQLModel, table=True):
    __tablename__ = "schedules"

    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="users.id", index=True)
    day_of_week: int = Field(description="0:월, 1:화, ..., 6:일")
    start_time: time # 수업 시작 시간
    end_time: time   # 수업 종료 시간
    description: Optional[str] = None # 과목명 등


class ProjectEvent(SQLModel, table=True):
    __tablename__ = "project_events"

    id: Optional[int] = Field(default=None, primary_key=True)
    project_id: int = Field(foreign_key="projects.id")

    title: str
    description: Optional[str] = None

    # 날짜와 시간 정보를 모두 포함
    start_datetime: datetime
    end_datetime: datetime

    created_by: int = Field(foreign_key="users.id")
    created_at: datetime = Field(default_factory=datetime.now)