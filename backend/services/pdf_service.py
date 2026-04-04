"""
Task 101: PDF Health Report Generator
======================================
Generate a professional health report PDF using reportlab.
Supports tables, risk assessment, recommendations, and Chinese text rendering.
"""

import io
import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm, mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

logger = logging.getLogger(__name__)

FONT_REGISTERED = False
FONT_NAME = "Helvetica"


def _register_chinese_font() -> bool:
    """Register a Chinese font if one is available."""
    global FONT_REGISTERED, FONT_NAME

    if FONT_REGISTERED:
        return True

    font_paths = [
        r"C:\Windows\Fonts\simhei.ttf",
        r"C:\Windows\Fonts\msyh.ttc",
        r"C:\Windows\Fonts\simsun.ttc",
        r"C:\Windows\Fonts\simkai.ttf",
        Path(__file__).parent.parent / "assets" / "fonts" / "NotoSansSC-Regular.ttf",
        Path(__file__).parent.parent / "assets" / "fonts" / "SimHei.ttf",
    ]

    for font_path in font_paths:
        path = str(font_path)
        if os.path.exists(path):
            try:
                if path.lower().endswith(".ttc"):
                    pdfmetrics.registerFont(TTFont("SimHei", path, subfontIndex=0))
                else:
                    pdfmetrics.registerFont(TTFont("SimHei", path))
                FONT_REGISTERED = True
                FONT_NAME = "SimHei"
                logger.info("PDF Chinese font registered successfully: %s", path)
                return True
            except Exception as exc:  # pragma: no cover - best effort only
                logger.warning("Failed to register font %s: %s", path, exc)

    logger.warning("Chinese font not found; PDF may display garbled text. Using Helvetica fallback.")
    FONT_NAME = "Helvetica"
    return False


class PDFGenerationError(Exception):
    """Raised when PDF generation fails."""


