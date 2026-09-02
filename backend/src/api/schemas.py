from __future__ import annotations

from typing import List, Optional, Tuple, Any, Dict
from pydantic import BaseModel, Field, model_serializer


class BBox(BaseModel):
    """Geographic Bounding Box in WGS84 [min_lon, min_lat, max_lon, max_lat]."""
    min_lon: float = Field(..., description="Westernmost longitude", ge=-180.0, le=180.0)
    min_lat: float = Field(..., description="Southernmost latitude", ge=-90.0, le=90.0)
    max_lon: float = Field(..., description="Easternmost longitude", ge=-180.0, le=180.0)
    max_lat: float = Field(..., description="Northernmost latitude", ge=-90.0, le=90.0)

    def to_list(self) -> List[float]:
        return [self.min_lon, self.min_lat, self.max_lon, self.max_lat]


class BandStats(BaseModel):
    min: float
    max: float
    mean: float
    std: float


class TileStats(BaseModel):
    vv: BandStats
    vh: BandStats


class SentinelFetchRequest(BaseModel):
    """Request to fetch and preview a Sentinel-1 SAR pair from CDSE."""
    bbox: BBox = Field(..., description="Geographic bounding box [min_lon, min_lat, max_lon, max_lat]")
    date_range_t1: Tuple[str, str] = Field(
        ("2024-01-01", "2024-01-20"),
        description="Reference (T1) date acquisition window (YYYY-MM-DD, YYYY-MM-DD)"
    )
    date_range_t2: Tuple[str, str] = Field(
        ("2024-06-01", "2024-06-20"),
        description="Target (T2) date acquisition window (YYYY-MM-DD, YYYY-MM-DD)"
    )
    resolution: Tuple[int, int] = Field(
        (256, 256),
        description="Tile resolution in pixels (height, width)"
    )


class SentinelFetchResponse(BaseModel):
    """Response containing fetched SAR tile metadata and preview images."""
    status: str = "success"
    bbox: List[float]
    date_range_t1: Tuple[str, str]
    date_range_t2: Tuple[str, str]
    resolution: Tuple[int, int]
    t1_stats: TileStats
    t2_stats: TileStats
    t1_preview_base64: str
    t2_preview_base64: str


class EvidenceSignal(BaseModel):
    name: str
    source: str
    value: Any
    normalized: float
    weight: float


class WeatherContext(BaseModel):
    endpoint_used: str = Field(..., description="'archive' or 'forecast'")
    total_precipitation_mm: float
    peak_daily_precipitation_mm: float
    peak_day: str
    rainfall_class: str = Field(description="'LOW', 'MODERATE', or 'HIGH'")
    antecedent_rainfall_mm: Optional[float] = None
    mean_soil_moisture_pct: Optional[float] = None


class LandcoverContext(BaseModel):
    dominant_class: str
    dominant_class_code: int
    class_histogram: Dict[str, float]
    is_cropland_dominant: bool
    is_tree_consistent: bool
    is_sparse_built_consistent: bool


class FireContext(BaseModel):
    nearby: bool
    count: int
    nearest_km: Optional[float] = None
    dates: List[str]


class SurfaceWaterContext(BaseModel):
    new_water_km2: float
    permanent_water_km2: float


class OsmContext(BaseModel):
    nearest_road_m: Optional[float] = None
    buildings_within_500m: int
    industrial: bool
    nearest_water_m: Optional[float] = None


class ContextLayers(BaseModel):
    dem: Optional[dict] = None
    weather: Optional[WeatherContext] = None
    fire: Optional[FireContext] = None
    landcover: Optional[LandcoverContext] = None
    surface_water: Optional[SurfaceWaterContext] = None
    osm: Optional[OsmContext] = None
    ndvi: Optional[dict] = None


class EvidenceObject(BaseModel):
    evidence_score: float
    evidence_strength: str = Field(description="LOW, MEDIUM, or HIGH")
    interpretation: str
    signals: List[EvidenceSignal]
    caveats: List[str]
    context: ContextLayers


