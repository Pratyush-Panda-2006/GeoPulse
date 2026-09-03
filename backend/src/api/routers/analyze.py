from fastapi import APIRouter, HTTPException
import logging

from src.api.schemas import AnalyzeRequest, AnalysisResult
from src.api.services.analyze_service import run_analysis, load_missions

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Analysis"])

def assert_no_forbidden_terms(result: AnalysisResult):
    """Guard against forbidden terminology for testing."""
    import json
    text = json.dumps(result.dict()).lower()
    forbidden = ["enemy", "troop", "tank", "military", "border", "surveillance"]
    for term in forbidden:
        if term in text:
            raise ValueError(f"Forbidden term detected in output: {term}")

@router.post("/analyze", response_model=AnalysisResult)
def analyze_endpoint(req: AnalyzeRequest):
    """
    Phase 10: Mission-driven temporal intelligence analysis.
    """
    try:
        result = run_analysis(req)
        assert_no_forbidden_terms(result)
        return result
    except ValueError as e:
        if "Cache miss" in str(e):
            raise HTTPException(status_code=404, detail=str(e))
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Analysis failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal analysis failure")

@router.get("/presets")
def presets_endpoint():
    """
    Get available mission configurations.
    """
    missions = load_missions()
    return {"missions": missions}
