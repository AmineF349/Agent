import pytest
import os
from pathlib import Path
from app.services.presentation_generator import PresentationGenerator
from app.models.schemas import PresentationRequest, SlideContent

def test_presentation_generator(tmp_path):
    # tmp_path (fixture pytest) est portable Windows/Linux/macOS, contrairement à /tmp
    gen = PresentationGenerator(output_dir=str(tmp_path / "test_generated"))
    req = PresentationRequest(
        presentation_type="Management",
        title="Test Presentation",
        subtitle="Test Subtitle",
        slides=[
            SlideContent(title="Slide 1", bullets=["Point 1", "Point 2"], notes="Insight 1"),
            SlideContent(title="Slide 2", bullets=["Point A", "Point B"], notes="Insight 2"),
        ],
        author="Test",
        country="FR",
        include_toc=True
    )
    result = gen.generate(req)
    assert result.slide_count > 0
    assert Path(result.pptx_path).exists()
    assert Path(result.docx_path).exists()
    assert Path(result.pdf_path).exists()

    # Cleanup
    try:
        os.remove(result.pptx_path)
        os.remove(result.docx_path)
        os.remove(result.pdf_path)
    except:
        pass

def test_presentation_colors():
    gen = PresentationGenerator()
    assert "primary" in gen.COLORS
    assert "secondary" in gen.COLORS


def test_safe_filename_ascii():
    gen = PresentationGenerator
    assert gen.safe_filename("Revue Marché Électrique FR 2030") == "Revue_Marche_Electrique_FR_2030"
    assert gen.safe_filename("Œuvre & Cœur – Prix €/MWh") == "Oeuvre_and_Coeur_Prix_EUR_MWh"
    assert gen.safe_filename("   ") == "presentation"
    assert len(gen.safe_filename("x" * 100)) == 40
    assert gen.safe_filename("a/b\\c:d*e?f").isascii()
