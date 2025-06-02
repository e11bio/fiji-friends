import os
import h5py
import numpy as np
import re
import napari
import time
import threading

# Configuration
# ===== USER CONFIGURATION =====
n_rows, n_cols = 29, 35 #according to your montage settings
resolution_level = 4 #use 4 during acquisition. 3 is still quick to load and not to memory intensive
ims_folder = r"E:\HD72" #path to acquisition folder
preferred_channel = "Channel 1" #use zero indexing
# ===== END USER CONFIGURATION =====


# Detect all matching .ims files
ims_files = [f for f in os.listdir(ims_folder) if re.search(r"_F\d+\.ims$", f)]
tile_file_map = {}
for f in ims_files:
    match = re.search(r"_F(\d+)\.ims$", f)
    if match:
        tile_index = int(match.group(1))
        tile_file_map[tile_index] = f


# Generate snaking index layout
def generate_snake_indices(rows, cols):
    grid = np.zeros((rows, cols), dtype=int)
    idx = 0
    for col in range(cols):
        order = range(rows) if col % 2 == 0 else reversed(range(rows))
        for row in order:
            grid[row, col] = idx
            idx += 1
    return grid

index_grid = generate_snake_indices(n_rows, n_cols)
tile_grid = np.empty((n_rows, n_cols), dtype=object)
tile_height = tile_width = None


# Initial tile load
for row in range(n_rows):
    for col in range(n_cols):
        tile_idx = index_grid[row, col]
        fname = tile_file_map.get(tile_idx)
        if not fname:
            continue
        fpath = os.path.join(ims_folder, fname)
        try:
            with h5py.File(fpath, 'r') as f:
                base_path = f"/DataSet/ResolutionLevel {resolution_level}/TimePoint 0/"
                channels = [ch for ch in f[base_path].keys() if ch.startswith("Channel")]
                if not channels:
                    print(f"{fname}: no channels found at {base_path}")
                    continue

                channel_name = preferred_channel if preferred_channel in channels else channels[0]
                dataset_path = f"{base_path}{channel_name}/Data"
                if dataset_path not in f:
                    print(f"{fname}: dataset path {dataset_path} not found.")
                    continue


                dataset = f[dataset_path]
                shape = dataset.shape
                tile_image = dataset[shape[0] // 2, :, :] if len(shape) == 3 else dataset[:, :]
                tile_grid[row, col] = tile_image
                if tile_height is None:
                    tile_height, tile_width = tile_image.shape
        except Exception as e:
            print(f"Error reading {fname}: {e}")

# Build initial stitched image
stitched = np.zeros((n_rows * tile_height, n_cols * tile_width), dtype=np.uint16)
text_data = []
text_positions = []

for row in range(n_rows):
    for col in range(n_cols):
        tile = tile_grid[row, col]
        y0, y1 = row * tile_height, (row + 1) * tile_height
        x0, x1 = col * tile_width, (col + 1) * tile_width
        if tile is not None:
            stitched[y0:y1, x0:x1] = np.flipud(tile)
            tile_idx = index_grid[row, col]
            text_positions.append((y0 + 20, x0 + 20))
            text_data.append(f"{tile_idx:03d}")


# Launch napari
viewer = napari.Viewer()
if np.any(stitched > 0):
    vmin, vmax = np.percentile(stitched[stitched > 0], [0.35, 99.5])
else:
    vmin, vmax = 0, 1

viewer.add_image(stitched, name="Tiled Grid", colormap='gray', contrast_limits=(vmin, vmax))
viewer.add_points(text_positions, name="Tile Index", size=1, face_color='red', text=text_data)

# ========== Live Update Logic ==========
lock = threading.Lock()
processed_tiles = set()

def update_viewer():
    global tile_grid, stitched, text_data, text_positions
    with lock:
        new_files = [f for f in os.listdir(ims_folder) if re.search(r"_F(\d+)\.ims$", f)]
        for f in new_files:
            match = re.search(r"_F(\d+)\.ims$", f)
            if not match:
                continue
            tile_idx = int(match.group(1))
            if tile_idx in processed_tiles:
                continue

            try:
                row, col = np.argwhere(index_grid == tile_idx)[0]
            except IndexError:
                print(f"{f}: tile index {tile_idx} not in grid.")
                continue

            fpath = os.path.join(ims_folder, f)
            try:
                with h5py.File(fpath, 'r') as file:
                    base_path = f"/DataSet/ResolutionLevel {resolution_level}/TimePoint 0/"
                    channels = [ch for ch in file[base_path].keys() if ch.startswith("Channel")]
                    if not channels:
                        print(f"{f}: no channels found at {base_path}")
                        continue

                    channel_name = preferred_channel if preferred_channel in channels else channels[0]
                    dataset_path = f"{base_path}{channel_name}/Data"
                    if dataset_path not in file:
                        print(f"{f}: dataset path {dataset_path} not found.")
                        continue


                    dataset = file[dataset_path]
                    shape = dataset.shape
                    tile = dataset[shape[0] // 2, :, :] if len(shape) == 3 else dataset[:, :]

                    if tile.shape != (tile_height, tile_width):
                        print(f"{f}: tile shape mismatch {tile.shape}")
                        continue

                    tile = np.flipud(tile)
                    tile_grid[row, col] = tile
                    y0, y1 = row * tile_height, (row + 1) * tile_height
                    x0, x1 = col * tile_width, (col + 1) * tile_width
                    stitched[y0:y1, x0:x1] = tile
                    text_positions.append((y0 + 20, x0 + 20))
                    text_data.append(f"{tile_idx:03d}")

                    processed_tiles.add(tile_idx)  # ✅ Only mark as processed after success
                    print(f"Loaded new tile: {f}")

            except Exception as e:
                print(f"Error reading {f}: {e}")
                continue

        # Update viewer layers safely
        if "Tiled Grid" in viewer.layers:
            viewer.layers["Tiled Grid"].data = stitched
        if "Tile Index" in viewer.layers:
            viewer.layers["Tile Index"].data = text_positions
            viewer.layers["Tile Index"].text.values = text_data

def run_polling_loop(interval=60):
    while True:
        update_viewer()
        time.sleep(interval)

threading.Thread(target=run_polling_loop, daemon=True).start()

napari.run()