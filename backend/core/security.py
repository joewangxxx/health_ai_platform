# ============================================
# Task 134: 敏感数据字段级加密工具
# AES-256-GCM 加密实现
# ============================================

from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
import base64
import os
from typing import Optional
from backend.core.config import settings


class FieldEncryption:
    """
    字段级加密工具类
    使用 AES-256-GCM 对敏感数据进行加密
    
    Features:
    - 基于 SECRET_KEY 派生加密密钥
    - 每次加密使用唯一的 Nonce (防止重放攻击)
    - 支持认证加密 (AEAD)，防止数据篡改
    """
    
    _key: bytes = None
    _salt: bytes = b"health_ai_encryption_salt_v1"  # 固定盐值用于密钥派生
    
    @classmethod
    def _get_key(cls) -> bytes:
        """
        从 SECRET_KEY 派生 256-bit 加密密钥
        使用 PBKDF2 密钥派生函数
        """
        if cls._key is None:
            secret = settings.SECRET_KEY.encode('utf-8')
            
            kdf = PBKDF2HMAC(
                algorithm=hashes.SHA256(),
                length=32,  # 256 bits for AES-256
                salt=cls._salt,
                iterations=100_000,  # OWASP 推荐的迭代次数
            )
            cls._key = kdf.derive(secret)
        
        return cls._key
    
    @classmethod
    def encrypt(cls, plaintext: str) -> str:
        """
        加密明文字符串
        
        Args:
            plaintext: 待加密的明文字符串
            
        Returns:
            str: Base64 编码的密文 (格式: nonce + ciphertext)
        """
        if not plaintext:
            return ""
        
        key = cls._get_key()
        aesgcm = AESGCM(key)
        
        # 生成随机 12-byte nonce (GCM 推荐长度)
        nonce = os.urandom(12)
        
        # 加密
        ciphertext = aesgcm.encrypt(nonce, plaintext.encode('utf-8'), None)
        
        # 拼接 nonce + ciphertext 并编码为 Base64
        encrypted = base64.b64encode(nonce + ciphertext).decode('utf-8')
        
        return encrypted
    
    @classmethod
    def decrypt(cls, encrypted: str) -> str:
        """
        解密密文字符串
        
        Args:
            encrypted: Base64 编码的密文
            
        Returns:
            str: 解密后的明文，解密失败返回空字符串
        """
        if not encrypted:
            return ""
        
        try:
            key = cls._get_key()
            aesgcm = AESGCM(key)
            
            # 解码 Base64
            data = base64.b64decode(encrypted.encode('utf-8'))
            
            # 分离 nonce (前12字节) 和 ciphertext
            nonce = data[:12]
            ciphertext = data[12:]
            
            # 解密
            plaintext = aesgcm.decrypt(nonce, ciphertext, None)
            
            return plaintext.decode('utf-8')
        
        except Exception as e:
            # 解密失败 (可能是数据损坏或密钥不匹配)
            print(f"⚠️ Decryption failed: {e}")
            return ""


# 便捷函数
def encrypt_value(value: Optional[str]) -> Optional[str]:
    """加密单个值，None 输入返回 None"""
    if value is None:
        return None
    return FieldEncryption.encrypt(value)


def decrypt_value(encrypted: Optional[str]) -> Optional[str]:
    """解密单个值，None 输入返回 None"""
    if encrypted is None:
        return None
    return FieldEncryption.decrypt(encrypted)


# ============================================
# 示例用法:
# ============================================
# from backend.core.security import encrypt_value, decrypt_value
#
# # 加密存储
# encrypted_phone = encrypt_value("13812345678")
# db_model._encrypted_phone = encrypted_phone
#
# # 解密读取
# phone = decrypt_value(db_model._encrypted_phone)
# ============================================
