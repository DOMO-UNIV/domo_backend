# app/routers/chat.py

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlmodel import Session, select
from typing import List
from datetime import datetime
from fastapi.responses import StreamingResponse
from app.database import get_db
from app.models.chat import ChatMessage
from app.models.user import User
from app.schemas import ChatMessageResponse, ChatMessageCreate
from app.routers.workspace import get_current_user_id
from vectorwave import vectorize
import asyncio
import json

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

# ✅ [신규] SSE 기반 실시간 채팅 스트림
@router.get("/projects/{project_id}/chat/stream")
async def stream_chat_messages(
        project_id: int,
        request: Request,
        db: Session = Depends(get_db)
):
    """
    Server-Sent Events (SSE) 엔드포인트
    클라이언트가 연결하면, 1초마다 DB를 확인해서 새로운 메시지가 있으면 '푸시'해줍니다.
    """

    async def event_generator():
        # 처음 연결 시점의 가장 마지막 메시지 ID를 가져옵니다.
        last_msg = db.exec(
            select(ChatMessage)
            .where(ChatMessage.project_id == project_id)
            .order_by(ChatMessage.id.desc())
            .limit(1)
        ).first()

        last_id = last_msg.id if last_msg else 0

        # 연결이 끊기지 않는 동안 계속 루프를 돕니다.
        while True:
            # 클라이언트 연결이 끊겼는지 체크
            if await request.is_disconnected():
                break

            # 1. 새로운 메시지가 있는지 조회 (마지막 ID보다 큰 것)
            # 주의: 실제 프로덕션에서는 Redis 등을 쓰지만, 간단하게 DB 폴링으로 구현합니다.
            new_messages = db.exec(
                select(ChatMessage)
                .where(ChatMessage.project_id == project_id)
                .where(ChatMessage.id > last_id)
                .order_by(ChatMessage.id.asc())
            ).all()

            # 2. 새 메시지가 있으면 전송
            if new_messages:
                for msg in new_messages:
                    # 보낼 데이터를 JSON 문자열로 변환
                    data = json.dumps({
                        "id": msg.id,
                        "content": msg.content,
                        "user_id": msg.user_id,
                        "created_at": msg.created_at.isoformat()
                    }, ensure_ascii=False)

                    # SSE 형식 (data: {json}\n\n)에 맞춰 전송
                    yield f"data: {data}\n\n"

                    # 마지막 ID 갱신
                    last_id = msg.id

            # 3. 1초 대기 (서버 부하 방지)
            await asyncio.sleep(1)

    return StreamingResponse(event_generator(), media_type="text/event-stream")