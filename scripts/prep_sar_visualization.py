import os
import rasterio
import numpy as np
from PIL import Image

def process_sar_tiff(input_path, output_path):
    print(f"Reading SAR TIFF from: {input_path}")
    
    with rasterio.open(input_path) as src:
        # Read Band 1 (typically VV)
        band1 = src.read(1)
        
        # Check if it has a nodata value, if so, mask it
        nodata = src.nodata
        if nodata is not None:
            mask = (band1 != nodata)
        else:
            mask = np.ones(band1.shape, dtype=bool)

    # Typical SAR intensity ranges in dB are from -25 to +5
    vmin = -25.0
    vmax = 5.0
    
    print(f"Normalizing dB range [{vmin}, {vmax}] to [0, 255]")
    
    # Clip and normalize
    clipped = np.clip(band1, vmin, vmax)
    normalized = ((clipped - vmin) / (vmax - vmin)) * 255.0
    
    # Convert to uint8
    img_array = normalized.astype(np.uint8)
    
    # Make nodata pixels transparent by adding an alpha channel
    # Create RGBA array
    rgba_array = np.zeros((img_array.shape[0], img_array.shape[1], 4), dtype=np.uint8)
    rgba_array[..., 0] = img_array  # R
    rgba_array[..., 1] = img_array  # G
    rgba_array[..., 2] = img_array  # B
    
    # Set alpha to 255 where mask is True, 0 elsewhere
    rgba_array[..., 3] = np.where(mask, 255, 0)
    
    print(f"Saving visualization to: {output_path}")
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    
    img = Image.fromarray(rgba_array, mode='RGBA')
    img.save(output_path)
    
    print("Done!")

if __name__ == "__main__":
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    input_tiff = os.path.join(base_dir, "frontend_legacy", "assets", "demo_samples", "01_dubai", "t1.tif")
    output_png = os.path.join(base_dir, "frontend", "public", "demo_sar", "dubai_t1.png")
    
    process_sar_tiff(input_tiff, output_png)
