"""
🔍 HealthAI 数据库诊断脚本
用于检查 SQLModel 模型定义与物理数据库结构是否一致

运行方式: python backend/debug_db.py
"""

import os
import sys
import sqlite3

# ================= 1. 路径设置 =================
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(SCRIPT_DIR)

print("=" * 60)
print("🔍 HealthAI 数据库诊断工具")
print("=" * 60)

# ================= 2. 检查 Python 运行时路径 =================
print("\n📂 [Step 1] 检查路径一致性")
print(f"   脚本所在目录 (SCRIPT_DIR): {SCRIPT_DIR}")
print(f"   项目根目录 (PROJECT_ROOT): {PROJECT_ROOT}")
print(f"   当前工作目录 (os.getcwd()): {os.getcwd()}")

# ================= 3. 查找所有可能的数据库文件 =================
print("\n📂 [Step 2] 扫描可能的数据库文件")

possible_paths = [
    os.path.join(SCRIPT_DIR, "users.db"),           # backend/users.db
    os.path.join(PROJECT_ROOT, "users.db"),         # 项目根目录/users.db
    os.path.join(os.getcwd(), "users.db"),          # CWD/users.db
    os.path.join(SCRIPT_DIR, "healthai.db"),        # 旧名称
]

found_dbs = []
for path in possible_paths:
    exists = os.path.exists(path)
    status = "✅ 存在" if exists else "❌ 不存在"
    print(f"   {status}: {path}")
    if exists:
        found_dbs.append(path)
        # 显示文件大小和修改时间
        stat = os.stat(path)
        from datetime import datetime
        mtime = datetime.fromtimestamp(stat.st_mtime).strftime('%Y-%m-%d %H:%M:%S')
        print(f"      📊 大小: {stat.st_size} bytes, 修改时间: {mtime}")

# ================= 4. 检查代码中定义的字段 =================
print("\n📝 [Step 3] 检查 models.py 中 UserProfile 的字段定义")

try:
    # 动态导入 models
    sys.path.insert(0, PROJECT_ROOT)
    from backend.models import UserProfile
    
    # 获取所有字段
    model_fields = list(UserProfile.model_fields.keys())
    print(f"   代码中定义的字段 ({len(model_fields)} 个):")
    for field in model_fields:
        print(f"      - {field}")
except Exception as e:
    print(f"   ❌ 导入 models.py 失败: {e}")
    model_fields = []

# ================= 5. 检查物理数据库中的字段 =================
print("\n💽 [Step 4] 检查物理数据库中 userprofile 表的实际结构")

for db_path in found_dbs:
    print(f"\n   --- 数据库: {db_path} ---")
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # 获取表结构
        cursor.execute("PRAGMA table_info(userprofile);")
        columns = cursor.fetchall()
        
        if columns:
            db_column_names = [col[1] for col in columns]
            print(f"   数据库中实际存在的列 ({len(columns)} 个):")
            for col in columns:
                print(f"      - {col[1]} ({col[2]})")  # 列名, 类型
        else:
            print("   ⚠️ userprofile 表不存在!")
        
        conn.close()
        
        # ================= 6. 对比分析 =================
        if columns and model_fields:
            print(f"\n   🔎 对比分析:")
            
            # 代码有但数据库没有的字段
            missing_in_db = set(model_fields) - set(db_column_names)
            if missing_in_db:
                print(f"   ❌ 代码中有但数据库中缺失的字段 ({len(missing_in_db)} 个):")
                for field in sorted(missing_in_db):
                    print(f"      🔴 {field}")
            else:
                print("   ✅ 所有代码字段在数据库中都存在")
            
            # 数据库有但代码没有的字段
            extra_in_db = set(db_column_names) - set(model_fields)
            if extra_in_db:
                print(f"   ⚠️ 数据库中有但代码中没有的字段 ({len(extra_in_db)} 个):")
                for field in sorted(extra_in_db):
                    print(f"      🟡 {field}")
                    
    except Exception as e:
        print(f"   ❌ 读取数据库失败: {e}")

# ================= 7. 解决方案建议 =================
print("\n" + "=" * 60)
print("💡 解决方案")
print("=" * 60)
print("""
SQLModel (SQLAlchemy) 不会自动迁移已存在的表结构！

🔧 为什么会这样?
   SQLModel.metadata.create_all(engine) 只会在表不存在时创建表。
   如果表已存在，即使你修改了 Python 模型，数据库表结构也不会更新。

🛠️ 解决方案:

   方案 A: 删除旧数据库 (开发环境推荐)
   ----------------------------------
   1. 停止后端服务
   2. 删除数据库文件:
      del f:\\health_ai_platform_2.0\\backend\\users.db
   3. 重启后端，SQLModel 会自动创建新表

   方案 B: 手动 ALTER TABLE (生产环境)
   ----------------------------------
   你也可以用 sqlite3 手动添加缺失的列:
   
   sqlite3 backend/users.db
   ALTER TABLE userprofile ADD COLUMN Height REAL;
   ALTER TABLE userprofile ADD COLUMN Weight REAL;
   -- ... 其他缺失字段

   方案 C: 使用 Alembic 迁移工具 (专业方案)
   ----------------------------------
   pip install alembic
   alembic init alembic
   alembic revision --autogenerate -m "add new fields"
   alembic upgrade head
""")

print("=" * 60)
print("诊断完成!")
print("=" * 60)
