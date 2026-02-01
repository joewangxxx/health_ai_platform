"""
Task 101: PDF Health Report Generator
======================================
使用 reportlab 生成专业健康报告 PDF。
支持中文显示、表格、风险评估和建议。
"""
import io
import os
import logging
from datetime import datetime
from typing import Dict, Any, List, Optional

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm, cm
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_JUSTIFY
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, 
    PageBreak, Image, ListFlowable, ListItem
)
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

# 配置日志
logger = logging.getLogger(__name__)

# ================= 字体配置 =================
# 尝试注册中文字体
FONT_REGISTERED = False
FONT_NAME = "SimHei"

def _register_chinese_font():
    """注册中文字体，支持多种路径"""
    global FONT_REGISTERED, FONT_NAME
    
    if FONT_REGISTERED:
        return True
    
    # 常见中文字体路径 (按优先级排序)
    font_paths = [
        # Windows 系统字体
        r"C:\Windows\Fonts\simhei.ttf",      # 黑体
        r"C:\Windows\Fonts\msyh.ttc",        # 微软雅黑
        r"C:\Windows\Fonts\simsun.ttc",      # 宋体
        r"C:\Windows\Fonts\simkai.ttf",      # 楷体
        # 项目 assets 目录 (用于跨平台部署)
        os.path.join(os.path.dirname(__file__), "..", "assets", "fonts", "NotoSansSC-Regular.ttf"),
        os.path.join(os.path.dirname(__file__), "..", "assets", "fonts", "SimHei.ttf"),
    ]
    
    for path in font_paths:
        if os.path.exists(path):
            try:
                if path.endswith('.ttc'):
                    # TTC 字体需要指定子字体索引
                    pdfmetrics.registerFont(TTFont(FONT_NAME, path, subfontIndex=0))
                else:
                    pdfmetrics.registerFont(TTFont(FONT_NAME, path))
                FONT_REGISTERED = True
                logger.info(f"✅ PDF 中文字体注册成功: {path}")
                print(f"✅ PDF 中文字体注册成功: {path}")
                return True
            except Exception as e:
                logger.warning(f"⚠️ 字体注册失败 {path}: {e}")
    
    logger.warning("⚠️ 未找到中文字体，PDF 可能显示乱码。建议将 SimHei.ttf 放入 backend/assets/fonts/")
    print("⚠️ 未找到中文字体，PDF 可能显示乱码")
    FONT_NAME = "Helvetica"
    return False


class PDFGenerationError(Exception):
    """PDF 生成异常"""
    pass


