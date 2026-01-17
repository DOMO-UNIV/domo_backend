from sqlmodel import Session
from app.models.activity import ActivityLog

def log_activity(
        db: Session,
        user_id: int,
        content: str,
        action_type: str,
        workspace_id: int = None
):
    """
    활동 로그를 DB에 저장하는 헬퍼 함수
    """
    log = ActivityLog(
        user_id=user_id,
        content=content,
        action_type=action_type,
        workspace_id=workspace_id
    )
    db.add(log)
    db.commit()