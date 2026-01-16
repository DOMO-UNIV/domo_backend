from fastapi import APIRouter, Depends, HTTPException, status, Response, Request
from sqlmodel import Session, select
from datetime import datetime, timedelta
import bcrypt

from app.database import get_db
from app.models.user import User
from app.models.session import UserSession
from app.schemas import UserCreate, UserLogin, UserResponse

router = APIRouter(tags=["Authentication"])

# --- 비밀번호 해싱 헬퍼 함수 ---
def hash_password(password: str) -> str:
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(password.encode('utf-8'), salt).decode('utf-8')

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return bcrypt.checkpw(plain_password.encode('utf-8'), hashed_password.encode('utf-8'))

# --- 1. 회원가입 API ---
@router.post("/signup", response_model=UserResponse)
def signup(user_data: UserCreate, db: Session = Depends(get_db)):
    # 이메일 중복 확인
    existing_user = db.exec(select(User).where(User.email == user_data.email)).first()
    if existing_user:
        raise HTTPException(status_code=400, detail="이미 가입된 이메일입니다.")

    # 전주대 이메일 자동 인증 체크 (@jj.ac.kr)
    is_jj = user_data.email.endswith("@jj.ac.kr")

    # DB에 유저 저장
    new_user = User(
        email=user_data.email,
        password_hash=hash_password(user_data.password),
        name=user_data.name,
        is_student_verified=is_jj
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return new_user

# --- 2. 로그인 API ---
@router.post("/login")
def login(response: Response, login_data: UserLogin, db: Session = Depends(get_db)):
    user = db.exec(select(User).where(User.email == login_data.email)).first()

    # 검증 실패 (유저가 없거나 비밀번호가 틀림)
    if not user or not verify_password(login_data.password, user.password_hash):
        raise HTTPException(status_code=401, detail="이메일 또는 비밀번호가 일치하지 않습니다.")

    # 세션 생성 (DB에 저장, 24시간 유효)
    expires = datetime.now() + timedelta(hours=24)
    session = UserSession(user_id=user.id, expires_at=expires)

    db.add(session)
    db.commit()
    db.refresh(session)

    # 브라우저에 쿠키 발급 (HttpOnly로 보안 강화)
    response.set_cookie(
        key="session_id",
        value=session.session_id,
        httponly=True,  # 자바스크립트에서 접근 불가 (XSS 방지)
        secure=False,   # 로컬 개발(http)이므로 False. (실배포 https에선 True 권장)
        samesite="lax",
        max_age=60 * 60 * 24 # 24시간
    )

    return {"message": "로그인 성공", "user": {"email": user.email, "name": user.name}}

# --- 3. 로그아웃 API ---
@router.post("/logout")
def logout(response: Response, request: Request, db: Session = Depends(get_db)):
    session_id = request.cookies.get("session_id")
    if session_id:
        # DB에서 세션 삭제 (서버 측 로그아웃)
        session = db.get(UserSession, session_id)
        if session:
            db.delete(session)
            db.commit()

    # 클라이언트 쿠키 삭제
    response.delete_cookie("session_id")
    return {"message": "로그아웃 되었습니다."}