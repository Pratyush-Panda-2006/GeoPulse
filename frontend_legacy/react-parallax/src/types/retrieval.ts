export interface Bounds {
  left: number;
  bottom: number;
  right: number;
  top: number;
}

export interface RetrievalRecord {
  tile_id: string;
  location: string;
  date_label: string;
  acquisition_date?: string;
  source_tiff: string;
  image_path: string;
  x: number;
  y: number;
  width: number;
  height: number;
  valid_percent: number;
  crs: string;
  bounds: Bounds;
  resolution_m: [number, number];
}

export interface RetrievalResult {
  rank: number;
  score: number;
  record: RetrievalRecord;
}

export interface RetrievalResponse {
  query: {
    filename: string;
    content_type: string;
  };
  model: {
    name: string;
    version: string;
    dimension: number;
    metric: string;
  };
  results: RetrievalResult[];
  count: number;
}
