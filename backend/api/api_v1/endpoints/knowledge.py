from fastapi import APIRouter, UploadFile, File, HTTPException, Depends, BackgroundTasks
from typing import List, Dict
import os
import shutil
import time
from datetime import datetime

from backend.models import User
from backend.auth import get_current_active_superuser

router = APIRouter()

DOCS_DIR = str((__import__("pathlib").Path(__file__).resolve().parents[3] / "rag" / "docs"))


def _build_knowledge_base_safe():
    from backend.rag.build_kb import build_knowledge_base

    build_knowledge_base()

def get_file_info(filename: str) -> Dict:
    file_path = os.path.join(DOCS_DIR, filename)
    stats = os.stat(file_path)
    return {
        "name": filename,
        "size": stats.st_size,
        "uploaded_at": datetime.fromtimestamp(stats.st_mtime).strftime("%Y-%m-%d %H:%M:%S")
    }

@router.get("/files", response_model=List[Dict])
async def list_knowledge_files(
    admin: User = Depends(get_current_active_superuser)
):
    """
    获取知识库文件列表 (PDFs)
    """
    if not os.path.exists(DOCS_DIR):
        return []
    
    files = [f for f in os.listdir(DOCS_DIR) if f.lower().endswith('.pdf')]
    return [get_file_info(f) for f in files]

@router.post("/upload")
async def upload_knowledge_file(
    file: UploadFile = File(...),
    admin: User = Depends(get_current_active_superuser)
):
    """
    上传新的 PDF 指南
    """
    if not file.filename.lower().endswith('.pdf'):
        raise HTTPException(400, "Only PDF files are supported.")
    
    if not os.path.exists(DOCS_DIR):
        os.makedirs(DOCS_DIR)
        
    file_path = os.path.join(DOCS_DIR, file.filename)
    
    try:
        content = await file.read()
        with open(file_path, "wb") as f:
            f.write(content)
        return {"status": "success", "message": f"File {file.filename} uploaded."}
    except Exception as e:
        raise HTTPException(500, f"Upload failed: {str(e)}")

@router.delete("/files/{filename}")
async def delete_knowledge_file(
    filename: str,
    admin: User = Depends(get_current_active_superuser)
):
    """
    删除指定的知识库文件
    """
    file_path = os.path.join(DOCS_DIR, filename)
    if not os.path.exists(file_path):
        raise HTTPException(404, "File not found.")
    
    try:
        os.remove(file_path)
        return {"status": "success", "message": f"File {filename} deleted."}
    except Exception as e:
        raise HTTPException(500, f"Delete failed: {str(e)}")

@router.post("/rebuild")
async def rebuild_knowledge_base_endpoint(
    background_tasks: BackgroundTasks,
    admin: User = Depends(get_current_active_superuser)
):
    """
    触发后台任务：重建 RAG 知识库索引
    """
    background_tasks.add_task(_build_knowledge_base_safe)
    return {"status": "queued", "message": "Knowledge base rebuild task started in background."}
