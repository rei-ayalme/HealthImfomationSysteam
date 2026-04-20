"""
DeepAnalyze API 服务器文件管理 API
处理文件上传、下载和管理端点
"""

import os
from typing import Optional

from fastapi import APIRouter, File, UploadFile, Form, HTTPException, Query, Response
from fastapi.responses import JSONResponse

from config import VALID_FILE_PURPOSES, FILE_STORAGE_DIR
from models import FileObject, FileDeleteResponse
from storage import storage


# 创建文件端点路由
router = APIRouter(prefix="/v1/files", tags=["files"])


@router.post("", response_model=FileObject)
async def create_file(
    file: UploadFile = File(...),
    purpose: str = Form("file-extract")
):
    """上传文件（OpenAI 兼容）"""
    # 验证用途
    if purpose not in VALID_FILE_PURPOSES:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid purpose. Must be one of {VALID_FILE_PURPOSES}"
        )

    # 保存文件到持久化位置
    os.makedirs(FILE_STORAGE_DIR, exist_ok=True)
    file_id = f"file-{file.filename.replace('.', '-').replace('_', '-')[:8]}-{os.urandom(4).hex()}"
    file_path = os.path.join(FILE_STORAGE_DIR, file_id)

    try:
        with open(file_path, "wb") as f:
            f.write(await file.read())



        file_obj = storage.create_file(file.filename, file_path, purpose)
        return file_obj
    except Exception as e:
        # 若创建失败则清理文件
        if os.path.exists(file_path):
            os.remove(file_path)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("", response_model=dict)
async def list_files(purpose: Optional[str] = Query(None)):
    """列出文件（OpenAI 兼容）"""
    files = storage.list_files(purpose=purpose)
    return {"object": "list", "data": [f.dict() for f in files]}


@router.get("/{file_id}", response_model=FileObject)
async def retrieve_file(file_id: str):
    """获取文件元数据（OpenAI 兼容）"""
    file_obj = storage.get_file(file_id)
    if not file_obj:
        raise HTTPException(status_code=404, detail="File not found")
    return file_obj


@router.delete("/{file_id}", response_model=FileDeleteResponse)
async def delete_file(file_id: str):
    """删除文件（OpenAI 兼容）"""
    success = storage.delete_file(file_id)
    if not success:
        raise HTTPException(status_code=404, detail="File not found")
    return FileDeleteResponse(id=file_id, object="file", deleted=True)


@router.get("/{file_id}/content")
async def download_file(file_id: str):
    """下载文件内容（OpenAI 兼容）"""
    file_obj = storage.get_file(file_id)
    if not file_obj:
        raise HTTPException(status_code=404, detail="File not found")

    filepath = storage.files[file_id].get("filepath")
    if not filepath or not os.path.exists(filepath):
        raise HTTPException(status_code=404, detail="File content not found")

    with open(filepath, "rb") as f:
        content = f.read()

    return Response(content=content, media_type="application/octet-stream")