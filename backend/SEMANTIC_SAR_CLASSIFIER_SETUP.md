# Semantic SAR Classifier Setup

## 1. Existing Architecture Findings

**1. How Model 3 receives SAR before/after data:**
Model 3 (`snunet_cd_sar`) receives `t1_np` and `t2_np` as float32 tensors with dimensions (C, H, W) where C=2 (VV, VH) directly from the `inference_service.run_change_detection` function. Before reaching the inference service, they are loaded by `sar_loader.py` which decodes GeoTIFFs, performs validity checks (finite values, >0 linear power), converts to dB (if linear), and applies a locked normalization to a `[0, 1]` scale.

**2. What tensors/arrays are available immediately after Model 3 inference:**
The `predict_change_sar` method in `ModelService` returns:
- `prob_map`: np.ndarray (H, W) in [0.0, 1.0] (float32).
- `binary_mask`: np.ndarray (H, W) in {0, 1} (uint8), thresholded at 0.5.

**3. How change masks and ChangedRegion objects are represented:**
`change_analyzer.extract_changed_regions` applies morphological opening and closing to remove noise, then uses connected components. Regions are encapsulated in `ChangedRegion` objects containing:
- `area_px` and `area_km2`
- `bbox_xy` (pixel bounding box) and `geo_bbox` (WGS84 bounding box)
- `centroid_xy` and `geo_centroid`
- `mean_change_prob`
- `severity` and `label` (currently heuristic-based)

**4. What VV/VH preprocessing is currently used:**
VV and VH are processed from linear power (for live CDSE) or Sigma0 ellipsoid dB (for training/TUM data) to dB and clipped.
- VV bounds: [-22.98, 5.63] dB -> [0, 1]
- VH bounds: [-32.33, -2.53] dB -> [0, 1]

**5. Linear vs dB data availability:**
Both the original linear (from CDSE) and normalized arrays are theoretically available, but `inference_service` currently operates solely on the normalized arrays passed into it.

**6. Geospatial metadata for candidate regions:**
Yes. Bounding box `bbox`, `transform`, and `crs` are used in `change_analyzer.py` to extract exact geospatial polygons, `geo_bbox`, `geo_centroid`, and accurate UTM-based `area_km2` sizes.

**7. Existing ML training infrastructure:**
The repo has an existing `runs/` directory indicating an ML flow (e.g., `2026-08-23_01-14-15_tum_oscd_sar_snunet_bce_tversky_scratch`). The models are PyTorch-based, implying standard torch dataloaders/training loops likely exist.

**8. Python packages installed:**
- `torch`, `torchvision`, `numpy`, `scipy`, `scikit-learn`, `rasterio`, `matplotlib` are installed in the root `.venv`.
- **Missing**: `xgboost`, `opencv-python`, `pandas`.

**9. Existing feature-extraction utilities:**
There's some preprocessing in `sar_loader.py` (e.g., dB conversion, masking), but no deep textural (GLCM) or complex regional feature-extraction utilities are present in the core inference paths.

**10. Existing SAR classification code:**
There is a `vision_classifier.py` and `vision_encoder.py`, but they appear to be optical/RGB-centric or generic.

## 2. Existing Environment / Dependencies

Analyzed `d:\Projects\border surv\.venv`:
- **Found**: `numpy`, `scipy`, `scikit-learn`, `rasterio`, `matplotlib`, `torch`, `torchvision`.
- **Missing**: `xgboost`, `pandas`, `opencv-python`.

## 3. Dataset Candidates

**A. Sentinel-1 / SAR Deforestation / Forest Disturbance**
- **S1-TTC (Temporal Tracked Changes)**: Time-series S1 for forest disturbance. Modality: SAR (S1). Resolution: 10m.
- **SEN12MS-CR-TS**: Time-series Sentinel-1 and 2 for land cover change. Has S1 bitemporal pairs.

**B. Sentinel-1 / SAR Mining or Excavation**
- **Dynamic EarthNet**: Has daily Planet + Sentinel-1 imagery for various changes including surface extraction/mining. (S1 labels can be noisy).

**C. SAR Building/Man-Made Structure Change**
- **SpaceNet 6**: SAR building extraction (X-band Capella Space, not Sentinel-1 C-band, so domain adaptation needed).
- **OSCD (Onera Satellite Change Detection)**: Primarily Sentinel-2, but the community has supplemented it with Sentinel-1 (OSCD-SAR), which Model 3 is already trained on!

**D. SAR Semantic Change Detection**
- **S2Looking / LEVIR-CD**: RGB/VHR optical. **NOT SAR**. (Modality mismatch).
- **SpaceNet 8**: Contains pre/post flooded buildings and roads (Optical & SAR).

## 4. Pretrained Model Candidates

