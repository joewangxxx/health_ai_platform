from typing import Optional, List
from datetime import datetime
from sqlmodel import Field, SQLModel, Relationship
from sqlalchemy import JSON, Column

class UserBase(SQLModel):
    username: str = Field(index=True, unique=True)
    email: Optional[str] = Field(default=None)

class User(UserBase, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    hashed_password: str
    is_superuser: bool = Field(default=False)
    
    # Relationship
    # Relationship
    profile: Optional["UserProfile"] = Relationship(back_populates="user")
    records: List["HealthRecord"] = Relationship(back_populates="user")

class UserRead(UserBase):
    id: int
    is_superuser: bool

class UserProfile(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="user.id", unique=True)
    
    # ================= 基础信息 =================
    Age: Optional[int] = None
    Gender: Optional[int] = None  # 1=Male, 2=Female
    
    # ================= 身体指标 =================
    Height: Optional[float] = None      # cm
    Weight: Optional[float] = None      # kg
    BMI: Optional[float] = None
    WaistCircum: Optional[float] = None # cm
    SBP: Optional[int] = None           # 收缩压
    DBP: Optional[int] = None           # 舒张压
    
    # ================= 生化指标 (V10/V12) =================
    Glucose_Fasting: Optional[float] = None
    HbA1c: Optional[float] = None
    Cholesterol_Total: Optional[float] = None
    Triglycerides: Optional[float] = None
    Cholesterol_HDL: Optional[float] = None
    Cholesterol_LDL: Optional[float] = None
    eGFR: Optional[float] = None
    ALT: Optional[float] = None
    
    # 🔥 V10 新增血常规 & 肝功能
    WBC: Optional[float] = None         # 白细胞 10^9/L
    Platelet: Optional[float] = None    # 血小板 10^9/L
    GGT: Optional[float] = None         # γ-谷氨酰转肽酶 U/L
    ALP: Optional[float] = None         # 碱性磷酸酶 U/L
    Creatinine: Optional[float] = None  # 肌酐 μmol/L
    
    # ================= 生活方式 =================
    Sleep_Hours: Optional[float] = None
    
    # ================= 基因组 & 历史数据 (JSON) =================
    # Task 134: 敏感数据加密存储
    # genomic_data 使用加密存储，通过 property 透明处理
    encrypted_genomic_data: Optional[str] = Field(default=None, description="加密后的基因数据")
    risk_history: Optional[str] = None   # JSON: 上次计算的风险报告
    
    # Task 73: Store non-structured extra findings
    extra_data: Optional[dict] = Field(default={}, sa_column=Column(JSON))
    
    # Task 85: Privacy-preserving research data sharing consent
    allow_research: bool = Field(default=False, description="是否允许匿名数据用于科研")

    # Relationship
    user: Optional[User] = Relationship(back_populates="profile")
    
    # ============================================
    # Task 134: 加密字段属性 (Property Decorators)
    # ============================================
    @property
    def genomic_data(self) -> Optional[str]:
        """解密读取基因组数据"""
        if not self.encrypted_genomic_data:
            return None
        try:
            from backend.core.security import decrypt_value
            return decrypt_value(self.encrypted_genomic_data)
        except Exception:
            # 兼容旧数据 (未加密的)
            return self.encrypted_genomic_data
    
    @genomic_data.setter
    def genomic_data(self, value: Optional[str]):
        """加密存储基因组数据"""
        if value is None:
            self.encrypted_genomic_data = None
        else:
            from backend.core.security import encrypt_value
            self.encrypted_genomic_data = encrypt_value(value)

class HealthRecord(SQLModel, table=True):
    """
    Time-series health record for history tracking
    """
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="user.id")
    record_date: datetime = Field(default_factory=datetime.utcnow)
    source: str = Field(default="manual") # upload, manual, device
    
    # Store key metrics as JSON since schema might evolve
    # Example: {"BMI": 24.5, "Glucose_Fasting": 5.6, "SBP": 120, "DBP": 80}
    metrics: str = Field(default="{}") 
    
    # Store risk snapshot
    risk_snapshot: Optional[str] = Field(default=None)

    # Relationship
    user: Optional[User] = Relationship(back_populates="records")

# Schema for Auth
class UserCreate(UserBase):
    password: str

class Token(SQLModel):
    access_token: str

class IoTHealthData(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="user.id")  # 关联用户
    device_type: str  # 设备类型，例如 "BLE_HRM", "MiBand"
    data_type: str    # 数据类型，例如 "heart_rate", "steps"
    value: float      # 数值
    unit: str         # 单位，例如 "bpm", "steps"
    raw_data: Optional[str] = None # 原始数据备份(可选)
    recorded_at: datetime = Field(default_factory=datetime.utcnow)

class MedicalDocument(SQLModel, table=True):
    """
    存储用户上传的体检报告文件 (Task 56)
    """
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="user.id")
    file_name: str              # 原始文件名
    file_path: str              # 本地存储路径
    file_url: str               # 前端访问 URL
    upload_date: datetime = Field(default_factory=datetime.utcnow)
    ocr_summary: Optional[str] = None  # JSON: 关键提取摘要


# ============================================
# Task 132: 亲情账户关联体系 (Family Account Linking)
# ============================================
class FamilyLink(SQLModel, table=True):
    """
    亲情账户关联表
    - manager: 主账户 (子女/管理者)
    - member: 被管理账户 (父母/家人)
    """
    id: Optional[int] = Field(default=None, primary_key=True)
    manager_id: int = Field(foreign_key="user.id", index=True)  # 管理者账户ID
    member_id: int = Field(foreign_key="user.id", index=True)   # 被管理账户ID
    relation_name: str = Field(default="家人")  # 关系名称: 父亲/母亲/爷爷等
    created_at: datetime = Field(default_factory=datetime.utcnow)
    is_active: bool = Field(default=True)  # 是否有效

    class Config:
        # 确保唯一性: 一个管理者不能重复关联同一个家人
        # 通过业务逻辑校验，而非数据库约束
        pass


class FamilyInvite(SQLModel, table=True):
    """
    亲情账户邀请码表
    """
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="user.id", unique=True)  # 生成邀请码的用户
    invite_code: str = Field(unique=True, index=True)  # 6位邀请码
    created_at: datetime = Field(default_factory=datetime.utcnow)
    expires_at: Optional[datetime] = None  # 过期时间 (可选)