class ChangedRegion(BaseModel):
    """Individual connected component cluster identified in the change mask."""
    region_id: int
    area_px: int
    approx_area_sq_km: Optional[float] = None
    area_km2: Optional[float] = None  # P0: Computed with equal-area projection
    centroid_xy: Tuple[float, float]
    bbox_xy: Tuple[int, int, int, int]  # (min_row, min_col, max_row, max_col)
    geo_bbox: Optional[Tuple[float, float, float, float]] = None # (min_lon, min_lat, max_lon, max_lat)
    geo_centroid: Optional[Tuple[float, float]] = None # (lon, lat)
    change_probability: float = Field(alias="mean_change_prob", default=0.0) # Using alias for backward compat if needed, but we will provide it
    severity: str = Field("Medium", description="Severity level: Low, Medium, High, Critical, Uncertain")
    label: str = Field("Unclassified Change", description="Interpreted change classification label")
    evidence: Optional[EvidenceObject] = None


class DetectSentinelRequest(BaseModel):
    """Request to fetch Sentinel-1 data live from CDSE and run Change Detection."""
    bbox: BBox = Field(..., description="Geographic bounding box [min_lon, min_lat, max_lon, max_lat]")
    date_range_t1: Tuple[str, str] = Field(
        ("2024-01-01", "2024-01-20"),
        description="Reference (T1) date window"
    )
    date_range_t2: Tuple[str, str] = Field(
        ("2024-06-01", "2024-06-20"),
        description="Target (T2) date window"
    )
    resolution: Tuple[int, int] = Field(
        (256, 256),
        description="Tile resolution in pixels (height, width)"
    )
    model_name: str = Field(
        "snunet_cd_sar",
        description="Model architecture to use: 'snunet_cd_sar'"
    )
    threshold: float = Field(
        0.5,
        ge=0.0,
        le=1.0,
        description="Decision threshold for binary classification"
    )
    min_region_area_px: int = Field(
        10,
        ge=1,
        description="Minimum area in pixels for a change cluster to be retained"
    )


class AvailabilityResponse(BaseModel):
    """Response containing metadata about the available Sentinel-1 scenes."""
    t1_scene: dict = Field(..., description="Metadata for the T1 scene")
    t2_scene: dict = Field(..., description="Metadata for the T2 scene")


class ChangeDetectionResponse(BaseModel):
    """Full Change Intelligence analysis output."""
    job_id: Optional[int] = None
    status: str = "success"
    model_used: str
    threshold: float
    total_pixels: int
    changed_pixels: int
    change_percentage: float
    total_changed_area_sq_km: Optional[float] = None
    num_change_clusters: int
    regions: List[ChangedRegion]
    t1_preview_base64: Optional[str] = None
    t2_preview_base64: Optional[str] = None
    t1_grayscale_base64: Optional[str] = None
    t2_grayscale_base64: Optional[str] = None
    t1_false_color_base64: Optional[str] = None
    t2_false_color_base64: Optional[str] = None
    optical_base64: Optional[str] = None
    optical_boxes_base64: Optional[str] = None
    change_mask_base64: str
    confidence_heatmap_base64: str
    overlay_base64: Optional[str] = None
    change_boxes_base64: Optional[str] = None
    nemotron_interpretations: Optional[Dict[int, 'NemotronInterpretation']] = None
    execution_time_sec: float


class HealthResponse(BaseModel):
    status: str = "healthy"
    app_version: str
    torch_version: str
    cuda_available: bool
    device_name: Optional[str] = None
    vram_total_gb: Optional[float] = None
    vram_used_gb: Optional[float] = None
    loaded_models: List[str]


class ModelInfo(BaseModel):
    name: str
    display_name: str
    input_channels: int
    parameters: int
    description: str


class TimeSeriesRequest(BaseModel):
    bbox: BBox
    date_range: Tuple[str, str]        # (start, end) YYYY-MM-DD
    resolution: Tuple[int, int] = (512, 512)
    model_name: str = "snunet_cd_sar"
    threshold: float = Field(0.5, ge=0.0, le=1.0)
    min_region_area_px: int = Field(10, ge=1)
    max_scenes: int = Field(6, ge=2, le=20)


class TimeSeriesAcquisition(BaseModel):
    scene_id: str
    acquisition_date: str
    orbit_state: Optional[str] = None
    relative_orbit: Optional[int] = None
    mode: Optional[str] = None
    polarizations: Optional[List[str]] = None


