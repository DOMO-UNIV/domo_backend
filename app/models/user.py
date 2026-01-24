from typing import Optional,List
from datetime import datetime
from sqlmodel import SQLModel, Field, Relationship



class User(SQLModel, table=True):
    __tablename__ = "users"

    id: Optional[int] = Field(default=None, primary_key=True)
    email: str = Field(unique=True, index=True)
    password_hash: str
    name: str
    nickname: Optional[str] = Field(default=None)
    profile_image: Optional[str] = None

    is_student_verified: bool = Field(default=False)

    is_active: bool = Field(default=True) # 탈퇴 시 False로 변경
    deleted_at: Optional[datetime] = Field(default=None) # 언제 탈퇴했는지 기록

    last_active_at: datetime = Field(default_factory=datetime.now)
    created_at: datetime = Field(default_factory=datetime.now)
    workspaces: List["WorkspaceMember"] = Relationship(back_populates="user", sa_relationship_kwargs={"cascade": "all, delete"})
