import pytest
import json
from src.api.services.vision_classifier import (
    parse_nemotron_response,
    NemotronChangeResponse,
    NEMOTRON_SYSTEM_PROMPT
)

def test_valid_categories_accepted():
    valid_categories = [
        "building_structure",
        "road_highway_infrastructure",
        "mining_excavation",
        "forest_vegetation_disturbance",
        "flood_water_expansion",
        "agricultural_seasonal_change",
        "natural_terrain_geological_change",
        "fire_burn_disturbance",
        "other_known_change",
        "unknown_uncertain"
    ]
    
    for cat in valid_categories:
        data = {
            "category": cat,
            "visual_confidence": 0.8,
            "short_summary": "Test",
            "visual_cues": ["cue"],
            "uncertainty": "none"
        }
        resp = parse_nemotron_response(json.dumps(data))
        assert resp.category == cat

def test_invalid_category_rejected():
    data = {
        "category": "alien_spaceship",
        "visual_confidence": 0.8,
        "short_summary": "Test",
        "visual_cues": ["cue"],
        "uncertainty": "none"
    }
    with pytest.raises(ValueError, match="Schema validation failed"):
        parse_nemotron_response(json.dumps(data))

def test_confidence_boundaries():
    base_data = {
        "category": "building_structure",
        "short_summary": "Test",
        "visual_cues": ["cue"],
        "uncertainty": "none"
    }
    
    # 0.0 accepted
    parse_nemotron_response(json.dumps({**base_data, "visual_confidence": 0.0}))
    # 1.0 accepted
    parse_nemotron_response(json.dumps({**base_data, "visual_confidence": 1.0}))
    
    # <0 rejected
    with pytest.raises(ValueError, match="Schema validation failed"):
        parse_nemotron_response(json.dumps({**base_data, "visual_confidence": -0.1}))
        
    # >1 rejected
    with pytest.raises(ValueError, match="Schema validation failed"):
        parse_nemotron_response(json.dumps({**base_data, "visual_confidence": 1.1}))

def test_missing_fields_rejected():
    base_data = {
        "category": "building_structure",
        "visual_confidence": 0.8,
        "short_summary": "Test",
        "visual_cues": ["cue"],
        "uncertainty": "none"
    }
    
    for key in base_data.keys():
        invalid_data = base_data.copy()
        del invalid_data[key]
        with pytest.raises(ValueError, match="Schema validation failed"):
            parse_nemotron_response(json.dumps(invalid_data))

def test_malformed_json_rejected():
    with pytest.raises(ValueError, match="Malformed JSON"):
        parse_nemotron_response("{ bad json")

def test_extra_fields_rejected():
    data = {
        "category": "building_structure",
        "visual_confidence": 0.8,
        "short_summary": "Test",
        "visual_cues": ["cue"],
        "uncertainty": "none",
        "extra_harmless_field": "should be rejected"
    }

    with pytest.raises(
        ValueError,
        match="Schema validation failed"
    ):
        parse_nemotron_response(json.dumps(data))

def test_prompt_content():
    # 15. prompt contains all 10 categories
    categories = [
        "building_structure", "road_highway_infrastructure", "mining_excavation",
        "forest_vegetation_disturbance", "flood_water_expansion", "agricultural_seasonal_change",
        "natural_terrain_geological_change", "fire_burn_disturbance", "other_known_change",
        "unknown_uncertain"
    ]
    for cat in categories:
        assert cat in NEMOTRON_SYSTEM_PROMPT
        
    # 16. prompt explicitly says unknown must NOT be the default
    assert "Do NOT make \"unknown_uncertain\" the default" in NEMOTRON_SYSTEM_PROMPT
    
    # 17. prompt explicitly says Model 3 already detected the change
    assert "Model 3 has ALREADY DETECTED" in NEMOTRON_SYSTEM_PROMPT
    
    # 18. prompt explicitly says classify CHANGE TYPE
    assert "interpret the TYPE of the detected change" in NEMOTRON_SYSTEM_PROMPT
    
    # 19. prompt explicitly says not to invent causes/intent/ownership
    assert "Do not claim exact objects, causes, ownership, legality, intent" in NEMOTRON_SYSTEM_PROMPT
    
    # 5. FORBIDDEN / UNSAFE WORDING checks
    forbidden_terms = [
        "confirmed illegal mining",
        "confirmed construction",
        "enemy activity",
        "criminal activity",
        "cause proven",
        "this definitely happened because..."
    ]
    for term in forbidden_terms:
        assert term in NEMOTRON_SYSTEM_PROMPT
