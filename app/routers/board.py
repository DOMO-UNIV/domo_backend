from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select
from typing import List
from app.database import get_db
from app.routers.workspace import get_current_user_id # 기존 인증 함수 재사용
from app.models.board import BoardColumn, Card
from app.models.workspace import Project, WorkspaceMember
from app.schemas import BoardColumnCreate, BoardColumnResponse, CardCreate, CardResponse, CardUpdate

router = APIRouter(tags=["Board & Cards"])

# 1. 컬럼 생성
@router.post("/projects/{project_id}/columns", response_model=BoardColumnResponse)
def create_column(project_id: int, col_data: BoardColumnCreate, user_id: int = Depends(get_current_user_id), db: Session = Depends(get_db)):
    project = db.get(Project, project_id)
    if not project: raise HTTPException(status_code=404, detail="프로젝트를 찾을 수 없습니다.")

    # 워크스페이스 멤버 권한 확인 로직 생략(필요 시 추가)

    new_col = BoardColumn(**col_data.model_dump(), project_id=project_id)
    db.add(new_col)
    db.commit()
    db.refresh(new_col)
    return new_col

# 2. 카드 생성
@router.post("/columns/{column_id}/cards", response_model=CardResponse)
def create_card(column_id: int, card_data: CardCreate, user_id: int = Depends(get_current_user_id), db: Session = Depends(get_db)):
    column = db.get(BoardColumn, column_id)
    if not column: raise HTTPException(status_code=404, detail="컬럼을 찾을 수 없습니다.")

    new_card = Card(**card_data.model_dump(), column_id=column_id)
    db.add(new_card)
    db.commit()
    db.refresh(new_card)
    return new_card

# 3. 특정 프로젝트의 모든 컬럼 및 카드 조회
@router.get("/projects/{project_id}/board")
def get_board(project_id: int, db: Session = Depends(get_db)):
    columns = db.exec(select(BoardColumn).where(BoardColumn.project_id == project_id).order_by(BoardColumn.order)).all()
    result = []
    for col in columns:
        cards = db.exec(select(Card).where(Card.column_id == col.id).order_by(Card.order)).all()
        result.append({
            "column": col,
            "cards": cards
        })
    return result

# 4. 카드 수정 및 이동 (핵심: column_id를 바꾸면 이동됨)
@router.patch("/cards/{card_id}", response_model=CardResponse)
def update_card(card_id: int, update_data: CardUpdate, db: Session = Depends(get_db)):
    card = db.get(Card, card_id)
    if not card: raise HTTPException(status_code=404, detail="카드를 찾을 수 없습니다.")

    data = update_data.model_dump(exclude_unset=True)
    for key, value in data.items():
        setattr(card, key, value)

    db.add(card)
    db.commit()
    db.refresh(card)
    return card