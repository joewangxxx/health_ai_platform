# ============================================
# Task 134: 鏁忔劅鏁版嵁瀛楁绾у姞瀵嗗伐鍏?
# AES-256-GCM 鍔犲瘑瀹炵幇
# ============================================

from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
import base64
import logging
import os
from typing import Optional
from backend.core.config import settings

logger = logging.getLogger(__name__)


class FieldEncryption:
    """
    瀛楁绾у姞瀵嗗伐鍏风被
    浣跨敤 AES-256-GCM 瀵规晱鎰熸暟鎹繘琛屽姞瀵?
    
    Features:
    - 鍩轰簬 SECRET_KEY 娲剧敓鍔犲瘑瀵嗛挜
    - 姣忔鍔犲瘑浣跨敤鍞竴鐨?Nonce (闃叉閲嶆斁鏀诲嚮)
    - 鏀寔璁よ瘉鍔犲瘑 (AEAD)锛岄槻姝㈡暟鎹鏀?
    """
    
    _key: bytes = None
    _salt: bytes = b"health_ai_encryption_salt_v1"  # 鍥哄畾鐩愬€肩敤浜庡瘑閽ユ淳鐢?
    
    @classmethod
    def _get_key(cls) -> bytes:
        """
        浠?SECRET_KEY 娲剧敓 256-bit 鍔犲瘑瀵嗛挜
        浣跨敤 PBKDF2 瀵嗛挜娲剧敓鍑芥暟
        """
        if cls._key is None:
            secret = settings.SECRET_KEY.encode('utf-8')
            
            kdf = PBKDF2HMAC(
                algorithm=hashes.SHA256(),
                length=32,  # 256 bits for AES-256
                salt=cls._salt,
                iterations=100_000,  # OWASP 鎺ㄨ崘鐨勮凯浠ｆ鏁?
            )
            cls._key = kdf.derive(secret)
        
        return cls._key
    
    @classmethod
    def encrypt(cls, plaintext: str) -> str:
        """
        鍔犲瘑鏄庢枃瀛楃涓?
        
        Args:
            plaintext: 寰呭姞瀵嗙殑鏄庢枃瀛楃涓?
            
        Returns:
            str: Base64 缂栫爜鐨勫瘑鏂?(鏍煎紡: nonce + ciphertext)
        """
        if not plaintext:
            return ""
        
        key = cls._get_key()
        aesgcm = AESGCM(key)
        
        # 鐢熸垚闅忔満 12-byte nonce (GCM 鎺ㄨ崘闀垮害)
        nonce = os.urandom(12)
        
        # 鍔犲瘑
        ciphertext = aesgcm.encrypt(nonce, plaintext.encode('utf-8'), None)
        
        # 鎷兼帴 nonce + ciphertext 骞剁紪鐮佷负 Base64
        encrypted = base64.b64encode(nonce + ciphertext).decode('utf-8')
        
        return encrypted
    
    @classmethod
    def decrypt(cls, encrypted: str) -> str:
        """
        瑙ｅ瘑瀵嗘枃瀛楃涓?
        
        Args:
            encrypted: Base64 缂栫爜鐨勫瘑鏂?
            
        Returns:
            str: 瑙ｅ瘑鍚庣殑鏄庢枃锛岃В瀵嗗け璐ヨ繑鍥炵┖瀛楃涓?
        """
        if not encrypted:
            return ""
        
        try:
            key = cls._get_key()
            aesgcm = AESGCM(key)
            
            # 瑙ｇ爜 Base64
            data = base64.b64decode(encrypted.encode('utf-8'))
            
            # 鍒嗙 nonce (鍓?2瀛楄妭) 鍜?ciphertext
            nonce = data[:12]
            ciphertext = data[12:]
            
            # 瑙ｅ瘑
            plaintext = aesgcm.decrypt(nonce, ciphertext, None)
            
        except Exception as e:
            # Decryption failed; return an empty string so callers can degrade safely.
            logger.warning("Decryption failed: %s", e)
            return ""


# 渚挎嵎鍑芥暟
def encrypt_value(value: Optional[str]) -> Optional[str]:
    """鍔犲瘑鍗曚釜鍊硷紝None 杈撳叆杩斿洖 None"""
    if value is None:
        return None
    return FieldEncryption.encrypt(value)


def decrypt_value(encrypted: Optional[str]) -> Optional[str]:
    """瑙ｅ瘑鍗曚釜鍊硷紝None 杈撳叆杩斿洖 None"""
    if encrypted is None:
        return None
    return FieldEncryption.decrypt(encrypted)


# ============================================
# 绀轰緥鐢ㄦ硶:
# ============================================
# from backend.core.security import encrypt_value, decrypt_value
#
# # 鍔犲瘑瀛樺偍
# encrypted_phone = encrypt_value("13812345678")
# db_model._encrypted_phone = encrypted_phone
#
# # 瑙ｅ瘑璇诲彇
# phone = decrypt_value(db_model._encrypted_phone)
# ============================================
