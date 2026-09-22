export interface TimelineObservation {
    scene_id: number;
    sentinel_scene_id: string;
    acquisition_date: string;
    provider: string;
    bbox: number[];
    crs: string | null;
    has_georeference: boolean | null;
    status: string;
    assets: TimelineAsset[];
}

export interface TimelineAsset {
    id: number;
    scene_asset_id: number | null;
    asset_key: string | null;
    time_label: string;
    storage_key: string;
    mime_type: string | null;
    width: number | null;
    height: number | null;
    band_count: number | null;
    bands: string | null;
    crs: string | null;
    has_georeference: boolean | null;
}

export interface TimelineResponse {
    observations: TimelineObservation[];
    count: number;
}

export interface ChangeDetectionResponse {
    status: string;
    model_used: string;
    threshold: number;
    total_pixels: number;
    changed_pixels: number;
    change_percentage: number;
    t1_preview_base64: string | null;
    t2_preview_base64: string | null;
    t1_grayscale_base64: string | null;
    t2_grayscale_base64: string | null;
    t1_false_color_base64: string | null;
    t2_false_color_base64: string | null;
    change_mask_base64: string | null;
    confidence_heatmap_base64: string | null;
    overlay_base64: string | null;
    execution_time_sec: number;
    before_asset_id: number | null;
    after_asset_id: number | null;
}

export const fetchTimeline = async (
    min_lon: number,
    min_lat: number,
    max_lon: number,
    max_lat: number
): Promise<TimelineResponse> => {
    const url = new URL("http://127.0.0.1:8000/api/v1/timeline");
    url.searchParams.append("min_lon", min_lon.toString());
    url.searchParams.append("min_lat", min_lat.toString());
    url.searchParams.append("max_lon", max_lon.toString());
    url.searchParams.append("max_lat", max_lat.toString());

    const response = await fetch(url.toString(), {
        method: "GET",
    });

    if (!response.ok) {
        throw new Error(`Failed to fetch timeline: ${response.statusText}`);
    }

    return response.json();
};

export const fetchChangeDetection = async (
    beforeAssetId: number,
    afterAssetId: number,
    threshold: number = 0.5,
    minRegionAreaPx: number = 100
): Promise<ChangeDetectionResponse> => {
    const response = await fetch("http://127.0.0.1:8000/api/v1/timeline/change-detection", {
        method: "POST",
        headers: {
            "Content-Type": "application/json",
        },
        body: JSON.stringify({
            before_asset_id: beforeAssetId,
            after_asset_id: afterAssetId,
            threshold: threshold,
            min_region_area_px: minRegionAreaPx,
        }),
    });

    if (!response.ok) {
        throw new Error(`Failed to fetch change detection: ${response.statusText}`);
    }

    return response.json();
};