class PDFHealthReportService:
    """
    健康报告 PDF 生成服务
    """
    
    def __init__(self):
        self.font_available = _register_chinese_font()
        self.font_name = FONT_NAME
        self.styles = self._create_styles()
    
    def _create_styles(self) -> Dict[str, ParagraphStyle]:
        """创建自定义样式"""
        base_styles = getSampleStyleSheet()
        
        return {
            "title": ParagraphStyle(
                "Title",
                parent=base_styles["Title"],
                fontName=self.font_name,
                fontSize=24,
                textColor=colors.HexColor("#1a365d"),
                spaceAfter=20,
                alignment=TA_CENTER,
            ),
            "subtitle": ParagraphStyle(
                "Subtitle",
                parent=base_styles["Normal"],
                fontName=self.font_name,
                fontSize=14,
                textColor=colors.grey,
                spaceAfter=30,
                alignment=TA_CENTER,
            ),
            "heading1": ParagraphStyle(
                "Heading1",
                parent=base_styles["Heading1"],
                fontName=self.font_name,
                fontSize=16,
                textColor=colors.HexColor("#2c5282"),
                spaceBefore=20,
                spaceAfter=10,
                borderColor=colors.HexColor("#4299e1"),
                borderWidth=0,
                borderPadding=5,
            ),
            "heading2": ParagraphStyle(
                "Heading2",
                parent=base_styles["Heading2"],
                fontName=self.font_name,
                fontSize=13,
                textColor=colors.HexColor("#2d3748"),
                spaceBefore=15,
                spaceAfter=8,
            ),
            "body": ParagraphStyle(
                "Body",
                parent=base_styles["Normal"],
                fontName=self.font_name,
                fontSize=10,
                textColor=colors.HexColor("#1a202c"),
                leading=16,
                alignment=TA_JUSTIFY,
            ),
            "highlight": ParagraphStyle(
                "Highlight",
                parent=base_styles["Normal"],
                fontName=self.font_name,
                fontSize=11,
                textColor=colors.HexColor("#c53030"),
                leading=16,
            ),
            "advice": ParagraphStyle(
                "Advice",
                parent=base_styles["Normal"],
                fontName=self.font_name,
                fontSize=10,
                textColor=colors.HexColor("#276749"),
                leading=14,
                leftIndent=20,
            ),
        }
    
    def create_health_report(
        self,
        user_profile: Dict[str, Any],
        risk_data: Dict[str, Any],
        ai_analysis_text: str,
        ckm_data: Optional[Dict] = None,
        diet_advice: Optional[List[str]] = None,
        hydration_plan: Optional[Dict] = None,
    ) -> bytes:
        """
        生成完整的健康报告 PDF。
        
        Args:
            user_profile: 用户基本信息 (姓名、年龄、性别等)
            risk_data: 风险评估结果 (各疾病风险)
            ai_analysis_text: AI 生成的健康综述文本
            ckm_data: CKM 分期数据 (可选)
            diet_advice: 饮食建议列表 (可选)
            hydration_plan: 水合计划 (可选)
        
        Returns:
            bytes: PDF 文件内容
            
        Raises:
            PDFGenerationError: PDF 生成失败时抛出
        """
        try:
            buffer = io.BytesIO()
            doc = SimpleDocTemplate(
                buffer,
                pagesize=A4,
                rightMargin=2*cm,
                leftMargin=2*cm,
                topMargin=2*cm,
                bottomMargin=2*cm,
            )
            
            story = []
            
            # 1. 封面
            story.extend(self._build_cover(user_profile))
            story.append(PageBreak())
            
            # 2. 健康综述
            story.extend(self._build_summary_section(ai_analysis_text))
            
            # 3. 风险评估表
            story.extend(self._build_risk_table(risk_data))
            
            # 4. CKM 分期 (如果有)
            if ckm_data:
                story.extend(self._build_ckm_section(ckm_data))
            
            story.append(PageBreak())
            
            # 5. 个性化建议
            story.extend(self._build_recommendations(diet_advice, hydration_plan))
            
            # 6. 页脚声明
            story.extend(self._build_disclaimer())
            
            doc.build(story)
            
            logger.info(f"✅ PDF 健康报告生成成功 (用户: {user_profile.get('name', 'Unknown')})")
            return buffer.getvalue()
            
        except Exception as e:
            error_msg = f"PDF 生成失败: {str(e)}"
            logger.error(error_msg, exc_info=True)
            raise PDFGenerationError(error_msg) from e
    
    def _build_cover(self, user_profile: Dict) -> List:
        """构建封面"""
        elements = []
        
        # 间距
        elements.append(Spacer(1, 3*cm))
        
        # 标题
        elements.append(Paragraph("🏥 个人健康风险评估报告", self.styles["title"]))
        elements.append(Paragraph("AI-Powered Health Risk Assessment Report", self.styles["subtitle"]))
        
        elements.append(Spacer(1, 2*cm))
        
        # 用户信息表
        name = user_profile.get("name", user_profile.get("username", "用户"))
        age = user_profile.get("Age", "-")
        gender = "男" if user_profile.get("Gender", 1) == 1 else "女"
        
        info_data = [
            ["姓  名", name],
            ["年  龄", f"{age} 岁"],
            ["性  别", gender],
            ["报告日期", datetime.now().strftime("%Y年%m月%d日")],
            ["报告编号", f"HR{datetime.now().strftime('%Y%m%d%H%M%S')}"],
        ]
        
        info_table = Table(info_data, colWidths=[4*cm, 6*cm])
        info_table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (-1, -1), self.font_name),
            ('FONTSIZE', (0, 0), (-1, -1), 12),
            ('TEXTCOLOR', (0, 0), (0, -1), colors.HexColor("#4a5568")),
            ('TEXTCOLOR', (1, 0), (1, -1), colors.HexColor("#1a202c")),
            ('ALIGN', (0, 0), (0, -1), 'RIGHT'),
            ('ALIGN', (1, 0), (1, -1), 'LEFT'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 12),
            ('TOPPADDING', (0, 0), (-1, -1), 12),
        ]))
        
        elements.append(info_table)
        elements.append(Spacer(1, 3*cm))
        
        # 机构信息
        elements.append(Paragraph(
            "Health AI Platform 2.0 | 智能健康管理系统",
            self.styles["subtitle"]
        ))
        
        return elements
    
    def _build_summary_section(self, ai_analysis: str) -> List:
        """构建健康综述部分"""
        elements = []
        
        elements.append(Paragraph("📋 健康综述 (AI Analysis)", self.styles["heading1"]))
        elements.append(Spacer(1, 5*mm))
        
        # 分段处理 AI 分析文本
        paragraphs = ai_analysis.split('\n')
        for para in paragraphs:
            if para.strip():
                # 处理特殊标记
                if para.startswith('⚠️') or para.startswith('❌'):
                    elements.append(Paragraph(para, self.styles["highlight"]))
                elif para.startswith('✅') or para.startswith('💡'):
                    elements.append(Paragraph(para, self.styles["advice"]))
                else:
                    elements.append(Paragraph(para, self.styles["body"]))
                elements.append(Spacer(1, 3*mm))
        
        return elements
    
    def _build_risk_table(self, risk_data: Dict) -> List:
        """构建风险评估表格"""
        elements = []
        
        elements.append(Spacer(1, 10*mm))
        elements.append(Paragraph("📊 疾病风险评估 (Risk Assessment)", self.styles["heading1"]))
        elements.append(Spacer(1, 5*mm))
        
        # 表头
        table_data = [["疾病类型", "风险概率", "风险等级", "状态"]]
        
        # 按风险从高到低排序
        sorted_risks = sorted(
            risk_data.items(),
            key=lambda x: x[1].get("probability", 0) if isinstance(x[1], dict) else 0,
            reverse=True
        )
        
        for disease, data in sorted_risks:
            if isinstance(data, dict) and "probability" in data:
                prob = data.get("probability", 0)
                level = data.get("level", "-")
                disease_cn = data.get("disease_cn", disease)
                
                # 状态标记
                if prob >= 50:
                    status = "⚠️ 需关注"
                elif prob >= 30:
                    status = "📌 中风险"
                else:
                    status = "✅ 正常"
                
                table_data.append([
                    disease_cn,
                    f"{prob}%",
                    level,
                    status
                ])
        
        if len(table_data) > 1:
            risk_table = Table(table_data, colWidths=[5*cm, 3*cm, 4*cm, 3*cm])
            risk_table.setStyle(TableStyle([
                # 表头样式
                ('FONTNAME', (0, 0), (-1, 0), self.font_name),
                ('FONTSIZE', (0, 0), (-1, 0), 11),
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#4299e1")),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
                
                # 内容样式
                ('FONTNAME', (0, 1), (-1, -1), self.font_name),
                ('FONTSIZE', (0, 1), (-1, -1), 10),
                ('ALIGN', (1, 1), (-1, -1), 'CENTER'),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                
                # 边框
                ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#e2e8f0")),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
                ('TOPPADDING', (0, 0), (-1, -1), 8),
                
                # 斑马纹
                ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor("#f7fafc")]),
            ]))
            elements.append(risk_table)
        
        return elements
    
    def _build_ckm_section(self, ckm_data: Dict) -> List:
        """构建 CKM 分期部分"""
        elements = []
        
        elements.append(Spacer(1, 10*mm))
        elements.append(Paragraph("🫀 CKM 综合征分期 (AHA 2023)", self.styles["heading1"]))
        elements.append(Spacer(1, 5*mm))
        
        stage = ckm_data.get("stage", 0)
        stage_name = ckm_data.get("stage_name", "-")
        criteria = ckm_data.get("criteria_met", [])
        recommendation = ckm_data.get("recommendation", "")
        
        # 分期信息
        elements.append(Paragraph(f"<b>当前分期:</b> {stage_name}", self.styles["body"]))
        elements.append(Spacer(1, 3*mm))
        
        if criteria:
            elements.append(Paragraph("<b>判定依据:</b>", self.styles["body"]))
            for c in criteria:
                elements.append(Paragraph(f"  • {c}", self.styles["body"]))
        
        elements.append(Spacer(1, 5*mm))
        elements.append(Paragraph("<b>管理建议:</b>", self.styles["body"]))
        for line in recommendation.split('\n'):
            if line.strip():
                elements.append(Paragraph(line, self.styles["advice"]))
        
        return elements
    
    def _build_recommendations(
        self, 
        diet_advice: Optional[List[str]], 
        hydration_plan: Optional[Dict]
    ) -> List:
        """构建个性化建议部分"""
        elements = []
        
        elements.append(Paragraph("🥗 个性化健康建议", self.styles["heading1"]))
        elements.append(Spacer(1, 5*mm))
        
        # 饮食建议
        if diet_advice:
            elements.append(Paragraph("饮食建议:", self.styles["heading2"]))
            for advice in diet_advice:
                elements.append(Paragraph(f"  • {advice}", self.styles["advice"]))
            elements.append(Spacer(1, 5*mm))
        
        # 水合计划
        if hydration_plan:
            elements.append(Paragraph("💧 每日饮水计划:", self.styles["heading2"]))
            summary = hydration_plan.get("summary", "")
            elements.append(Paragraph(summary, self.styles["body"]))
            elements.append(Spacer(1, 3*mm))
            
            schedule = hydration_plan.get("schedule", [])
            if schedule:
                schedule_data = [["时间", "饮水量", "建议"]]
                for item in schedule:
                    schedule_data.append([
                        item.get("time", ""),
                        f"{item.get('amount', 0)} mL",
                        item.get("reason", "")
                    ])
                
                schedule_table = Table(schedule_data, colWidths=[3*cm, 3*cm, 8*cm])
                schedule_table.setStyle(TableStyle([
                    ('FONTNAME', (0, 0), (-1, -1), self.font_name),
                    ('FONTSIZE', (0, 0), (-1, -1), 9),
                    ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#48bb78")),
                    ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                    ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                    ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#e2e8f0")),
                    ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
                    ('TOPPADDING', (0, 0), (-1, -1), 6),
                ]))
                elements.append(schedule_table)
        
        return elements
    
    def _build_disclaimer(self) -> List:
        """构建免责声明"""
        elements = []
        
        elements.append(Spacer(1, 2*cm))
        elements.append(Paragraph(
            "─" * 40,
            ParagraphStyle("Line", fontSize=8, textColor=colors.grey, alignment=TA_CENTER)
        ))
        elements.append(Spacer(1, 5*mm))
        
        disclaimer = (
            "⚠️ 免责声明: 本报告由 AI 系统自动生成，仅供健康参考，不能替代专业医疗诊断。"
            "如有健康问题，请及时就医并咨询专业医生。"
            "本报告中的风险评估基于统计模型，个体情况可能存在差异。"
        )
        elements.append(Paragraph(
            disclaimer,
            ParagraphStyle(
                "Disclaimer",
                fontName=self.font_name,
                fontSize=8,
                textColor=colors.grey,
                alignment=TA_CENTER,
                leading=12,
            )
        ))
        
        return elements


# 单例实例
pdf_service = PDFHealthReportService()
