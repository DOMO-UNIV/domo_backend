from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select
from typing import List

from app.database import get_db
from app.models.user import User
from app.models.session import UserSession
from app.models.workspace import Workspace, WorkspaceMember, Project
from app.schemas import WorkspaceCreate, WorkspaceResponse, ProjectCreate, ProjectResponse, AddMemberRequest, \
    WorkspaceMemberResponse
from datetime import datetime
from typing import Any

router = APIRouter(tags=["Workspace & Project"])

# 쿠키에서 세션 ID를 추출하여 유저 ID 반환하는 의존성 함수
from fastapi import Cookie
def get_current_user_id(session_id: str = Cookie(None), db: Session = Depends(get_db)):
    if not session_id:
        raise HTTPException(status_code=401, detail="로그인이 필요합니다.")

    session = db.get(UserSession, session_id)
    if not session or session.expires_at < datetime.now():
        raise HTTPException(status_code=401, detail="세션이 만료되었습니다.")

    return session.user_id


# 1. 워크스페이스 생성 (팀 만들기)
@router.post("/workspaces", response_model=WorkspaceResponse)
def create_workspace(
        ws_data: WorkspaceCreate,
        user_id: int = Depends(get_current_user_id),
        db: Session = Depends(get_db)
):
    # 워크스페이스 생성
    new_ws = Workspace(
        name=ws_data.name,
        description=ws_data.description,
        owner_id=user_id
    )
    db.add(new_ws)
    db.commit()
    db.refresh(new_ws)

    # 생성자를 멤버(Admin)로 추가
    member = WorkspaceMember(workspace_id=new_ws.id, user_id=user_id, role="admin")
    db.add(member)
    db.commit()

    return new_ws

# 2. 내 워크스페이스 목록 조회
@router.get("/workspaces", response_model=List[WorkspaceResponse])
def get_my_workspaces(
        user_id: int = Depends(get_current_user_id),
        db: Session = Depends(get_db)
):
    # 내가 멤버로 속한 워크스페이스 찾기 (Join 쿼리)
    statement = (
        select(Workspace)
        .join(WorkspaceMember)
        .where(WorkspaceMember.user_id == user_id)
    )
    results = db.exec(statement).all()
    return results

# 3. 프로젝트 생성 (워크스페이스 안에)
@router.post("/workspaces/{workspace_id}/projects", response_model=ProjectResponse)
def create_project(
        workspace_id: int,
        project_data: ProjectCreate,
        user_id: int = Depends(get_current_user_id),
        db: Session = Depends(get_db)
):
    # 권한 확인: 내가 이 워크스페이스 멤버인가?
    member = db.get(WorkspaceMember, (workspace_id, user_id))
    if not member:
        raise HTTPException(status_code=403, detail="워크스페이스 멤버가 아닙니다.")

    new_project = Project(
        name=project_data.name,
        description=project_data.description,
        workspace_id=workspace_id
    )
    db.add(new_project)
    db.commit()
    db.refresh(new_project)

    return new_project

@router.get("/workspaces/{workspace_id}/projects", response_model=List[ProjectResponse])
def get_workspace_projects(
        workspace_id: int,
        user_id: int = Depends(get_current_user_id),
        db: Session = Depends(get_db)
):
    # 1. 권한 확인: 내가 이 워크스페이스의 멤버인지 확인 (보안 필수!)
    member = db.get(WorkspaceMember, (workspace_id, user_id))
    if not member:
        raise HTTPException(status_code=403, detail="워크스페이스 멤버가 아니거나 존재하지 않는 워크스페이스입니다.")

    # 2. 해당 워크스페이스의 프로젝트들만 조회
    projects = db.exec(select(Project).where(Project.workspace_id == workspace_id)).all()
    return projects

# app/routers/workspace.py 맨 아래에 추가

# 5. 워크스페이스에 팀원 초대 (이메일로 추가)
@router.post("/workspaces/{workspace_id}/members")
def add_workspace_member(
        workspace_id: int,
        request: AddMemberRequest,
        user_id: int = Depends(get_current_user_id),
        db: Session = Depends(get_db)
):
    # 1. 권한 확인: 초대하는 사람(나)이 해당 워크스페이스의 admin인지 확인
    my_membership = db.get(WorkspaceMember, (workspace_id, user_id))
    if not my_membership or my_membership.role != "admin":
        raise HTTPException(status_code=403, detail="팀원 초대 권한이 없습니다 (관리자 전용).")

    # 2. 초대할 유저가 존재하는지 확인
    target_user = db.exec(select(User).where(User.email == request.email)).first()
    if not target_user:
        raise HTTPException(status_code=404, detail="해당 이메일을 가진 사용자가 존재하지 않습니다.")

    # 3. 이미 멤버인지 확인
    existing_member = db.get(WorkspaceMember, (workspace_id, target_user.id))
    if existing_member:
        raise HTTPException(status_code=400, detail="이미 워크스페이스의 멤버입니다.")

    # 4. 멤버 추가 (기본 역할은 'member')
    new_member = WorkspaceMember(
        workspace_id=workspace_id,
        user_id=target_user.id,
        role="member"
    )
    db.add(new_member)
    db.commit()

    return {"message": f"{target_user.name} 님이 팀원으로 추가되었습니다."}


# app/routers/workspace.py 맨 아래에 추가

# 6. 워크스페이스 전체 멤버 목록 조회
@router.get("/workspaces/{workspace_id}/members", response_model=List[WorkspaceMemberResponse])
def get_workspace_members(
        workspace_id: int,
        user_id: int = Depends(get_current_user_id),
        db: Session = Depends(get_db)
) -> Any:
    # 1. 권한 확인: 요청한 사람이 이 워크스페이스의 멤버인지 확인
    membership = db.get(WorkspaceMember, (workspace_id, user_id))
    if not membership:
        raise HTTPException(status_code=403, detail="워크스페이스 멤버만 조회 가능합니다.")

    # 2. User 테이블과 WorkspaceMember 테이블을 Join하여 정보 조회
    # SQLModel의 select 문법으로 유저 정보와 역할을 동시에 가져옵니다.
    statement = (
        select(User.id.label("user_id"), User.name, User.email, WorkspaceMember.role)
        .join(WorkspaceMember, User.id == WorkspaceMember.user_id)
        .where(WorkspaceMember.workspace_id == workspace_id)
    )

    results = db.exec(statement).all()

    # 결과를 스키마 형태에 맞게 변환하여 반환
    return [
        WorkspaceMemberResponse(
            user_id=r.user_id,
            name=r.name,
            email=r.email,
            role=r.role
        ) for r in results
    ]