# app/routers/file.py

import os
import uuid
import shutil
from typing import List
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, BackgroundTasks
from fastapi.encoders import jsonable_encoder
from fastapi.responses import FileResponse  # 👈 파일 전송용
from sqlmodel import Session, select, desc

from app.database import get_db
from app.routers.workspace import get_current_user_id
from app.models.file import FileMetadata, FileVersion
from app.models.workspace import Project
from app.models.user import User
from app.schemas import FileResponse as FileSchema, FileVersionResponse
from app.utils.logger import log_activity
from app.utils.connection_manager import board_event_manager
from vectorwave import vectorize

router = APIRouter(tags=["Files"])

UPLOAD_DIR = "/app/uploads/files"
os.makedirs(UPLOAD_DIR, exist_ok=True)

# =================================================================
# 📥 1. 파일 다운로드 (특정 버전) - [복구됨]
# =================================================================
@router.get("/files/download/{version_id}")
@vectorize(search_description="Download file version", capture_return_value=False)
def download_file_version(version_id: int, db: Session = Depends(get_db)):
    # 1. 버전 정보 조회
    version = db.get(FileVersion, version_id)
    if not version:
        raise HTTPException(status_code=404, detail="파일 버전을 찾을 수 없습니다.")

    # 2. 메타데이터 조회 (파일명 확인용)
    file_meta = db.get(FileMetadata, version.file_id)
    if not file_meta:
        raise HTTPException(status_code=404, detail="파일 정보를 찾을 수 없습니다.")

    # 3. 실제 파일 존재 여부 확인
    if not os.path.exists(version.saved_path):
        raise HTTPException(status_code=404, detail="서버에 실제 파일이 존재하지 않습니다.")

    # 4. 다운로드 제공 (파일명: v1_원래이름.ext)
    return FileResponse(
        path=version.saved_path,
        filename=f"v{version.version}_{file_meta.filename}",
        media_type="application/octet-stream"
    )

# =================================================================
# 📜 2. 파일 히스토리 조회 - [복구됨]
# =================================================================
@router.get("/files/{file_id}/versions", response_model=List[FileVersionResponse])
@vectorize(search_description="Get file version history", capture_return_value=True)
def get_file_history(
        file_id: int,
        db: Session = Depends(get_db)
):
    # 1. 파일 존재 확인
    file_meta = db.get(FileMetadata, file_id)
    if not file_meta:
        raise HTTPException(status_code=404, detail="파일을 찾을 수 없습니다.")

    # 2. 버전 목록 조회 (최신순)
    versions = db.exec(
        select(FileVersion)
        .where(FileVersion.file_id == file_id)
        .order_by(desc(FileVersion.version))
    ).all()

    return versions

# =================================================================
# 📤 3. 파일 업로드 API (단건 & 배치)
# =================================================================

