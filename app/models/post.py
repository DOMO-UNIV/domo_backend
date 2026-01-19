from typing import Optional, List
from sqlmodel import SQLModel, Field, Relationship
from datetime import datetime
from app.models.user import User  # User 모델 참조를 위해

class Post(SQLModel, table=True):
    __tablename__ = "posts"

    id: Optional[int] = Field(default=None, primary_key=True)
    project_id: int = Field(foreign_key="projects.id")
    user_id: int = Field(foreign_key="users.id")

    title: str
    content: str

    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)

    # 관계 설정
    comments: List["PostComment"] = Relationship(back_populates="post", sa_relationship_kwargs={"cascade": "all, delete"})
    user: Optional[User] = Relationship()
    project: Optional["Project"] = Relationship(back_populates="posts")


class PostComment(SQLModel, table=True):
    __tablename__ = "post_comments"

    id: Optional[int] = Field(default=None, primary_key=True)
    post_id: int = Field(foreign_key="posts.id")
    user_id: int = Field(foreign_key="users.id")

    content: str
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)

    post: Optional[Post] = Relationship(back_populates="comments")
    user: Optional[User] = Relationship()