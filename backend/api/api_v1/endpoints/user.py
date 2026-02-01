# User Data Endpoints (Task 57)
from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select, col
from backend.database import get_session
from backend.auth import get_current_user
from backend.models import User, MedicalDocument
import json
import os

router = APIRouter()

@router.get("/documents")
async def get_user_documents(
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """
    获取当前用户上传的所有体检文档列表 (Task 57)
    """
    statement = select(MedicalDocument).where(
        MedicalDocument.user_id == current_user.id
    ).order_by(col(MedicalDocument.upload_date).desc())
    
    docs = session.exec(statement).all()
    
    result = []
    for doc in docs:
        # Parse ocr_summary if exists
        ocr_data = None
        if doc.ocr_summary:
            try:
                ocr_data = json.loads(doc.ocr_summary)
            except:
                ocr_data = None
        
        result.append({
            "id": doc.id,
            "file_name": doc.file_name,
            "file_url": doc.file_url,
            "upload_date": doc.upload_date.strftime("%Y-%m-%d %H:%M"),
            "ocr_summary": ocr_data,
            "has_data": ocr_data is not None and len(ocr_data) > 0
        })
    
    return {"status": "success", "documents": result, "total": len(result)}


@router.delete("/documents/{doc_id}")
async def delete_user_document(
    doc_id: int,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """
    删除指定的体检文档 (Task 69)
    - 验证文档归属
    - 删除物理文件
    - 删除数据库记录
    """
    # 1. Query document
    statement = select(MedicalDocument).where(
        MedicalDocument.id == doc_id
    )
    doc = session.exec(statement).first()
    
    # 2. Check existence
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    
    # 3. Check ownership
    if doc.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to delete this document")
    
    # 4. Delete physical file
    file_deleted = False
    if doc.file_path and os.path.exists(doc.file_path):
        try:
            os.remove(doc.file_path)
            file_deleted = True
            print(f"🗑️ Deleted file: {doc.file_path}")
        except Exception as e:
            print(f"⚠️ Failed to delete file {doc.file_path}: {e}")
    
    # 5. Delete database record
    session.delete(doc)
    session.commit()
    
    return {
        "status": "success",
        "message": f"Document {doc_id} deleted successfully",
        "file_deleted": file_deleted
    }