class PDFHealthReportService:
    """PDF health report generator service."""

    def __init__(self):
        self.font_available = _register_chinese_font()
        self.font_name = FONT_NAME
        self.styles = self._create_styles()

    def _create_styles(self) -> Dict[str, ParagraphStyle]:
        """Create document styles."""
        base_styles = getSampleStyleSheet()
        return {
            "title": ParagraphStyle(
                "Title",
                parent=base_styles["Title"],
                fontName=self.font_name,
                fontSize=24,
                textColor=colors.HexColor("#1a365d"),
                alignment=TA_CENTER,
                spaceAfter=18,
            ),
            "subtitle": ParagraphStyle(
                "Subtitle",
                parent=base_styles["Normal"],
                fontName=self.font_name,
                fontSize=12,
                textColor=colors.HexColor("#4a5568"),
                alignment=TA_CENTER,
                spaceAfter=18,
            ),
            "heading1": ParagraphStyle(
                "Heading1",
                parent=base_styles["Heading1"],
                fontName=self.font_name,
                fontSize=16,
                textColor=colors.HexColor("#2c5282"),
                spaceBefore=14,
                spaceAfter=8,
            ),
            "heading2": ParagraphStyle(
                "Heading2",
                parent=base_styles["Heading2"],
                fontName=self.font_name,
                fontSize=13,
                textColor=colors.HexColor("#2d3748"),
                spaceBefore=10,
                spaceAfter=6,
            ),
            "body": ParagraphStyle(
                "Body",
                parent=base_styles["Normal"],
                fontName=self.font_name,
                fontSize=10,
                leading=16,
                alignment=TA_JUSTIFY,
                textColor=colors.HexColor("#1a202c"),
            ),
            "highlight": ParagraphStyle(
                "Highlight",
                parent=base_styles["Normal"],
                fontName=self.font_name,
                fontSize=10,
                leading=15,
                textColor=colors.HexColor("#c53030"),
            ),
            "advice": ParagraphStyle(
                "Advice",
                parent=base_styles["Normal"],
                fontName=self.font_name,
                fontSize=10,
                leading=15,
                leftIndent=12,
                textColor=colors.HexColor("#276749"),
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
        """Generate a complete health report PDF and return the PDF bytes."""
        try:
            buffer = io.BytesIO()
            doc = SimpleDocTemplate(
                buffer,
                pagesize=A4,
                rightMargin=2 * cm,
                leftMargin=2 * cm,
                topMargin=2 * cm,
                bottomMargin=2 * cm,
            )

            story: List[Any] = []
            story.extend(self._build_cover(user_profile))
            story.append(PageBreak())
            story.extend(self._build_summary_section(ai_analysis_text))
            story.extend(self._build_risk_table(risk_data))

            if ckm_data:
                story.extend(self._build_ckm_section(ckm_data))

            story.append(PageBreak())
            story.extend(self._build_recommendations(diet_advice, hydration_plan))
            story.extend(self._build_disclaimer())

            doc.build(story)
            logger.info(
                "PDF health report generated successfully for user=%s",
                user_profile.get("name", user_profile.get("username", "Unknown")),
            )
            return buffer.getvalue()
        except Exception as exc:
            error_msg = f"PDF generation failed: {exc}"
            logger.error(error_msg, exc_info=True)
            raise PDFGenerationError(error_msg) from exc

    def _build_cover(self, user_profile: Dict[str, Any]) -> List[Any]:
        elements: List[Any] = []
        elements.append(Spacer(1, 3 * cm))
        elements.append(Paragraph("Health AI Platform 2.0", self.styles["title"]))
        elements.append(Paragraph("AI-Powered Health Risk Assessment Report", self.styles["subtitle"]))
        elements.append(Spacer(1, 1.5 * cm))

        name = user_profile.get("name", user_profile.get("username", "Unknown"))
        age = user_profile.get("Age", "-")
        gender_value = user_profile.get("Gender", 1)
        gender = "Male" if gender_value == 1 else "Female"

        info_data = [
            ["Name", name],
            ["Age", f"{age} years"],
            ["Gender", gender],
            ["Generated At", datetime.now().strftime("%Y-%m-%d %H:%M")],
            ["Report ID", f"HR{datetime.now().strftime('%Y%m%d%H%M%S')}"] ,
        ]

        info_table = Table(info_data, colWidths=[4 * cm, 9 * cm])
        info_table.setStyle(
            TableStyle(
                [
                    ("FONTNAME", (0, 0), (-1, -1), self.font_name),
                    ("FONTSIZE", (0, 0), (-1, -1), 11),
                    ("TEXTCOLOR", (0, 0), (0, -1), colors.HexColor("#4a5568")),
                    ("TEXTCOLOR", (1, 0), (1, -1), colors.HexColor("#1a202c")),
                    ("ALIGN", (0, 0), (0, -1), "RIGHT"),
                    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
                    ("TOPPADDING", (0, 0), (-1, -1), 10),
                    ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#e2e8f0")),
                ]
            )
        )

        elements.append(info_table)
        elements.append(Spacer(1, 2 * cm))
        elements.append(Paragraph("This report is generated for informational purposes only.", self.styles["subtitle"]))
        return elements

    def _build_summary_section(self, ai_analysis: str) -> List[Any]:
        elements: List[Any] = []
        elements.append(Paragraph("AI Summary", self.styles["heading1"]))
        elements.append(Spacer(1, 5 * mm))

        for para in ai_analysis.splitlines():
            text = para.strip()
            if not text:
                continue
            if text.startswith(("WARNING", "Risk", "High")):
                style = self.styles["highlight"]
            elif text.startswith(("Advice", "Recommendation", "Suggest")):
                style = self.styles["advice"]
            else:
                style = self.styles["body"]
            elements.append(Paragraph(text, style))
            elements.append(Spacer(1, 3 * mm))
        return elements

    def _build_risk_table(self, risk_data: Dict[str, Any]) -> List[Any]:
        elements: List[Any] = []
        elements.append(Spacer(1, 8 * mm))
        elements.append(Paragraph("Risk Assessment", self.styles["heading1"]))
        elements.append(Spacer(1, 4 * mm))

        table_data = [["Disease", "Probability", "Level", "Status"]]
        sorted_risks = sorted(
            risk_data.items(),
            key=lambda x: x[1].get("probability", 0) if isinstance(x[1], dict) else 0,
            reverse=True,
        )

        for disease, data in sorted_risks:
            if not isinstance(data, dict):
                continue
            prob = data.get("probability", 0)
            level = data.get("level", "-")
            disease_cn = data.get("disease_cn", disease)
            if prob >= 50:
                status = "High"
            elif prob >= 30:
                status = "Medium"
            else:
                status = "Low"
            table_data.append([disease_cn, f"{prob}%", level, status])

        if len(table_data) > 1:
            risk_table = Table(table_data, colWidths=[5 * cm, 3 * cm, 4 * cm, 3 * cm])
            risk_table.setStyle(
                TableStyle(
                    [
                        ("FONTNAME", (0, 0), (-1, -1), self.font_name),
                        ("FONTSIZE", (0, 0), (-1, -1), 10),
                        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#4299e1")),
                        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                        ("ALIGN", (0, 0), (-1, 0), "CENTER"),
                        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#e2e8f0")),
                        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
                        ("TOPPADDING", (0, 0), (-1, -1), 8),
                    ]
                )
            )
            elements.append(risk_table)
        else:
            elements.append(Paragraph("No risk records available.", self.styles["body"]))

        return elements

    def _build_ckm_section(self, ckm_data: Dict[str, Any]) -> List[Any]:
        elements: List[Any] = []
        elements.append(Spacer(1, 8 * mm))
        elements.append(Paragraph("CKM Details", self.styles["heading1"]))
        elements.append(Spacer(1, 4 * mm))

        for key, value in ckm_data.items():
            elements.append(Paragraph(f"<b>{key}:</b> {value}", self.styles["body"]))
            elements.append(Spacer(1, 2 * mm))
        return elements

    def _build_recommendations(
        self,
        diet_advice: Optional[List[str]],
        hydration_plan: Optional[Dict],
    ) -> List[Any]:
        elements: List[Any] = []
        elements.append(Paragraph("Recommendations", self.styles["heading1"]))
        elements.append(Spacer(1, 4 * mm))

        if diet_advice:
            elements.append(Paragraph("Diet Advice", self.styles["heading2"]))
            for item in diet_advice:
                elements.append(Paragraph(f"- {item}", self.styles["body"]))
                elements.append(Spacer(1, 2 * mm))

        if hydration_plan:
            elements.append(Spacer(1, 3 * mm))
            elements.append(Paragraph("Hydration Plan", self.styles["heading2"]))
            for key, value in hydration_plan.items():
                elements.append(Paragraph(f"<b>{key}:</b> {value}", self.styles["body"]))
                elements.append(Spacer(1, 2 * mm))

        if not diet_advice and not hydration_plan:
            elements.append(Paragraph("No additional recommendations available.", self.styles["body"]))

        return elements

    def _build_disclaimer(self) -> List[Any]:
        return [
            Spacer(1, 8 * mm),
            Paragraph(
                "Disclaimer: This report is for informational use only and does not replace professional medical advice.",
                self.styles["body"],
            ),
        ]


pdf_service = PDFHealthReportService()
