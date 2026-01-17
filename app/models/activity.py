from datetime import datetime
from typing import Optional
from sqlmodel import SQLModel, Field

class ActivityLog(SQLModel, table=True):
    __tablename__ = "activity_logs"

    id: Optional[int] = Field(default=None, primary_key=True)

    user_id: int = Field(foreign_key="users.id", index=True)      # 누가
    workspace_id: Optional[int] = Field(default=None, foreign_key="workspaces.id", index=True) # 어디서

    content: str  # 내용 (예: "김철수님이 새 프로젝트 '알파'를 생성했습니다.")
    action_type: str # 분류 (CREATE, UPDATE, DELETE, UPLOAD 등) - 필터링용

    created_at: datetime = Field(default_factory=datetime.now)