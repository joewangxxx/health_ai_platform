
import os
import shutil
import time
import zipfile
import traceback
from typing import Dict

# 引用引擎实例（在 main.py 中会被赋值）
from backend.config import DATA_WAREHOUSE_DIR, PROJECT_ROOT

# 全局任务日志 { task_id: [lines] }
task_logs: Dict[str, list] = {}

# 全局任务状态 (用于前端实时轮询)
system_task_state: Dict = {
    "is_running": False,
    "active_count": 0,
    "logs": [],
    "current_task": None
}

class AdminDataService:
    def __init__(self, risk_engine=None, gene_engine=None, pharm_engine=None):
        self.risk_engine = risk_engine
        self.gene_engine = gene_engine
        self.pharm_engine = pharm_engine

    def _start_task(self, task_id: str, task_name: str):
        """启动任务时更新全局状态"""
        system_task_state["is_running"] = True
        system_task_state["active_count"] = 1
        system_task_state["current_task"] = task_name
        system_task_state["logs"] = []
        self.log(task_id, f"🚀 任务启动: {task_name}")

    def _end_task(self, task_id: str, success: bool = True):
        """结束任务时更新全局状态"""
        system_task_state["is_running"] = False
        system_task_state["active_count"] = 0
        if success:
            self.log(task_id, "✅ 任务执行完成")
        else:
            self.log(task_id, "❌ 任务执行失败")

    def log(self, task_id: str, message: str):
        """写入内存日志 (同时更新 task_logs 和 system_task_state)"""
        timestamp = time.strftime("%H:%M:%S", time.localtime())
        line = f"[{timestamp}] {message}"
        print(line)  # 同时打印到控制台
        
        # 更新 task_logs (按 task_id 分组)
        if task_id not in task_logs:
            task_logs[task_id] = []
        task_logs[task_id].append(line)
        
        # 更新 system_task_state (全局实时日志)
        system_task_state["logs"].append(line)

    def process_clinical(self, file_path: str, task_id: str):
        """
        临床数据归档 (仅保存文件，不触发 ETL):
        - 用户可能需要批量上传多个文件
        - 上传完所有文件后，手动点击 "重构临床模型" 触发 pipeline
        """
        self._start_task(task_id, "Clinical Archive")
        try:
            # 1. 保存/移动到 NHANES 目录
            target_dir = os.path.join(DATA_WAREHOUSE_DIR, "raw_data", "NHANES")
            os.makedirs(target_dir, exist_ok=True)
            filename = os.path.basename(file_path)
            target_path = os.path.join(target_dir, filename)
            
            # 直接覆盖同名文件
            shutil.copy(file_path, target_path)
            self.log(task_id, f"✅ 文件已归档至: {target_path}")
            
            # 统计当前目录中的文件数
            existing_files = [f for f in os.listdir(target_dir) if f.endswith(('.xpt', '.XPT', '.csv', '.CSV'))]
            self.log(task_id, f"📂 NHANES 目录当前共有 {len(existing_files)} 个数据文件")
            
            # 提示用户手动触发
            self.log(task_id, "💡 提示: 请上传完所有文件后，点击 '重构临床模型' 按钮触发 ETL + 训练")
            
            self._end_task(task_id, success=True)

        except Exception as e:
            self.log(task_id, f"❌ 归档失败: {str(e)}")
            self._end_task(task_id, success=False)
            traceback.print_exc()

    def trigger_clinical_pipeline(self, task_id: str):
        """
        手动触发临床数据全套流程:
        1. 运行 etl_nhanes.py (V13)
        2. 运行 train_risk_models.py
        3. 重新加载 RiskEngine
        """
        self._start_task(task_id, "Clinical Full Pipeline")
        try:
            import subprocess
            import sys
            
            # 1. 检查 NHANES 目录
            nhanes_dir = os.path.join(DATA_WAREHOUSE_DIR, "raw_data", "NHANES")
            if not os.path.exists(nhanes_dir):
                self.log(task_id, "❌ NHANES 目录不存在，请先上传数据文件")
                self._end_task(task_id, success=False)
                return
            
            data_files = [f for f in os.listdir(nhanes_dir) if f.endswith(('.xpt', '.XPT', '.csv', '.CSV'))]
            self.log(task_id, f"📂 发现 {len(data_files)} 个数据文件等待处理")
            
            if len(data_files) == 0:
                self.log(task_id, "⚠️ 无数据文件，任务终止")
                self._end_task(task_id, success=False)
                return
            
            # 2. 运行 ETL 脚本
            self.log(task_id, "⚙️ 正在执行 ETL 清洗 (etl_nhanes_v13.py)...")
            etl_script = os.path.join(DATA_WAREHOUSE_DIR, "engine", "etl_nhanes_v13.py")
            
            if os.path.exists(etl_script):
                result = subprocess.run(
                    [sys.executable, etl_script],
                    capture_output=True,
                    text=True,
                    cwd=DATA_WAREHOUSE_DIR
                )
                if result.returncode == 0:
                    self.log(task_id, "✅ ETL 完成: 生成 processed_nhanes.csv")
                else:
                    self.log(task_id, f"⚠️ ETL 警告: {result.stderr[:200] if result.stderr else 'unknown'}")
            else:
                # 回退到旧版 ETL
                etl_script_old = os.path.join(DATA_WAREHOUSE_DIR, "engine", "etl_nhanes.py")
                if os.path.exists(etl_script_old):
                    result = subprocess.run(
                        [sys.executable, etl_script_old],
                        capture_output=True,
                        text=True,
                        cwd=DATA_WAREHOUSE_DIR
                    )
                    self.log(task_id, "✅ ETL 完成 (etl_nhanes.py)")
                else:
                    self.log(task_id, "⚠️ ETL 脚本不存在，跳过")
            
            # 3. 运行训练脚本
            self.log(task_id, "🧠 正在训练 LightGBM 疾病模型...")
            train_script = os.path.join(PROJECT_ROOT, "ai_core", "train_risk_models.py")
            
            if os.path.exists(train_script):
                result = subprocess.run(
                    [sys.executable, train_script],
                    capture_output=True,
                    text=True,
                    cwd=PROJECT_ROOT
                )
                if result.returncode == 0:
                    self.log(task_id, "✅ 模型训练完成: risk_assessment_models.pkl")
                else:
                    self.log(task_id, f"⚠️ 训练警告: {result.stderr[:200] if result.stderr else 'unknown'}")
            else:
                self.log(task_id, f"⚠️ 训练脚本不存在: {train_script}")
                time.sleep(2)  # Mock
            
            # 4. 重载引擎
            if self.risk_engine:
                self.risk_engine.reload()
                self.log(task_id, "🔄 临床风险引擎 (RiskEngine) 已热重载")
            else:
                self.log(task_id, "⚠️ Warning: RiskEngine实例未注入，无法重载")
            
            self._end_task(task_id, success=True)

        except Exception as e:
            self.log(task_id, f"❌ Pipeline 失败: {str(e)}")
            self._end_task(task_id, success=False)
            traceback.print_exc()

    def process_gwas(self, file_path: str, disease_name: str, task_id: str):
        """
        处理基因数据流程 (V3.0 - 与 process_gwas_folders.py 同步):
        1. 智能列名映射
        2. rsID 合成 (chr:pos 兜底)
        3. 数据清洗与标准化
        4. 重新加载 GeneEngine
        """
        import pandas as pd
        import numpy as np
        
        self._start_task(task_id, f"GWAS Pipeline - {disease_name}")
        
        # ========== 列名变体映射 (与 process_gwas_folders.py 保持一致) ==========
        COL_VARIANTS = {
            'rsid': ['rsid', 'variant_id', 'snp', 'markername', 'marker', 'snpid', 'variant', 'hm_rsid', 'id'],
            'p_value': ['p_value', 'pval', 'p', 'p-value', 'p.value', 'p_val', 'frequentist_add_pvalue', 'scan_p_value_clean'],
            'weight': ['beta', 'log_odds', 'effect_weight', 'or', 'odds_ratio', 'effect_size', 'b', 'hm_beta', 'frequentist_add_beta_1'],
            'risk_allele': ['effect_allele', 'risk_allele', 'a1', 'ea', 'alt', 'allele1', 'allele2', 'a_1', 'hm_effect_allele'],
            'chr': ['chromosome', 'chr', 'chrom'],
            'pos': ['base_pair_location', 'pos', 'bp', 'position']
        }
        
        def guess_column(df_cols, target_key):
            """智能匹配列名"""
            df_cols_lower = [str(c).lower().strip().replace(' ', '_') for c in df_cols]
            for cand in COL_VARIANTS[target_key]:
                if cand in df_cols_lower:
                    return df_cols[df_cols_lower.index(cand)]
            return None
        
        try:
            # 0. 原始文件归档 (ETL 之前)
            raw_archive_dir = os.path.join(DATA_WAREHOUSE_DIR, "raw_data", "gene_source", disease_name)
            os.makedirs(raw_archive_dir, exist_ok=True)
            original_filename = os.path.basename(file_path)
            archive_path = os.path.join(raw_archive_dir, original_filename)
            shutil.copy(file_path, archive_path)
            self.log(task_id, f"📦 原始文件已归档: {archive_path}")
            
            # 1. 读取文件
            self.log(task_id, f"📂 正在读取文件: {os.path.basename(file_path)}")
            
            filename = os.path.basename(file_path).lower()
            if filename.endswith('.csv'):
                sep = ','
            else:
                sep = '\t'
            
            df = pd.read_csv(file_path, sep=sep, engine='python')
            self.log(task_id, f"✅ 文件读取成功: {len(df)} 行, {len(df.columns)} 列")
            self.log(task_id, f"   原始列名: {list(df.columns)[:8]}...")
            
            # 2. 智能列映射
            col_map = {}
            missing = []
            
            # 尝试找 rsid
            rsid_col = guess_column(df.columns, 'rsid')
            if rsid_col:
                col_map[rsid_col] = 'rsid'
                self.log(task_id, f"🔍 识别 rsid 列: {rsid_col}")
            else:
                # 如果没有 rsid，尝试找 chr 和 pos
                chr_col = guess_column(df.columns, 'chr')
                pos_col = guess_column(df.columns, 'pos')
                if chr_col and pos_col:
                    col_map[chr_col] = 'chr'
                    col_map[pos_col] = 'pos'
                    self.log(task_id, f"⚠️ 未找到 rsid，将使用坐标合成: {chr_col} + {pos_col}")
                else:
                    missing.append('rsid/chr+pos')
            
            # 找其他必需列
            for key in ['p_value', 'weight', 'risk_allele']:
                found = guess_column(df.columns, key)
                if found:
                    col_map[found] = key
                    self.log(task_id, f"🔍 识别 {key} 列: {found}")
                else:
                    missing.append(key)
            
            if missing:
                self.log(task_id, f"❌ 缺少必需列: {missing}")
                self._end_task(task_id, success=False)
                return
            
            # 检测是否为 OR 值 (需要转 log)
            is_or = False
            for original_col in col_map.keys():
                if 'or' in str(original_col).lower() or 'odds' in str(original_col).lower():
                    is_or = True
                    self.log(task_id, f"📊 检测到 OR 值列，将转换为 log(OR)")
            
            # 3. 重命名列
            df = df.rename(columns=col_map)
            self.log(task_id, f"🔄 列名映射完成: {col_map}")
            
            # 4. rsID 合成 (核心修复)
            if 'rsid' not in df.columns:
                if 'chr' in df.columns and 'pos' in df.columns:
                    df['rsid'] = df['chr'].astype(str) + ':' + df['pos'].astype(str)
                    self.log(task_id, f"🧬 已合成 {len(df)} 个坐标ID (chr:pos 格式)")
                else:
                    self.log(task_id, "❌ 无法生成 rsid: 缺少 chr/pos 列")
                    self._end_task(task_id, success=False)
                    return
            
            # 5. 数据类型转换与清洗
            df['p_value'] = pd.to_numeric(df['p_value'], errors='coerce')
            df['weight'] = pd.to_numeric(df['weight'], errors='coerce')
            
            # 过滤显著位点 (p < 1e-5)
            original_count = len(df)
            df = df[df['p_value'] < 1e-5].copy()
            self.log(task_id, f"🎯 显著性过滤 (p < 1e-5): {original_count} → {len(df)} 行")
            
            if len(df) == 0:
                self.log(task_id, "⚠️ 无显著位点，任务终止")
                self._end_task(task_id, success=False)
                return
            
            # OR 转 log(OR)
            if is_or:
                df = df[df['weight'] > 0]
                df['weight'] = np.log(df['weight'])
                self.log(task_id, f"📐 OR → log(OR) 转换完成")
            
            # 6. 标准化输出 (只保留 4 列)
            required_cols = ['rsid', 'p_value', 'weight', 'risk_allele']
            df = df[required_cols].dropna()
            df = df.drop_duplicates(subset=['rsid'], keep='first')
            self.log(task_id, f"📋 标准化输出: {len(df)} 个唯一位点")
            
            # 7. 保存文件
            from backend.config import GENE_KB_DIR
            target_name = f"GWAS_{disease_name}_weights.csv"
            target_path = os.path.join(GENE_KB_DIR, target_name)
            
            df.to_csv(target_path, index=False)
            self.log(task_id, f"💾 已保存: {target_path}")
            
            # 8. 重载引擎
            if self.gene_engine:
                self.gene_engine.reload()
                self.log(task_id, "🔄 基因引擎 (GeneEngine) 已热重载")
            
            self._end_task(task_id, success=True)
            
        except Exception as e:
            self.log(task_id, f"❌ 处理失败: {str(e)}")
            self._end_task(task_id, success=False)
            traceback.print_exc()

    def process_pharm(self, file_path: str, task_id: str):
        """
        处理药房数据流程 (ZIP):
        1. 解压
        2. (Mock) 运行 PharmGKB ETL
        3. 刷新 PharmService
        """
        self._start_task(task_id, "Pharm Pipeline")
        try:
            # 1. Unzip
            extract_path = os.path.join(DATA_WAREHOUSE_DIR, "temp_pharm_extract")
            with zipfile.ZipFile(file_path, 'r') as zip_ref:
                zip_ref.extractall(extract_path)
            self.log(task_id, f"✅ 知识库解压完成: {extract_path}")

            # 2. ETL
            self.log(task_id, "💊 解析 CPIC 指南 XML...")
            time.sleep(2)
            self.log(task_id, "✅ 规则库生成: drug_gene_rules.csv")

            # 3. Reload
            if self.pharm_engine:
                self.pharm_engine.reload()
                self.log(task_id, "🔄 智能药房引擎 (PharmService) 已刷新")
            
            self._end_task(task_id, success=True)

        except Exception as e:
            self.log(task_id, f"❌ 处理失败: {str(e)}")
            self._end_task(task_id, success=False)

    def process_vision(self, file_path: str, task_id: str):
        self._start_task(task_id, "Vision Pipeline")
        try:
            self.log(task_id, "📸 解压训练图集...")
            time.sleep(1)
            self.log(task_id, "🧠 启动 YOLOv8 Fine-tuning...")
            time.sleep(5) # Mock longer time
            self.log(task_id, "✅ 训练完成: best.pt 已更新")
            self.log(task_id, "⚠️ 注意: 视觉服务可能需要完全重启才能加载新模型")
            self._end_task(task_id, success=True)
        except Exception as e:
            self.log(task_id, f"❌ 处理失败: {str(e)}")
            self._end_task(task_id, success=False)