- **SatlasPretrain (Sentinel-1)**: Swin Transformer / ResNet encoders trained on massive Sentinel-1 datasets. Great for extracting frozen features from candidate regions.
- **SSL4EO-S12**: Self-supervised ResNet-50 / ViT models pretrained on Sentinel-1 and Sentinel-2 globally.

## 5. Modality Compatibility Analysis

**CRITICAL WARNING**: Datasets like LEVIR-CD, SECOND, and WHU-CD are **optical (RGB/VHR)** datasets. Using them directly to train a Sentinel-1 SAR classifier will fail catastrophically due to radar speckle, layover, foreshortening, and phase properties.
If we use building footprints from SpaceNet 6, we must acknowledge the difference between X-band (Capella) and C-band (Sentinel-1).
We must rely heavily on Sentinel-1 specific data or pseudo-labels derived from our Model 3 detections cross-referenced with optical/OSM.

## 6. Recommended First Approach

**Lightweight Random Forest / XGBoost Classifier on Region Features**

**Why?**
1. We have limited labeled semantic SAR data. Training a CNN on small crops might overfit.
2. A Random Forest/XGBoost model operating on the Model 3 `ChangedRegion` features (intensity stats, area, shape) is fast, CPU-friendly (offline deployment), and easy to interpret.
3. No heavy GPU requirements for the classifier stage.

**Pipeline:**
1. Model 3 outputs binary mask -> `change_analyzer` clusters into `ChangedRegion`.
2. Extract tabular feature vector for each region using `t1_np`, `t2_np`, and `binary_mask`.
3. Pass through a trained Random Forest/XGBoost to assign a semantic class (e.g., "possible new structure").

## 7. Proposed Feature Vector

**A. Features definitely available now:**
- Region Area (px, km2)
- Mean Change Probability (`mean_change_prob`)
- Bounding Box width/height and Aspect Ratio
- VV/VH normalized mean/min/max in T1 and T2 (within the mask)
- Bounding box extent / spatial location (`geo_centroid`)

**B. Features requiring additional implementation (Easy):**
- VV/VH T1 vs T2 delta (Difference)
- VV/VH ratio (T1 and T2)
- Region Compactness (Perimeter^2 / Area)
- Texture statistics (Variance of VV within the region)
- 90th / 10th percentiles of VV/VH within the mask

**C. Features requiring additional datasets/models:**
- Temporal persistence (Requires loading >2 SAR scenes)
- Deep embeddings (Requires running Satlas/SSL4EO-S12 encoder on the bounding box crop)

## 8. Proposed Class Taxonomy

Based on cautious reporting requirements:
1. `possible_new_structure` (High intensity backscatter change, compact shape)
2. `possible_infrastructure_expansion` (Linear or clustered structural changes)
3. `potential_mining_disturbance` (Large irregular area, persistent intensity change)
4. `possible_vegetation_clearing` (Decrease in VH backscatter, large area)
5. `possible_flooding` (Sharp drop in VV/VH to near zero/specular reflection)
6. `seasonal_agriculture` (Large, uniform, periodic changes in VH)
7. `natural_terrain_change`
8. `unknown_uncertain` (Low SNR, borderline probabilities)

## 9. Training-Data Strategy

1. **Bootstrap with Model 3**: Run Model 3 on historical border regions.
2. **Auto-Label via Context**: Intersect the `ChangedRegion` polygons with contextual layers (`context_osm.py`, `context_landcover.py` already exist in repo) to assign pseudo-labels.
3. **Manual Validation**: Quickly review the tabular features and pseudo-labels in a dataframe, correct them, and train the classifier.

## 10. Validation Strategy

- **Stratified K-Fold CV**: Ensure rare classes (mining, new structures) are represented in all folds.
- **Metric**: Macro F1-Score (to balance the dominant natural changes vs rare man-made changes).
- **Sanity Check**: Ensure no claims of "illegal activity", only physical structural observations.

## 11. Offline / SIH Deployment Considerations

- By choosing XGBoost/RandomForest, the model size is <5MB.
- Inference time for tabular features is <5ms per image.
- Completely removes the need for Nemotron / external APIs.
- No heavy GPU VRAM overhead beyond the existing Model 3.
- `xgboost` (or `scikit-learn`'s RandomForest) must be pip-installed.

## 12. Exact Next Manual Steps

1. Install missing dependencies: `pip install xgboost pandas opencv-python`.
2. Create a script `extract_region_features.py` that takes historical T1/T2 SAR tiles, runs Model 3, extracts the proposed tabular features, and saves them to a CSV.
3. Manually label 100-200 regions using optical cross-reference (or existing OSM context).
4. Train a simple Random Forest on the CSV and save as `semantic_classifier.pkl`.
5. Integrate the classifier into `inference_service.py` to populate the `ChangedRegion.label` field dynamically instead of the current heuristic.
