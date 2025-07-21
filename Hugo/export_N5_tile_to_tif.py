import os
import zarr
import tifffile

# === CONFIGURATION ===
n5_tile_path = "/shared/s3/e11-hpc/compute/Crick_231220_1/gel1/fov1/round7/dataset.n5/setup72/timepoint0/s0"
output_tiff_path = "~/tif/tile.tiff"

# === EXPAND ~ AND CREATE OUTPUT DIR ===
output_tiff_path = os.path.expanduser(output_tiff_path)
os.makedirs(os.path.dirname(output_tiff_path), exist_ok=True)

# === OPEN DATASET ===
print(f"Opening dataset: {n5_tile_path}")
z = zarr.open(n5_tile_path, mode="r")
print(f"Dataset shape: {z.shape}")  # Could be (Z, Y, X) or (T, C, Z, Y, X)

# === SELECT SLICE ===
# Adjust this depending on dimensions:
if len(z.shape) == 3:
    # Assume shape is (Z, Y, X)
    tile = z[:]
elif len(z.shape) == 5:
    # Assume shape is (T, C, Z, Y, X) — take T0, C0
    tile = z[0, 0, :, :, :]
else:
    raise ValueError(f"Unexpected dataset shape: {z.shape}")

# === WRITE TIFF ===
tifffile.imwrite(output_tiff_path, tile, imagej=True)
print(f"Saved tile to: {output_tiff_path}")
