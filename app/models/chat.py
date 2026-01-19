from typing import Optional
from sqlmodel import SQLModel, Field, Relationship
from datetime import datetime
from app.models.user import User

class ChatMessage(SQLModel, table=True):
    __tablename__ = "chat_messages"

    id: Optional[int] = Field(default=None, primary_key=True)
    project_id: int = Field(foreign_key="projects.id", index=True)
    user_id: int = Field(foreign_key="users.id")

    content: str
    created_at: datetime = Field(default_factory=datetime.now)

    user: Optional[User] = Relationship()
    project: Optional["Project"] = Relationship(back_populates="chats")
