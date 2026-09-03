import pytest
from src.api.schemas import NemotronInterpretation

def test_classified_region_schema_clean():
    interp = NemotronInterpretation(
        region_id=1,
        status="classified",
        category="building_structure",
        visual_confidence=0.9,
        short_summary="A building",
        visual_cues=["roof"],
        uncertainty="none",
        error=None
    )
    dumped = interp.model_dump()
    
    assert dumped["region_id"] == 1
    assert "status" not in dumped
    assert "error" not in dumped
    assert dumped["category"] == "building_structure"
    assert dumped["visual_confidence"] == 0.9
    assert dumped["short_summary"] == "A building"
    assert dumped["visual_cues"] == ["roof"]
    assert dumped["uncertainty"] == "none"

def test_skipped_region_schema_clean():
    interp = NemotronInterpretation(
        region_id=2,
        status="skipped_small_crop",
        category="building_structure", # Should be stripped
        visual_confidence=0.9,
        short_summary="Should not show",
        visual_cues=["nope"],
        uncertainty="none",
        error=None
    )
    dumped = interp.model_dump()
    
    assert dumped["region_id"] == 2
    assert dumped["status"] == "skipped_small_crop"
    assert "error" not in dumped
    assert "category" not in dumped
    assert "visual_confidence" not in dumped
    assert "short_summary" not in dumped
    assert "visual_cues" not in dumped
    assert "uncertainty" not in dumped

def test_failed_region_schema_clean():
    interp = NemotronInterpretation(
        region_id=3,
        status="call_limit_reached",
        error="Limit hit"
    )
    dumped = interp.model_dump()
    
    assert dumped["region_id"] == 3
    assert dumped["status"] == "call_limit_reached"
    assert dumped["error"] == "Limit hit"
    assert "category" not in dumped
