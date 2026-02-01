from datetime import datetime, timedelta
from typing import Optional
from jose import JWTError, jwt
from jose import JWTError, jwt
# from passlib.context import CryptContext (Removed)
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlmodel import Session, select
from backend.database import get_session
from backend.models import User

# Configuration
SECRET_KEY = "PLEASE_CHANGE_THIS_TO_A_SUPER_SECRET_KEY_IN_PRODUCTION"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 3000 # Long expiry for demo

import bcrypt

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/token")

def verify_password(plain_password, hashed_password):
    # Ensure bytes for bcrypt
    if isinstance(plain_password, str):
        plain_password = plain_password.encode('utf-8')
    if isinstance(hashed_password, str):
        hashed_password = hashed_password.encode('utf-8')
    return bcrypt.checkpw(plain_password, hashed_password)

def authenticate_user(session: Session, username: str, password: str):
    print(f"👉 正在尝试登录用户: {username}")
    
    statement = select(User).where(User.username == username)
    user = session.exec(statement).first()
    
    print(f"🔎 数据库查询结果: {user}")
    
    if not user:
        return False
        
    print(f"🔐 数据库中的哈希: {user.hashed_password}")
    
    is_valid = verify_password(password, user.hashed_password)
    print(f"⚖️ 密码比对结果: {is_valid}")
    
    if not is_valid:
        return False
        
    return user

def get_password_hash(password):
    # Ensure bytes
    if isinstance(password, str):
        password = password.encode('utf-8')
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(password, salt).decode('utf-8')

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

async def get_current_user(token: str = Depends(oauth2_scheme), session: Session = Depends(get_session)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
    
    # Use SQLModel select
    statement = select(User).where(User.username == username)
    results = session.exec(statement)
    user = results.first()
    
    if user is None:
        raise credentials_exception
    return user

async def get_current_active_superuser(current_user: User = Depends(get_current_user)) -> User:
    if not current_user.is_superuser:
        raise HTTPException(
            status_code=403, detail="Permission Denied: Admins only"
        )
    return current_user
