"""
User Data Endpoints
===================

鎻愪緵鐢ㄦ埛鏁版嵁绠＄悊鐩稿叧鐨?API 绔偣锛屽寘鎷細
- 浣撴鏂囨。绠＄悊 (Task 57, 69)
- 浜叉儏璐︽埛鍏宠仈浣撶郴 (Task 132)

Author: Health AI Platform Team
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select, col
from backend.database import get_session
from backend.auth import get_current_user
from backend.models import User, MedicalDocument
from backend.services.payload_normalization import normalize_ocr_processing_status_payload, normalize_ocr_summary_payload
import json
import logging
import os

router = APIRouter()
logger = logging.getLogger(__name__)

@router.get("/documents")
async def get_user_documents(
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """
    鑾峰彇褰撳墠鐢ㄦ埛涓婁紶鐨勬墍鏈変綋妫€鏂囨。鍒楄〃 (Task 57)
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
                ocr_data = normalize_ocr_summary_payload(doc.ocr_summary)
            except (json.JSONDecodeError, TypeError) as e:
                logger.warning("OCR data parse failed (doc_id=%s): %s", doc.id, e)
                ocr_data = None

        ocr_processing_status = normalize_ocr_processing_status_payload(
            doc.ocr_processing_status,
            default_status="success" if ocr_data else None,
            structured_data_present=ocr_data is not None and len(ocr_data) > 0,
            raw_text_present=ocr_data is not None,
            saved_at=doc.upload_date.isoformat() if doc.upload_date else None,
        )
        
        result.append({
            "id": doc.id,
            "file_name": doc.file_name,
            "file_url": doc.file_url,
            "upload_date": doc.upload_date.strftime("%Y-%m-%d %H:%M"),
            "ocr_summary": ocr_data,
            "has_data": ocr_data is not None and len(ocr_data) > 0,
            "ocr_processing_status": ocr_processing_status,
        })
    
    return {"status": "success", "documents": result, "total": len(result)}