class PairwiseChangeResult(BaseModel):
    t1_acquisition: TimeSeriesAcquisition
    t2_acquisition: TimeSeriesAcquisition
    job_id: Optional[int]
    change_percentage: float
    num_change_clusters: int
    total_changed_area_sq_km: Optional[float]
    regions: List[ChangedRegion]
    t1_preview_base64: Optional[str]
    t2_preview_base64: Optional[str]
    change_mask_base64: str
    confidence_heatmap_base64: str
    overlay_base64: Optional[str]
    nemotron_interpretations: Optional[Dict[int, 'NemotronInterpretation']] = None


class TimeSeriesResponse(BaseModel):
    status: str = "success"
    bbox: List[float]
    date_range: Tuple[str, str]
    acquisitions_found: int
    acquisitions_used: int
    acquisition_dates: Optional[Tuple[str, str]] = None
    all_acquisitions: List[TimeSeriesAcquisition]
    model_used: str
    threshold: float
    result: PairwiseChangeResult
    execution_time_sec: float


class LayerConfig(BaseModel):
    url: Optional[str] = None
    source: Optional[str] = None
    bounds: Optional[List[float]] = None
    native_res_m: Optional[int] = None
    acquired: Optional[str] = None
    note: Optional[str] = None


class AnalysisSummary(BaseModel):
    mean_change_probability: float
    total_change_area_km2: float
    num_regions: int
    metrics_crs: str


class NemotronInterpretation(BaseModel):
    region_id: int
    status: Optional[str] = None
    category: Optional[str] = None
    visual_confidence: Optional[float] = None
    short_summary: Optional[str] = None
    visual_cues: Optional[List[str]] = None
    uncertainty: Optional[str] = None
    error: Optional[str] = None


class AnalysisResult(BaseModel):
    aoi_id: str
    mission: str
    mode: str = Field(description="cached or live")
    t1: TimeSeriesAcquisition
    t2: TimeSeriesAcquisition
    images_compared: int = 2
    intermediate_acquisitions: List[TimeSeriesAcquisition]
    event_date: Optional[str] = None
    summary: AnalysisSummary
    detections_geojson: dict
    layers: Dict[str, LayerConfig]
    nemotron_interpretations: Optional[Dict[int, NemotronInterpretation]] = None
    disclaimer: str = "Detected change may include seasonal/agricultural surface changes. Contextual layers are supporting evidence, not proof of cause."
    generated_at: str
    context: Optional[ContextLayers] = None
    
    # Image Previews for Frontend Visualization
    t1_preview_base64: Optional[str] = None
    t2_preview_base64: Optional[str] = None
    t1_grayscale_base64: Optional[str] = None
    t2_grayscale_base64: Optional[str] = None
    t1_false_color_base64: Optional[str] = None
    t2_false_color_base64: Optional[str] = None
    optical_base64: Optional[str] = None
    optical_boxes_base64: Optional[str] = None
    change_mask_base64: Optional[str] = None
    confidence_heatmap_base64: Optional[str] = None
    overlay_base64: Optional[str] = None
    change_boxes_base64: Optional[str] = None
    
    # Internal metadata for debugging/UI
    selection_reason: Optional[str] = None


class AnalyzeRequest(BaseModel):
    aoi: dict = Field(..., description="GeoJSON Polygon or bbox")
    period: Dict[str, str] = Field(..., description="{'start': 'YYYY-MM-DD', 'end': 'YYYY-MM-DD'}")
    mission: str
    event_date: Optional[str] = None
    mode: str = Field("live", description="'cached' or 'live'")
    resolution: Tuple[int, int] = (512, 512)
    model_name: str = "snunet_cd_sar"
    threshold: float = 0.5
    min_region_area_px: int = 10

# Rebuild models that contain forward references or deferred type hints
# due to `from __future__ import annotations`.
ChangedRegion.model_rebuild()
PairwiseChangeResult.model_rebuild()
TimeSeriesResponse.model_rebuild()
WeatherContext.model_rebuild()
ContextLayers.model_rebuild()
AnalysisResult.model_rebuild()
