from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from app.utils.connection_manager import voice_manager
import logging

router = APIRouter(tags=["Voice Chat"])
logger = logging.getLogger(__name__)


@router.websocket("/ws/projects/{project_id}/voice")
async def voice_chat_endpoint(websocket: WebSocket, project_id: int):
    """
    음성 채팅 WebSocket 엔드포인트
    WebRTC Signaling 서버 역할 수행
    
    Signaling Flow:
    1. Client A connects -> receives "room_info" with existing peer count
    2. Client A sends "join" with senderId
    3. Server broadcasts "join" to all other clients
    4. Existing clients receive "join" and send "offer" to new client
    5. New client receives "offer" and responds with "answer"
    6. Both exchange "ice" candidates
    7. WebRTC connection established
    """
    # 연결 수락
    await voice_manager.connect(websocket, project_id)
    logger.info(f"[Voice] New WebSocket connection to project {project_id}")
    
    # 해당 소켓의 userId 저장용 (disconnect 시 사용)
    user_id = None
    
    try:
        while True:
            # 클라이언트로부터 메시지 수신
            data = await websocket.receive_json()
            msg_type = data.get("type")
            sender_id = data.get("senderId")
            
            logger.info(f"[Voice] Received: type={msg_type}, senderId={sender_id}, project={project_id}")
            
            if msg_type == "join":
                # userId 저장 (disconnect 시 사용)
                user_id = sender_id
                voice_manager.register_user(websocket, project_id, sender_id)
                
                # 현재 방의 다른 참여자 수 확인
                peer_count = voice_manager.get_peer_count(project_id, websocket)
                logger.info(f"[Voice] User {sender_id} joined. Existing peers: {peer_count}")
                
                # 1. 기존 참여자들에게 새 참여자의 join 알림
                #    -> 기존 참여자들이 이 메시지를 받으면 새 참여자에게 Offer를 전송
                await voice_manager.broadcast(data, project_id, websocket)
                logger.info(f"[Voice] Broadcasted join to {peer_count} peers")
                
            elif msg_type == "offer":
                target_id = data.get("targetId")
                logger.info(f"[Voice] Forwarding offer: {sender_id} -> {target_id}")
                await voice_manager.broadcast(data, project_id, websocket)
                
            elif msg_type == "answer":
                target_id = data.get("targetId")
                logger.info(f"[Voice] Forwarding answer: {sender_id} -> {target_id}")
                await voice_manager.broadcast(data, project_id, websocket)
                
            elif msg_type == "ice":
                target_id = data.get("targetId")
                logger.info(f"[Voice] Forwarding ICE: {sender_id} -> {target_id}")
                await voice_manager.broadcast(data, project_id, websocket)
                
            else:
                # 기타 메시지
                logger.info(f"[Voice] Unknown message type: {msg_type}")
                await voice_manager.broadcast(data, project_id, websocket)
                
    except WebSocketDisconnect:
        logger.info(f"[Voice] WebSocket disconnected: user={user_id}, project={project_id}")
        
        # 연결 해제 처리
        voice_manager.disconnect(websocket, project_id)
        
        # 다른 참여자들에게 퇴장 알림 (senderId 포함!)
        if user_id is not None:
            await voice_manager.broadcast_all(
                {
                    "type": "user_left",
                    "senderId": user_id,
                },
                project_id
            )
            logger.info(f"[Voice] Broadcasted user_left for user {user_id}")
            
    except Exception as e:
        logger.error(f"[Voice] Error: {e}", exc_info=True)
        voice_manager.disconnect(websocket, project_id)
        
        if user_id is not None:
            await voice_manager.broadcast_all(
                {
                    "type": "user_left",
                    "senderId": user_id,
                },
                project_id
            )