@router.delete("/documents/{doc_id}")
async def delete_user_document(
    doc_id: int,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """
    鍒犻櫎鎸囧畾鐨勪綋妫€鏂囨。 (Task 69)
    - 楠岃瘉鏂囨。褰掑睘
    - 鍒犻櫎鐗╃悊鏂囦欢
    - 鍒犻櫎鏁版嵁搴撹褰?
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
            logger.info("Deleted file: %s", doc.file_path)
        except Exception as e:
            logger.warning("Failed to delete file %s: %s", doc.file_path, e)
    
    # 5. Delete database record
    session.delete(doc)
    session.commit()
    
    return {
        "status": "success",
        "message": f"Document {doc_id} deleted successfully",
        "file_deleted": file_deleted
    }


# ============================================
# Task 132: 浜叉儏璐︽埛鍏宠仈浣撶郴 (Family Account Linking)
# ============================================
from backend.models import FamilyLink, FamilyInvite
from pydantic import BaseModel
import secrets
from datetime import timedelta

class FamilyBindRequest(BaseModel):
    """缁戝畾瀹朵汉璇锋眰"""
    invite_code: str  # 閭€璇风爜
    relation_name: str = "瀹朵汉"  # 鍏崇郴鍚嶇О


class FamilyMemberResponse(BaseModel):
    """瀹朵汉淇℃伅鍝嶅簲"""
    id: int
    member_id: int
    username: str
    email: str | None
    relation_name: str
    created_at: str


@router.post("/family/invite")
async def generate_invite_code(
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """
    鐢熸垚褰撳墠鐢ㄦ埛鐨勯個璇风爜 (渚涘浜烘壂鎻?杈撳叆)
    """
    # 妫€鏌ユ槸鍚﹀凡鏈夐個璇风爜
    existing = session.exec(
        select(FamilyInvite).where(FamilyInvite.user_id == current_user.id)
    ).first()
    
    if existing:
        return {
            "status": "success",
            "invite_code": existing.invite_code,
            "message": "杩斿洖宸叉湁閭€璇风爜"
        }
    
    # 鐢熸垚6浣嶅ぇ鍐欏瓧姣嶆暟瀛楅個璇风爜
    invite_code = secrets.token_hex(3).upper()  # 渚嬪: A1B2C3
    
    invite = FamilyInvite(
        user_id=current_user.id,
        invite_code=invite_code
    )
    session.add(invite)
    session.commit()
    
    return {
        "status": "success",
        "invite_code": invite_code,
        "message": "Invite code created successfully; please share it with your family member."
    }


@router.post("/family/bind")
async def bind_family_member(
    request: FamilyBindRequest,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """
    閫氳繃閭€璇风爜缁戝畾瀹朵汉璐︽埛
    - 褰撳墠鐢ㄦ埛鎴愪负绠＄悊鑰?(manager)
    - 閭€璇风爜鎵€灞炵敤鎴锋垚涓鸿绠＄悊鑰?(member)
    """
    # 1. 楠岃瘉閭€璇风爜
    invite = session.exec(
        select(FamilyInvite).where(FamilyInvite.invite_code == request.invite_code.upper())
    ).first()
    
    if not invite:
        raise HTTPException(status_code=404, detail="閭€璇风爜鏃犳晥鎴栧凡杩囨湡")
    
    # 2. 涓嶈兘缁戝畾鑷繁
    if invite.user_id == current_user.id:
        raise HTTPException(status_code=400, detail="Cannot bind your own account")
    
    # 3. 妫€鏌ユ槸鍚﹀凡缁戝畾
    existing_link = session.exec(
        select(FamilyLink).where(
            FamilyLink.manager_id == current_user.id,
            FamilyLink.member_id == invite.user_id,
            FamilyLink.is_active == True
        )
    ).first()
    
    if existing_link:
        raise HTTPException(status_code=400, detail="璇ュ浜鸿处鎴峰凡缁戝畾")
    
    # 4. 鑾峰彇琚粦瀹氱敤鎴蜂俊鎭?
    member_user = session.exec(select(User).where(User.id == invite.user_id)).first()
    if not member_user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # 5. 鍒涘缓鍏宠仈
    link = FamilyLink(
        manager_id=current_user.id,
        member_id=invite.user_id,
        relation_name=request.relation_name
    )
    session.add(link)
    session.commit()
    
    return {
        "status": "success",
        "message": f"鎴愬姛缁戝畾瀹朵汉: {request.relation_name}",
        "member": {
            "id": member_user.id,
            "username": member_user.username,
            "relation_name": request.relation_name
        }
    }


@router.get("/family/members")
async def get_family_members(
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """
    鑾峰彇褰撳墠鐢ㄦ埛绠＄悊鐨勬墍鏈夊浜哄垪琛?
    """
    # 鏌ヨ鎵€鏈夋縺娲荤殑鍏宠仈
    links = session.exec(
        select(FamilyLink).where(
            FamilyLink.manager_id == current_user.id,
            FamilyLink.is_active == True
        )
    ).all()
    
    members = []
    for link in links:
        # 鑾峰彇瀹朵汉鐢ㄦ埛淇℃伅
        member_user = session.exec(select(User).where(User.id == link.member_id)).first()
        if member_user:
            members.append({
                "id": link.id,
                "member_id": member_user.id,
                "username": member_user.username,
                "email": member_user.email,
                "relation_name": link.relation_name,
                "created_at": link.created_at.strftime("%Y-%m-%d")
            })
    
    return {
        "status": "success",
        "members": members,
        "count": len(members)
    }


@router.post("/family/switch/{member_id}")
async def switch_to_family_member(
    member_id: int,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """
    鍒囨崲鍒板浜鸿处鎴疯鍥?(鑾峰彇涓存椂璁块棶 Token)
    - 楠岃瘉褰撳墠鐢ㄦ埛鏄惁鏈夋潈绠＄悊璇ュ浜?
    - 杩斿洖璇ュ浜虹殑涓存椂璁块棶鍑瘉
    """
    from backend.auth import create_access_token
    
    # 1. 楠岃瘉鍏宠仈鍏崇郴
    link = session.exec(
        select(FamilyLink).where(
            FamilyLink.manager_id == current_user.id,
            FamilyLink.member_id == member_id,
            FamilyLink.is_active == True
        )
    ).first()
    
    if not link:
        raise HTTPException(status_code=403, detail="Not authorized to access this family account")
    
    # 2. 鑾峰彇瀹朵汉鐢ㄦ埛淇℃伅
    member_user = session.exec(select(User).where(User.id == member_id)).first()
    if not member_user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # 3. 鐢熸垚涓存椂 Token (鏈夋晥鏈?灏忔椂)
    # 娉ㄦ剰: 杩欓噷鐢熸垚鐨勬槸鐪熷疄鐨勮闂?Token锛屽墠绔彲浠ョ敤瀹冭闂瀹朵汉鐨勬暟鎹?
    access_token = create_access_token(
        data={"sub": member_user.username, "acting_as": current_user.id},
        expires_delta=timedelta(hours=2)
    )
    
    return {
        "status": "success",
        "message": f"Switched to {link.relation_name} account",
        "access_token": access_token,
        "token_type": "bearer",
        "member": {
            "id": member_user.id,
            "username": member_user.username,
            "relation_name": link.relation_name
        },
        "expires_in": 7200  # 绉?
    }


@router.delete("/family/unbind/{link_id}")
async def unbind_family_member(
    link_id: int,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """
    瑙ｉ櫎瀹朵汉缁戝畾
    """
    link = session.exec(
        select(FamilyLink).where(
            FamilyLink.id == link_id,
            FamilyLink.manager_id == current_user.id
        )
    ).first()
    
    if not link:
        raise HTTPException(status_code=404, detail="鍏宠仈涓嶅瓨鍦ㄦ垨鏃犳潈鎿嶄綔")
    
    # 杞垹闄?
    link.is_active = False
    session.add(link)
    session.commit()
    
    return {
        "status": "success",
        "message": "Family link removed successfully"
    }