@router.post("/projects/{project_id}/files", response_model=FileSchema)
@vectorize(search_description="Upload file to project", capture_return_value=True, replay=True)
async def upload_file(
        project_id: int,
        file: UploadFile = File(...),
        user_id: int = Depends(get_current_user_id),
        db: Session = Depends(get_db)
):
    project = db.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    user = db.get(User, user_id)

    file_ext = os.path.splitext(file.filename)[1]
    saved_filename = f"{uuid.uuid4()}{file_ext}"
    saved_path = os.path.join(UPLOAD_DIR, saved_filename)

    with open(saved_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    file_size = os.path.getsize(saved_path)

    existing_file = db.exec(
        select(FileMetadata)
        .where(FileMetadata.project_id == project_id)
        .where(FileMetadata.filename == file.filename)
    ).first()

    current_version_num = 1
    target_file_id = None

    if existing_file:
        last_version = db.exec(
            select(FileVersion)
            .where(FileVersion.file_id == existing_file.id)
            .order_by(desc(FileVersion.version))
        ).first()

        if last_version:
            current_version_num = last_version.version + 1

        target_file_id = existing_file.id
        existing_file.updated_at = datetime.now()
        db.add(existing_file)
    else:
        new_file = FileMetadata(
            project_id=project_id,
            filename=file.filename,
            owner_id=user_id
        )
        db.add(new_file)
        db.commit()
        db.refresh(new_file)
        target_file_id = new_file.id
        existing_file = new_file

    new_version = FileVersion(
        file_id=target_file_id,
        version=current_version_num,
        saved_path=saved_path,
        file_size=file_size,
        uploader_id=user_id
    )
    db.add(new_version)
    db.commit()
    db.refresh(new_version)

    response_data = FileSchema(
        id=existing_file.id,
        project_id=existing_file.project_id,
        filename=existing_file.filename,
        owner_id=existing_file.owner_id,
        created_at=existing_file.created_at,
        latest_version=FileVersionResponse(
            id=new_version.id,
            version=new_version.version,
            file_size=new_version.file_size,
            created_at=new_version.created_at,
            uploader_id=new_version.uploader_id
        )
    )

    action_msg = "업로드" if current_version_num == 1 else f"새 버전(v{current_version_num}) 업데이트"
    log_activity(
        db=db, user_id=user_id, workspace_id=project.workspace_id, action_type="UPLOAD",
        content=f"💾 '{user.name}'님이 파일 '{file.filename}'을(를) {action_msg}했습니다."
    )

    # 🔥 [SSE] SSE 알림 (jsonable_encoder 사용)
    await board_event_manager.broadcast(project_id, {
        "type": "FILE_UPLOADED",
        "user_id": user_id,
        "data": jsonable_encoder(response_data)
    })

    return response_data

@router.post("/projects/{project_id}/files/batch", response_model=List[FileSchema])
@vectorize(search_description="Batch upload files", capture_return_value=True)
async def upload_files_batch(
        project_id: int,
        files: List[UploadFile] = File(...),
        user_id: int = Depends(get_current_user_id),
        db: Session = Depends(get_db)
):
    project = db.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    user = db.get(User, user_id)
    results = []

    for file in files:
        file_ext = os.path.splitext(file.filename)[1]
        saved_filename = f"{uuid.uuid4()}{file_ext}"
        saved_path = os.path.join(UPLOAD_DIR, saved_filename)

        with open(saved_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        file_size = os.path.getsize(saved_path)

        existing_file = db.exec(
            select(FileMetadata)
            .where(FileMetadata.project_id == project_id)
            .where(FileMetadata.filename == file.filename)
        ).first()

        current_version_num = 1
        target_file_id = None

        if existing_file:
            last_version = db.exec(
                select(FileVersion)
                .where(FileVersion.file_id == existing_file.id)
                .order_by(desc(FileVersion.version))
            ).first()
            if last_version:
                current_version_num = last_version.version + 1
            target_file_id = existing_file.id
            existing_file.updated_at = datetime.now()
            db.add(existing_file)
        else:
            new_file = FileMetadata(
                project_id=project_id,
                filename=file.filename,
                owner_id=user_id
            )
            db.add(new_file)
            db.commit()
            db.refresh(new_file)
            target_file_id = new_file.id
            existing_file = new_file

        new_version = FileVersion(
            file_id=target_file_id,
            version=current_version_num,
            saved_path=saved_path,
            file_size=file_size,
            uploader_id=user_id
        )
        db.add(new_version)
        db.commit()
        db.refresh(new_version)

        results.append(FileSchema(
            id=existing_file.id,
            project_id=existing_file.project_id,
            filename=existing_file.filename,
            owner_id=existing_file.owner_id,
            created_at=existing_file.created_at,
            latest_version=FileVersionResponse(
                id=new_version.id,
                version=new_version.version,
                file_size=new_version.file_size,
                created_at=new_version.created_at,
                uploader_id=new_version.uploader_id
            )
        ))

        try:
            action_msg = "업로드" if current_version_num == 1 else f"새 버전(v{current_version_num}) 업데이트"
            log_activity(
                db=db,
                user_id=user_id,
                workspace_id=project.workspace_id,
                action_type="UPLOAD",
                content=f"💾 '{user.name}'님이 파일 '{file.filename}'을(를) {action_msg}했습니다."
            )
        except Exception:
            pass

    # 🔥 [SSE] 배치 알림 (jsonable_encoder 사용)
    if results:
        await board_event_manager.broadcast(project_id, {
            "type": "FILES_BATCH_UPLOADED",
            "user_id": user_id,
            "data": jsonable_encoder(results)
        })

    return results


@router.get("/projects/{project_id}/files", response_model=List[FileSchema])
@vectorize(search_description="List project files", capture_return_value=True)
def get_project_files(
        project_id: int,
        db: Session = Depends(get_db)
):
    files = db.exec(select(FileMetadata).where(FileMetadata.project_id == project_id)).all()

    results = []
    for f in files:
        latest_v = db.exec(
            select(FileVersion)
            .where(FileVersion.file_id == f.id)
            .order_by(desc(FileVersion.version))
        ).first()

        if latest_v:
            results.append(FileSchema(
                id=f.id,
                project_id=f.project_id,
                filename=f.filename,
                owner_id=f.owner_id,
                created_at=f.created_at,
                latest_version=FileVersionResponse(
                    id=latest_v.id,
                    version=latest_v.version,
                    file_size=latest_v.file_size,
                    created_at=latest_v.created_at,
                    uploader_id=latest_v.uploader_id
                )
            ))

    return results

@router.delete("/files/{file_id}")
@vectorize(search_description="Delete file", capture_return_value=True)
async def delete_file(
        file_id: int,
        user_id: int = Depends(get_current_user_id),
        db: Session = Depends(get_db)
):
    file_meta = db.get(FileMetadata, file_id)
    if not file_meta:
        raise HTTPException(status_code=404, detail="File not found")

    project = db.get(Project, file_meta.project_id)
    filename = file_meta.filename
    project_id = file_meta.project_id

    # 1. 버전 정보(자식) 먼저 삭제
    versions = db.exec(select(FileVersion).where(FileVersion.file_id == file_id)).all()
    for v in versions:
        if os.path.exists(v.saved_path):
            try:
                os.remove(v.saved_path)
            except OSError:
                pass
        db.delete(v)

    # 2. 메타데이터(부모) 삭제
    db.delete(file_meta)
    db.commit()

    if project:
        user = db.get(User, user_id)
        log_activity(
            db=db, user_id=user_id, workspace_id=project.workspace_id, action_type="DELETE",
            content=f"🗑️ '{user.name}'님이 파일 '{filename}'을(를) 삭제했습니다."
        )

    # 🔥 [SSE] 삭제 알림
    await board_event_manager.broadcast(project_id, {
        "type": "FILE_DELETED",
        "user_id": user_id,
        "data": {"id": file_id}
    })

    return {"message": "파일이 삭제되었습니다."}