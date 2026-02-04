"""
User Data Endpoints
===================

提供用户数据管理相关的 API 端点，包括：
- 体检文档管理 (Task 57, 69)
- 亲情账户关联体系 (Task 132)

Author: Health AI Platform Team
"""
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
            except (json.JSONDecodeError, TypeError) as e:
                print(f"⚠️ OCR 数据解析失败 (doc_id={doc.id}): {e}")
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


# ============================================
# Task 132: 亲情账户关联体系 (Family Account Linking)
# ============================================
from backend.models import FamilyLink, FamilyInvite
from pydantic import BaseModel
import secrets
from datetime import timedelta

class FamilyBindRequest(BaseModel):
    """绑定家人请求"""
    invite_code: str  # 邀请码
    relation_name: str = "家人"  # 关系名称


class FamilyMemberResponse(BaseModel):
    """家人信息响应"""
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
    生成当前用户的邀请码 (供家人扫描/输入)
    """
    # 检查是否已有邀请码
    existing = session.exec(
        select(FamilyInvite).where(FamilyInvite.user_id == current_user.id)
    ).first()
    
    if existing:
        return {
            "status": "success",
            "invite_code": existing.invite_code,
            "message": "返回已有邀请码"
        }
    
    # 生成6位大写字母数字邀请码
    invite_code = secrets.token_hex(3).upper()  # 例如: A1B2C3
    
    invite = FamilyInvite(
        user_id=current_user.id,
        invite_code=invite_code
    )
    session.add(invite)
    session.commit()
    
    return {
        "status": "success",
        "invite_code": invite_code,
        "message": "邀请码生成成功，请分享给家人"
    }


@router.post("/family/bind")
async def bind_family_member(
    request: FamilyBindRequest,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """
    通过邀请码绑定家人账户
    - 当前用户成为管理者 (manager)
    - 邀请码所属用户成为被管理者 (member)
    """
    # 1. 验证邀请码
    invite = session.exec(
        select(FamilyInvite).where(FamilyInvite.invite_code == request.invite_code.upper())
    ).first()
    
    if not invite:
        raise HTTPException(status_code=404, detail="邀请码无效或已过期")
    
    # 2. 不能绑定自己
    if invite.user_id == current_user.id:
        raise HTTPException(status_code=400, detail="不能绑定自己的账户")
    
    # 3. 检查是否已绑定
    existing_link = session.exec(
        select(FamilyLink).where(
            FamilyLink.manager_id == current_user.id,
            FamilyLink.member_id == invite.user_id,
            FamilyLink.is_active == True
        )
    ).first()
    
    if existing_link:
        raise HTTPException(status_code=400, detail="该家人账户已绑定")
    
    # 4. 获取被绑定用户信息
    member_user = session.exec(select(User).where(User.id == invite.user_id)).first()
    if not member_user:
        raise HTTPException(status_code=404, detail="用户不存在")
    
    # 5. 创建关联
    link = FamilyLink(
        manager_id=current_user.id,
        member_id=invite.user_id,
        relation_name=request.relation_name
    )
    session.add(link)
    session.commit()
    
    return {
        "status": "success",
        "message": f"成功绑定家人: {request.relation_name}",
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
    获取当前用户管理的所有家人列表
    """
    # 查询所有激活的关联
    links = session.exec(
        select(FamilyLink).where(
            FamilyLink.manager_id == current_user.id,
            FamilyLink.is_active == True
        )
    ).all()
    
    members = []
    for link in links:
        # 获取家人用户信息
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
    切换到家人账户视图 (获取临时访问 Token)
    - 验证当前用户是否有权管理该家人
    - 返回该家人的临时访问凭证
    """
    from backend.auth import create_access_token
    
    # 1. 验证关联关系
    link = session.exec(
        select(FamilyLink).where(
            FamilyLink.manager_id == current_user.id,
            FamilyLink.member_id == member_id,
            FamilyLink.is_active == True
        )
    ).first()
    
    if not link:
        raise HTTPException(status_code=403, detail="无权访问该家人账户")
    
    # 2. 获取家人用户信息
    member_user = session.exec(select(User).where(User.id == member_id)).first()
    if not member_user:
        raise HTTPException(status_code=404, detail="用户不存在")
    
    # 3. 生成临时 Token (有效期2小时)
    # 注意: 这里生成的是真实的访问 Token，前端可以用它访问该家人的数据
    access_token = create_access_token(
        data={"sub": member_user.username, "acting_as": current_user.id},
        expires_delta=timedelta(hours=2)
    )
    
    return {
        "status": "success",
        "message": f"已切换到 {link.relation_name} 的账户",
        "access_token": access_token,
        "token_type": "bearer",
        "member": {
            "id": member_user.id,
            "username": member_user.username,
            "relation_name": link.relation_name
        },
        "expires_in": 7200  # 秒
    }


@router.delete("/family/unbind/{link_id}")
async def unbind_family_member(
    link_id: int,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """
    解除家人绑定
    """
    link = session.exec(
        select(FamilyLink).where(
            FamilyLink.id == link_id,
            FamilyLink.manager_id == current_user.id
        )
    ).first()
    
    if not link:
        raise HTTPException(status_code=404, detail="关联不存在或无权操作")
    
    # 软删除
    link.is_active = False
    session.add(link)
    session.commit()
    
    return {
        "status": "success",
        "message": "已解除家人绑定"
    }
