# app/models/community.py

from datetime import datetime
from typing import Optional, List
from sqlmodel import SQLModel, Field, Relationship
from app.models.user import User


class CommunityPost(SQLModel, table=True):
    __tablename__ = "community_posts"

    id: Optional[int] = Field(default=None, primary_key=True)
    title: str
    content: str
    image_url: Optional[str] = None  # ✅ 사진 1장 (필수 아님, 선택)

    user_id: int = Field(foreign_key="users.id")
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)

    # 작성자 정보 (Join용)
    user: Optional[User] = Relationship()
    # 댓글들
    comments: List["CommunityComment"] = Relationship(back_populates="post",
                                                      sa_relationship_kwargs={"cascade": "all, delete"})


class CommunityComment(SQLModel, table=True):
    __tablename__ = "community_comments"

    id: Optional[int] = Field(default=None, primary_key=True)
    content: str

    post_id: int = Field(foreign_key="community_posts.id")
    user_id: int = Field(foreign_key="users.id")
    created_at: datetime = Field(default_factory=datetime.now)

    user: Optional[User] = Relationship()
    post: Optional[CommunityPost] = Relationship(back_populates="comments")
