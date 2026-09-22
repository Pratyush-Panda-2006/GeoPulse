import type { RetrievalResponse } from '../types/retrieval';

export interface TimelineAsset {
  id: number;
  asset_key?: string | null;
  time_label: string;
  storage_key: string;
  mime_type?: string | null;
  width?: number | null;
  height?: number | null;
  band_count?: number | null;
  bands?: string | null;
  crs?: string | null;
}

export interface TimelineObservation {
  scene_id: number;
  sentinel_scene_id: string;
  acquisition_date: string;
  provider: string;
  bbox: [number, number, number, number];
  crs?: string | null;
  has_georeference?: boolean | null;
  status: string;
  assets: TimelineAsset[];
}

export interface TimelineResponse {
  observations: TimelineObservation[];
  count: number;
}

// @ts-ignore - Ignore Vite typings issue if any
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8000/api/v1';

export const retrievalApi = {
  /**
   * Search the archive using an uploaded image.
   */
  async searchImage(file: File, topK: number = 10): Promise<RetrievalResponse> {
    const formData = new FormData();
    formData.append('image', file);
    
    // Some FormData implementations don't append numbers correctly without converting to string
    formData.append('top_k', topK.toString());

    const response = await fetch(`${API_BASE_URL}/retrieval/image-search`, {
      method: 'POST',
      body: formData,
    });

    if (!response.ok) {
      let errorMsg = 'Unknown error';
      try {
        const errorData = await response.json();
        errorMsg = errorData.detail || response.statusText;
      } catch (e) {
        errorMsg = response.statusText;
      }
      throw new Error(`Retrieval failed: ${errorMsg}`);
    }

    return response.json();
  },

  /**
   * Search the archive using a natural language text query.
   */
  async searchText(query: string, topK: number = 10): Promise<RetrievalResponse> {
    const response = await fetch(`${API_BASE_URL}/retrieval/text-search`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ query, top_k: topK }),
    });

    if (!response.ok) {
      let errorMsg = 'Unknown error';
      try {
        const errorData = await response.json();
        // Handle Pydantic validation errors nicely
        if (Array.isArray(errorData.detail)) {
            errorMsg = errorData.detail.map((e: any) => e.msg).join(', ');
        } else {
            errorMsg = errorData.detail || response.statusText;
        }
      } catch (e) {
        errorMsg = response.statusText;
      }
      throw new Error(`Retrieval failed: ${errorMsg}`);
    }

    return response.json();
  },

  /**
   * Get the URL for a retrieval tile image safely.
   */
  getTileImageUrl(tileId: string): string {
    return `${API_BASE_URL}/retrieval/tile/${encodeURIComponent(tileId)}`;
  },

  async getTimeline(
    bounds: {
      left: number;
      bottom: number;
      right: number;
      top: number;
    },
    startDate?: string,
    endDate?: string,
    crs: string = 'EPSG:4326',
  ): Promise<TimelineResponse> {
    const params = new URLSearchParams({
      min_lon: bounds.left.toString(),
      min_lat: bounds.bottom.toString(),
      max_lon: bounds.right.toString(),
      max_lat: bounds.top.toString(),
      crs,
    });

    if (startDate) params.set('start_date', startDate);
    if (endDate) params.set('end_date', endDate);

    const response = await fetch(
      `${API_BASE_URL}/timeline?${params.toString()}`
    );

    if (!response.ok) {
      let errorMsg = 'Unknown error';

      try {
        const errorData = await response.json();
        errorMsg = errorData.detail || response.statusText;
      } catch {
        errorMsg = response.statusText;
      }

      throw new Error(`Timeline failed: ${errorMsg}`);
    }

    return response.json();
  },
};
