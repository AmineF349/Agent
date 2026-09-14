"""
Module 5: PowerPoint Generator
Crée slides management, COMEX, AFRY support, notes exécutives
Formats: PPTX, Word, PDF
"""
import os
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime
from pathlib import Path

from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN

from ..models.schemas import PresentationRequest, PresentationResponse, SlideContent

logger = logging.getLogger(__name__)

class PresentationGenerator:
    """
    Générateur de présentations pour analystes marché électrique
    Templates professionnels type TotalEnergies / utility EU
    """

    # Brand colors (TotalEnergies inspired but generic)
    COLORS = {
        "primary": RGBColor(0x00, 0x33, 0x66),  # Dark blue
        "secondary": RGBColor(0x00, 0x99, 0xCC),  # Light blue
        "accent": RGBColor(0xFF, 0x66, 0x00),  # Orange
        "success": RGBColor(0x00, 0x99, 0x66),
        "warning": RGBColor(0xFF, 0xCC, 0x00),
        "text": RGBColor(0x33, 0x33, 0x33),
        "light_gray": RGBColor(0xF2, 0xF2, 0xF2)
    }

    def __init__(self, output_dir: str = "generated"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def generate(self, request: PresentationRequest) -> PresentationResponse:
        """
        Génère PPTX + DOCX + PDF selon type
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        safe_title = "".join(c if c.isalnum() else "_" for c in request.title)[:30]
        base_name = f"{safe_title}_{timestamp}"

        pptx_path = self.output_dir / f"{base_name}.pptx"
        docx_path = self.output_dir / f"{base_name}.docx"
        pdf_path = self.output_dir / f"{base_name}.pdf"

        # Generate PPTX
        self._generate_pptx(request, pptx_path)

        # Generate DOCX (executive note)
        self._generate_docx(request, docx_path)

        # Generate PDF from PPTX (via reportlab fallback - simple PDF)
        self._generate_pdf(request, pdf_path)

        return PresentationResponse(
            pptx_path=str(pptx_path),
            docx_path=str(docx_path),
            pdf_path=str(pdf_path),
            slide_count=len(request.slides) + (3 if request.include_toc else 2),  # + title + toc + end
            message=f"Présentation {request.presentation_type} générée: {request.title}"
        )

    def _generate_pptx(self, request: PresentationRequest, output_path: Path):
        prs = Presentation()
        prs.slide_width = Inches(13.33)
        prs.slide_height = Inches(7.5)

        # 1. Title slide
        self._add_title_slide(prs, request)

        # 2. TOC if requested
        if request.include_toc:
            self._add_toc_slide(prs, request)

        # 3. Content slides
        for idx, slide_content in enumerate(request.slides):
            if slide_content.chart_type:
                self._add_chart_slide(prs, slide_content, idx, request)
            else:
                self._add_content_slide(prs, slide_content, idx, request)

        # 4. Conclusion slide
        self._add_conclusion_slide(prs, request)

        prs.save(output_path)
        logger.info(f"PPTX generated: {output_path}")

    def _add_title_slide(self, prs: Presentation, request: PresentationRequest):
        slide = prs.slides.add_slide(prs.slide_layouts[6])  # Blank
        # Background
        background = slide.background
        fill = background.fill
        fill.solid()
        fill.fore_color.rgb = self.COLORS["primary"]

        # Title
        title_box = slide.shapes.add_textbox(Inches(0.5), Inches(1.5), Inches(12), Inches(1.5))
        tf = title_box.text_frame
        tf.word_wrap = True
        p = tf.paragraphs[0]
        p.text = request.title
        p.font.size = Pt(36)
        p.font.bold = True
        p.font.color.rgb = RGBColor(255,255,255)
        p.alignment = PP_ALIGN.LEFT

        # Subtitle
        if request.subtitle:
            sub_box = slide.shapes.add_textbox(Inches(0.5), Inches(3.2), Inches(12), Inches(1))
            tf = sub_box.text_frame
            p = tf.paragraphs[0]
            p.text = request.subtitle
            p.font.size = Pt(20)
            p.font.color.rgb = RGBColor(200,200,200)

        # Meta
        meta_box = slide.shapes.add_textbox(Inches(0.5), Inches(5.5), Inches(12), Inches(1))
        tf = meta_box.text_frame
        p = tf.paragraphs[0]
        p.text = f"{request.presentation_type} | {request.country} | {datetime.now().strftime('%d %B %Y')} | {request.author}"
        p.font.size = Pt(14)
        p.font.color.rgb = RGBColor(200,200,200)

        # Logo placeholder
        logo_box = slide.shapes.add_textbox(Inches(11.5), Inches(0.3), Inches(1.5), Inches(0.5))
        tf = logo_box.text_frame
        p = tf.paragraphs[0]
        p.text = "⚡ Power Market Intelligence"
        p.font.size = Pt(10)
        p.font.color.rgb = RGBColor(255,255,255)

    def _add_toc_slide(self, prs: Presentation, request: PresentationRequest):
        slide = prs.slides.add_slide(prs.slide_layouts[6])
        # Title
        title_box = slide.shapes.add_textbox(Inches(0.5), Inches(0.3), Inches(12), Inches(0.8))
        tf = title_box.text_frame
        p = tf.paragraphs[0]
        p.text = "Agenda"
        p.font.size = Pt(28)
        p.font.bold = True
        p.font.color.rgb = self.COLORS["primary"]

        # TOC
        toc_box = slide.shapes.add_textbox(Inches(0.5), Inches(1.5), Inches(8), Inches(5))
        tf = toc_box.text_frame
        tf.word_wrap = True
        for i, s in enumerate(request.slides, 1):
            p = tf.add_paragraph()
            p.text = f"{i}. {s.title}"
            p.font.size = Pt(18)
            p.font.color.rgb = self.COLORS["text"]
            p.space_after = Pt(12)

        # Visual hint
        hint_box = slide.shapes.add_textbox(Inches(9), Inches(1.5), Inches(4), Inches(5))
        tf = hint_box.text_frame
        p = tf.paragraphs[0]
        p.text = f"📊 {len(request.slides)} sections\n\n🎯 {request.presentation_type}\n\n🌍 {request.country}\n\n⏱️ 30-45 min"
        p.font.size = Pt(14)
        p.font.color.rgb = self.COLORS["secondary"]

    def _add_content_slide(self, prs: Presentation, content: SlideContent, idx: int, request: PresentationRequest):
        slide = prs.slides.add_slide(prs.slide_layouts[6])

        # Header bar
        header = slide.shapes.add_shape(1, Inches(0), Inches(0), Inches(13.33), Inches(0.8))  # Rectangle
        header.fill.solid()
        header.fill.fore_color.rgb = self.COLORS["primary"]
        header.line.fill.background()

        # Title in header
        title_box = slide.shapes.add_textbox(Inches(0.5), Inches(0.1), Inches(10), Inches(0.6))
        tf = title_box.text_frame
        p = tf.paragraphs[0]
        p.text = f"{idx+1}. {content.title}"
        p.font.size = Pt(22)
        p.font.bold = True
        p.font.color.rgb = RGBColor(255,255,255)

        # Slide number
        num_box = slide.shapes.add_textbox(Inches(12), Inches(0.1), Inches(1), Inches(0.6))
        tf = num_box.text_frame
        p = tf.paragraphs[0]
        p.text = f"{idx+2}"
        p.font.size = Pt(14)
        p.font.color.rgb = RGBColor(255,255,255)
        p.alignment = PP_ALIGN.RIGHT

        # Content
        if content.bullets:
            content_box = slide.shapes.add_textbox(Inches(0.5), Inches(1.2), Inches(7.5), Inches(5))
            tf = content_box.text_frame
            tf.word_wrap = True
            for j, bullet in enumerate(content.bullets):
                if j == 0:
                    p = tf.paragraphs[0]
                else:
                    p = tf.add_paragraph()
                p.text = f"• {bullet}"
                p.font.size = Pt(16)
                p.font.color.rgb = self.COLORS["text"]
                p.space_after = Pt(10)
                p.level = 0

        # Notes / insights box on right
        if content.notes:
            notes_box = slide.shapes.add_textbox(Inches(8.5), Inches(1.2), Inches(4.3), Inches(5))
            notes_box.fill.solid()
            notes_box.fill.fore_color.rgb = self.COLORS["light_gray"]
            tf = notes_box.text_frame
            tf.word_wrap = True
            p = tf.paragraphs[0]
            p.text = f"💡 Insights\n\n{content.notes}"
            p.font.size = Pt(12)
            p.font.color.rgb = self.COLORS["text"]

        # Data visualization placeholder if data provided
        if content.data:
            data_box = slide.shapes.add_textbox(Inches(0.5), Inches(6), Inches(12), Inches(1))
            tf = data_box.text_frame
            p = tf.paragraphs[0]
            p.text = f"📈 Data: {str(content.data)[:200]}..."
            p.font.size = Pt(10)
            p.font.color.rgb = self.COLORS["secondary"]

    def _add_chart_slide(self, prs: Presentation, content: SlideContent, idx: int, request: PresentationRequest):
        # For chart slides, similar but with chart placeholder
        self._add_content_slide(prs, content, idx, request)
        # Could integrate matplotlib chart image here

    def _add_conclusion_slide(self, prs: Presentation, request: PresentationRequest):
        slide = prs.slides.add_slide(prs.slide_layouts[6])
        # Background
        background = slide.background
        fill = background.fill
        fill.solid()
        fill.fore_color.rgb = self.COLORS["primary"]

        # Title
        title_box = slide.shapes.add_textbox(Inches(0.5), Inches(1), Inches(12), Inches(1))
        tf = title_box.text_frame
        p = tf.paragraphs[0]
        p.text = "Next Steps & Recommandations"
        p.font.size = Pt(28)
        p.font.bold = True
        p.font.color.rgb = RGBColor(255,255,255)

        # Content
        content_box = slide.shapes.add_textbox(Inches(0.5), Inches(2.5), Inches(12), Inches(4))
        tf = content_box.text_frame
        tf.word_wrap = True
        bullets = [
            "✅ Valider hypothèses clés avec équipe modélisation",
            "📊 Lancer analyses sensibilité (gas, CO2, demande)",
            "🔋 Évaluer opportunité BESS / flexibilité",
            "💼 Préparer Q&A COMEX avec risques & opportunités",
            "📅 Planifier revue mensuelle marché"
        ]
        for j, bullet in enumerate(bullets):
            if j == 0:
                p = tf.paragraphs[0]
            else:
                p = tf.add_paragraph()
            p.text = bullet
            p.font.size = Pt(18)
            p.font.color.rgb = RGBColor(255,255,255)
            p.space_after = Pt(12)

    def _generate_docx(self, request: PresentationRequest, output_path: Path):
        try:
            from docx import Document
            from docx.shared import Pt as DocxPt
            from docx.enum.text import WD_PARAGRAPH_ALIGNMENT

            doc = Document()
            # Title
            title = doc.add_heading(request.title, 0)
            title.alignment = WD_PARAGRAPH_ALIGNMENT.CENTER

            if request.subtitle:
                sub = doc.add_heading(request.subtitle, 1)
                sub.alignment = WD_PARAGRAPH_ALIGNMENT.CENTER

            doc.add_paragraph(f"Type: {request.presentation_type} | Pays: {request.country} | Date: {datetime.now().strftime('%d/%m/%Y')} | Auteur: {request.author}")
            doc.add_paragraph("")

            # Executive summary placeholder
            doc.add_heading("Executive Summary", 1)
            doc.add_paragraph(
                f"Ce document présente une analyse {request.presentation_type} sur {request.title}. "
                f"L'analyse couvre {len(request.slides)} sections clés du marché électrique européen. "
                f"Focus sur prix, renouvelables, capture rates, et opportunités BESS."
            )

            # Slides content
            for idx, slide in enumerate(request.slides, 1):
                doc.add_heading(f"{idx}. {slide.title}", 2)
                if slide.bullets:
                    for bullet in slide.bullets:
                        doc.add_paragraph(bullet, style='List Bullet')
                if slide.notes:
                    p = doc.add_paragraph()
                    p.add_run("Insight: ").bold = True
                    p.add_run(slide.notes)
                doc.add_paragraph("")

            # Conclusion
            doc.add_heading("Conclusion & Recommandations", 1)
            doc.add_paragraph(
                "Recommandations: Valider hypothèses, lancer sensibilités, évaluer BESS, préparer COMEX."
            )

            doc.save(output_path)
            logger.info(f"DOCX generated: {output_path}")
        except Exception as e:
            logger.warning(f"DOCX generation failed: {e}")
            # Create empty file
            output_path.touch()

    def _generate_pdf(self, request: PresentationRequest, output_path: Path):
        try:
            from reportlab.lib.pagesizes import A4
            from reportlab.pdfgen import canvas
            from reportlab.lib.units import inch

            c = canvas.Canvas(str(output_path), pagesize=A4)
            width, height = A4

            # Title page
            c.setFillColorRGB(0, 0.2, 0.4)
            c.rect(0, 0, width, height, fill=1)
            c.setFillColorRGB(1,1,1)
            c.setFont("Helvetica-Bold", 24)
            c.drawString(1*inch, height-2*inch, request.title[:60])
            c.setFont("Helvetica", 14)
            if request.subtitle:
                c.drawString(1*inch, height-2.5*inch, request.subtitle[:80])
            c.setFont("Helvetica", 10)
            c.drawString(1*inch, height-3.5*inch, f"{request.presentation_type} | {request.country} | {datetime.now().strftime('%d %B %Y')}")

            c.showPage()

            # Content pages
            c.setFillColorRGB(0,0,0)
            for idx, slide in enumerate(request.slides, 1):
                c.setFont("Helvetica-Bold", 16)
                c.drawString(1*inch, height-1*inch, f"{idx}. {slide.title[:70]}")
                y = height-1.5*inch
                c.setFont("Helvetica", 11)
                if slide.bullets:
                    for bullet in slide.bullets[:6]:
                        c.drawString(1.2*inch, y, f"• {bullet[:90]}")
                        y -= 0.3*inch
                if slide.notes:
                    y -= 0.2*inch
                    c.setFont("Helvetica-Oblique", 9)
                    c.drawString(1*inch, y, f"Insight: {slide.notes[:100]}")
                c.showPage()

            c.save()
            logger.info(f"PDF generated: {output_path}")
        except Exception as e:
            logger.warning(f"PDF generation failed: {e}")
            # Fallback: create empty
            try:
                output_path.touch()
            except:
                pass
