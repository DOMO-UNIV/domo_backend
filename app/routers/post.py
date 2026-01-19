from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select
from typing import List
from vectorwave import vectorize

from app.database import get_db
from app.routers.workspace import get_current_user_id
from app.models.post import Post, PostComment
from app.models.user import User
from app.schemas import PostCreate, PostUpdate, PostResponse, PostCommentCreate, PostCommentResponse

router = APIRouter(tags=["Project Board"])

# 1. 게시글 목록 조회
@router.get("/projects/{project_id}/posts", response_model=List[PostResponse])
def get_project_posts(project_id: int, db: Session = Depends(get_db)):
    posts = db.exec(
        select(Post).where(Post.project_id == project_id).order_by(Post.created_at.desc())
    ).all()
    return posts

# 2. 게시글 작성
@router.post("/projects/{project_id}/posts", response_model=PostResponse)
@vectorize(search_description="Create board post", capture_return_value=True)
def create_post(
        project_id: int,
        post_data: PostCreate,
        user_id: int = Depends(get_current_user_id),
        db: Session = Depends(get_db)
):
    new_post = Post(project_id=project_id, user_id=user_id, **post_data.model_dump())
    db.add(new_post)
    db.commit()
    db.refresh(new_post)
    return new_post

# 3. 게시글 상세 조회
@router.get("/posts/{post_id}", response_model=PostResponse)
def get_post(post_id: int, db: Session = Depends(get_db)):
    post = db.get(Post, post_id)
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")
    return post

# 4. 게시글 삭제
@router.delete("/posts/{post_id}")
def delete_post(post_id: int, user_id: int = Depends(get_current_user_id), db: Session = Depends(get_db)):
    post = db.get(Post, post_id)
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")
    if post.user_id != user_id:
        raise HTTPException(status_code=403, detail="작성자만 삭제할 수 있습니다.")
    db.delete(post)
    db.commit()
    return {"message": "게시글이 삭제되었습니다."}

# 5. 댓글 작성
@router.post("/posts/{post_id}/comments", response_model=PostCommentResponse)
def create_post_comment(
        post_id: int,
        comment_data: PostCommentCreate,
        user_id: int = Depends(get_current_user_id),
        db: Session = Depends(get_db)
):
    comment = PostComment(post_id=post_id, user_id=user_id, content=comment_data.content)
    db.add(comment)
    db.commit()
    db.refresh(comment)
    return comment