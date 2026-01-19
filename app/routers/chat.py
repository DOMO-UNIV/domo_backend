# app/routers/chat.py

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlmodel import Session, select
from typing import List
from datetime import datetime

from app.database import get_db
from app.models.chat import ChatMessage
from app.models.user import User
from app.schemas import ChatMessageResponse, ChatMessageCreate
from app.routers.workspace import get_current_user_id
from vectorwave import vectorize

router = APIRouter(tags=["Project Chat"])

# 1. 채팅 메시지 목록 조회 (Polling용)
# 프론트엔드: 1~3초마다 이 API를 호출해서 새로운 메시지가 있는지 확인합니다.
@router.get("/projects/{project_id}/chat", response_model=List[ChatMessageResponse])
def get_chat_messages(
        project_id: int,
        limit: int = 50,
        after_id: int = 0,  # 👈 핵심: 이 ID 이후의 메시지만 가져오기 (최적화)
        db: Session = Depends(get_db),
        user_id: int = Depends(get_current_user_id)
):
    query = select(ChatMessage).where(ChatMessage.project_id == project_id)

    # 마지막으로 받은 메시지 이후의 것만 조회 (대역폭 절약)
    if after_id > 0:
        query = query.where(ChatMessage.id > after_id)

    # 최신순 정렬 -> 다시 시간순 정렬
    messages = db.exec(query.order_by(ChatMessage.created_at.desc()).limit(limit)).all()

    # 시간순으로 정렬해서 반환 (과거 -> 현재)
    return list(reversed(messages))

# 2. 채팅 메시지 전송 (일반 HTTP POST)
@router.post("/projects/{project_id}/chat", response_model=ChatMessageResponse)
@vectorize(search_description="Send chat message", capture_return_value=True)
def send_chat_message(
        project_id: int,
        message_data: ChatMessageCreate,
        db: Session = Depends(get_db),
        user_id: int = Depends(get_current_user_id)
):
    # 유저 정보 조회 (응답용)
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # 메시지 저장
    new_msg = ChatMessage(
        project_id=project_id,
        user_id=user_id,
        content=message_data.content
    )
    db.add(new_msg)
    db.commit()
    db.refresh(new_msg)

    return new_msg