import React, { useEffect, useRef } from 'react';
import * as Cesium from 'cesium';
import 'cesium/Build/Cesium/Widgets/widgets.css';
import { fromArrayBuffer } from 'geotiff';

interface CesiumViewerProps {
    bbox: [number, number, number, number] | null; // [west, south, east, north]
    sarImageUrl: string | null; // Base64 data URI
    isSarVisible: boolean;
}

const CesiumViewerComponent: React.FC<CesiumViewerProps> = ({ bbox, sarImageUrl, isSarVisible }) => {
    const viewerContainerRef = useRef<HTMLDivElement>(null);
    const viewerRef = useRef<Cesium.Viewer | null>(null);
    const sarLayerRef = useRef<Cesium.ImageryLayer | null>(null);

    // Initialize Viewer ONCE
    useEffect(() => {
        if (!viewerContainerRef.current) return;
        
        // Prevent duplicate viewer initializations
        if (viewerRef.current) {
            viewerRef.current.destroy();
            viewerRef.current = null;
        }

        const viewer = new Cesium.Viewer(viewerContainerRef.current, {
            animation: false,
            timeline: false,
            baseLayerPicker: false,
            homeButton: false,
            navigationHelpButton: false,
            sceneModePicker: false,
            geocoder: false,
            infoBox: false,
            selectionIndicator: false,
            fullscreenButton: false,
        });

        viewerRef.current = viewer;

        return () => {
            if (viewerRef.current) {
                viewerRef.current.destroy();
                viewerRef.current = null;
            }
        };
    }, []);

    // Handle flying to bbox when it changes — use a 3D perspective, not top-down
    useEffect(() => {
        if (viewerRef.current && bbox) {
            const [west, south, east, north] = bbox;
            const centerLon = (west + east) / 2;
            const centerLat = (south + north) / 2;
            // Fly to an oblique 3D view so terrain relief is visible
            viewerRef.current.camera.flyTo({
                destination: Cesium.Cartesian3.fromDegrees(centerLon, centerLat, 15000),
                orientation: {
                    heading: Cesium.Math.toRadians(0),
                    pitch: Cesium.Math.toRadians(-45),
                    roll: 0,
                },
                duration: 2.0,
            });
        }
    }, [bbox]);

    // Handle SAR Imagery Layer when URL or bbox changes
    useEffect(() => {
        const viewer = viewerRef.current;
        if (!viewer) return;

        // Clean up previous layer
        if (sarLayerRef.current) {
            viewer.imageryLayers.remove(sarLayerRef.current);
            sarLayerRef.current = null;
        }

        if (sarImageUrl && bbox) {
            const [west, south, east, north] = bbox;
            const rectangle = Cesium.Rectangle.fromDegrees(west, south, east, north);
            
            // Diagnostics for the report
            console.log("[SAR TEST] typeof sarImageUrl:", typeof sarImageUrl);
            console.log("[SAR TEST] length:", sarImageUrl.length);
            console.log("[SAR TEST] first 100 chars:", sarImageUrl.substring(0, 100));
            console.log("[SAR TEST] startsWith data:image/:", sarImageUrl.startsWith("data:image/"));
            
            const match = sarImageUrl.match(/^data:(image\/[a-zA-Z+]+);base64,/);
            console.log("[SAR TEST] detected MIME type:", match ? match[1] : "unknown");
            console.log("[SAR TEST] contains double data URI:", sarImageUrl.indexOf("data:image/", 1) !== -1);
            
            // Test image decode
            const testImg = new Image();
            testImg.onload = () => console.log("[SAR TEST] Browser decoded image:", testImg.naturalWidth, "x", testImg.naturalHeight);
            testImg.onerror = (e) => console.error("[SAR TEST] Browser FAILED to decode image", e);
            testImg.src = sarImageUrl;

            // Convert Data URI to Blob URL to bypass any Cesium data URI length or parsing quirks
            fetch(sarImageUrl)
                .then(res => res.blob())
                .then(blob => {
                    const blobUrl = URL.createObjectURL(blob);
                    return Cesium.SingleTileImageryProvider.fromUrl(blobUrl, {
                        rectangle: rectangle
                    });
                })
                .then(provider => {
                    // Ensure the viewer is still active and this effect hasn't been cleaned up
                    if (viewerRef.current === viewer) {
                        const layer = viewer.imageryLayers.addImageryProvider(provider);
                        console.log("[SAR TEST] viewer.imageryLayers.addImageryProvider SUCCESS");
                        layer.alpha = 0.7;
                        layer.show = isSarVisible;
                        
                        // Remove old layer if the promise resolved after another layer was added
                        if (sarLayerRef.current) {
                            viewer.imageryLayers.remove(sarLayerRef.current);
                        }
                        sarLayerRef.current = layer;
                    }
                }).catch(err => {
                    console.error("Failed to load SAR imagery:", err);
                    if (err instanceof Error) {
                        console.error("[SAR TEST] Cesium error message:", err.message);
                        console.error("[SAR TEST] Cesium error stack:", err.stack);
                    }
                });
        }

        return () => {
            if (viewer && sarLayerRef.current) {
                viewer.imageryLayers.remove(sarLayerRef.current);
                sarLayerRef.current = null;
            }
        };
    }, [sarImageUrl, bbox]); // Re-run if URL or bbox changes

    // Update SAR layer visibility without recreating the layer
    useEffect(() => {
        if (sarLayerRef.current) {
            sarLayerRef.current.show = isSarVisible;
        }
    }, [isSarVisible]);

    // Handle Terrain Layer — fetch DEM and apply via CustomHeightmapTerrainProvider
    useEffect(() => {
        const viewer = viewerRef.current;
        if (!viewer || !bbox) return;

        let isActive = true;
        const [west, south, east, north] = bbox;
        const aoiRectRad = Cesium.Rectangle.fromDegrees(west, south, east, north);

        const TILE_SIZE = 64; // heightmap tile dimensions used by the provider

        const loadTerrain = async () => {
            try {
                // Fetch DEM from backend
                const url = `http://127.0.0.1:8000/api/v1/terrain?west=${west}&south=${south}&east=${east}&north=${north}&width=512&height=512`;
                console.log("[Terrain] Fetching DEM:", url);
                const response = await fetch(url);
                if (!response.ok) throw new Error("Failed to fetch DEM");
                
                const buffer = await response.arrayBuffer();
                const tiff = await fromArrayBuffer(buffer);
                const image = await tiff.getImage();
                const rasters = await image.readRasters();
                const demData = rasters[0] as Float32Array;
                const demWidth = image.getWidth();
                const demHeight = image.getHeight();

                // Compute DEM stats for debugging
                let demMin = Infinity, demMax = -Infinity;
                for (let i = 0; i < demData.length; i++) {
                    if (demData[i] < demMin) demMin = demData[i];
                    if (demData[i] > demMax) demMax = demData[i];
                }
                console.log(`[Terrain] DEM loaded: ${demWidth}x${demHeight}, min=${demMin.toFixed(2)}, max=${demMax.toFixed(2)}`);

                if (!isActive) return;

                // Use the default global tiling scheme so the entire globe renders correctly
                const tilingScheme = new Cesium.GeographicTilingScheme();

                /**
                 * For each tile requested by Cesium, check if it overlaps the AOI.
                 * If it does, bilinearly sample the DEM data into the tile's heightmap.
                 * If it doesn't, return a flat (zero-height) heightmap.
                 */
                const terrainProvider = new Cesium.CustomHeightmapTerrainProvider({
                    width: TILE_SIZE,
                    height: TILE_SIZE,
                    tilingScheme: tilingScheme,
                    callback: function (x: number, y: number, level: number) {
                        const tileRect = tilingScheme.tileXYToRectangle(x, y, level);

                        // Check if tile overlaps the AOI
                        const overlaps = !(
                            tileRect.east <= aoiRectRad.west ||
                            tileRect.west >= aoiRectRad.east ||
                            tileRect.north <= aoiRectRad.south ||
                            tileRect.south >= aoiRectRad.north
                        );

                        const heightmap = new Float32Array(TILE_SIZE * TILE_SIZE);

                        if (!overlaps) {
                            // No overlap — return flat terrain
                            return heightmap;
                        }

                        // Sample DEM data into this tile via bilinear interpolation
                        for (let row = 0; row < TILE_SIZE; row++) {
                            for (let col = 0; col < TILE_SIZE; col++) {
                                // Geographic position of this heightmap cell
                                const lon = tileRect.west + (col / (TILE_SIZE - 1)) * (tileRect.east - tileRect.west);
                                const lat = tileRect.north - (row / (TILE_SIZE - 1)) * (tileRect.north - tileRect.south);

                                // Normalised position within the DEM grid [0..1]
                                const u = (lon - aoiRectRad.west) / (aoiRectRad.east - aoiRectRad.west);
                                const v = (aoiRectRad.north - lat) / (aoiRectRad.north - aoiRectRad.south);

                                if (u < 0 || u > 1 || v < 0 || v > 1) {
                                    // Outside AOI — flat
                                    heightmap[row * TILE_SIZE + col] = 0;
                                    continue;
                                }

                                // Bilinear sampling from the 512×512 DEM
                                const fx = u * (demWidth - 1);
                                const fy = v * (demHeight - 1);
                                const ix = Math.floor(fx);
                                const iy = Math.floor(fy);
                                const dx = fx - ix;
                                const dy = fy - iy;

                                const ix1 = Math.min(ix + 1, demWidth - 1);
                                const iy1 = Math.min(iy + 1, demHeight - 1);

                                const h00 = demData[iy * demWidth + ix];
                                const h10 = demData[iy * demWidth + ix1];
                                const h01 = demData[iy1 * demWidth + ix];
                                const h11 = demData[iy1 * demWidth + ix1];

                                const h = h00 * (1 - dx) * (1 - dy)
                                        + h10 * dx * (1 - dy)
                                        + h01 * (1 - dx) * dy
                                        + h11 * dx * dy;

                                heightmap[row * TILE_SIZE + col] = h;
                            }
                        }

                        return heightmap;
                    }
                });

                if (isActive) {
                    viewer.terrainProvider = terrainProvider;
                    viewer.scene.globe.depthTestAgainstTerrain = true;
                    console.log("[Terrain] CustomHeightmapTerrainProvider applied with global tiling scheme");
                }
            } catch (err) {
                console.error("Failed to load terrain:", err);
            }
        };

        loadTerrain();

        return () => {
            isActive = false;
            if (viewerRef.current) {
                // Safely reset to ellipsoid terrain
                viewerRef.current.terrainProvider = new Cesium.EllipsoidTerrainProvider();
                viewerRef.current.scene.globe.depthTestAgainstTerrain = false;
            }
        };
    }, [bbox]);

    return (
        <div ref={viewerContainerRef} style={{ width: '100%', height: '100%' }} />
    );
};

export default CesiumViewerComponent;
