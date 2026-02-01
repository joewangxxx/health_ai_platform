import sys
import os

# ================= 🔧 1. 路径修正 =================
# 获取当前脚本所在目录 (backend)
current_dir = os.path.dirname(os.path.abspath(__file__))
# 获取项目根目录 (health_ai_platform_2.0)
project_root = os.path.dirname(current_dir)

# 🔥 核心修复：只将【项目根目录】加入 sys.path
# 这样我们只能通过 'backend.xxx' 来导入，保证和 auth.py 里的导入路径完全一致
if project_root not in sys.path:
    sys.path.append(project_root)

# ================= 📦 2. 模块导入 (统一使用 backend. 前缀) =================
try:
    from sqlmodel import Session, select, create_engine, SQLModel
    # 🔥 以前是 from models import User，现在必须改掉
    from backend.models import User 
    from backend.auth import get_password_hash
except ImportError as e:
    print(f"❌ 导入失败: {e}")
    print("请确保你在 health_ai_platform_2.0 根目录下，或者 Python 环境配置正确。")
    sys.exit(1)

# ================= ⚙️ 数据库配置 =================
# 🔥 直接引用 database.py 的变量，避免硬编码不一致
from backend.database import DATABASE_PATH, engine

def create_admin():
    print(f"📁 数据库路径: {DATABASE_PATH}")
    print("🔄 正在删除旧表结构...")
    SQLModel.metadata.drop_all(engine)  # ← 强制删除旧表
    print("🔄 正在创建新表结构...")
    SQLModel.metadata.create_all(engine)  # ← 重建新表
    
    print("👤 正在检查/创建管理员账号...")
    
    with Session(engine) as session:
        # 检查是否已存在
        statement = select(User).where(User.username == "admin")
        results = session.exec(statement)
        existing_admin = results.first()
        
        if existing_admin:
            print("⚠️ 管理员账号 'admin' 已存在。")
            if not existing_admin.is_superuser:
                print("   - 正在自动升级为超级管理员...")
                existing_admin.is_superuser = True
                session.add(existing_admin)
                session.commit()
                print("   ✅ 升级权限成功。")
            return

        # 创建新管理员
        admin_user = User(
            username="admin",
            email="admin@healthai.com",
            # 使用 auth.py 中的哈希函数
            hashed_password=get_password_hash("admin"),
            is_superuser=True
        )
        
        session.add(admin_user)
        session.commit()
        session.refresh(admin_user)
        
        print("✅ 成功！管理员账号已创建。")
        print("👉 账号: admin")
        print("👉 密码: admin")

if __name__ == "__main__":
    create_admin()