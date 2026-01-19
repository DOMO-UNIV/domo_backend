from typing import Optional,List
from datetime import datetime
from sqlmodel import SQLModel, Field
from sqlmodel import SQLModel, Field, Relationship


class User(SQLModel, table=True):
    __tablename__ = "users"

    id: Optional[int] = Field(default=None, primary_key=True)
    email: str = Field(unique=True, index=True)
    password_hash: str
    name: str
    profile_image: Optional[str] = None

    is_student_verified: bool = Field(default=False)

    last_active_at: datetime = Field(default_factory=datetime.now)
    created_at: datetime = Field(default_factory=datetime.now)
    workspaces: List["WorkspaceMember"] = Relationship(back_populates="user", sa_relationship_kwargs={"cascade": "all, delete"})
