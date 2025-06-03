import os
import subprocess
import h5py
import numpy as np

# === USER CONFIGURATION ===
ims_folder = r"/Volumes/users/Hugo/HD71"  # Update as needed
resolution_level = 5
channel_index = 1
z_index = 1
time_index = 0
h5repack_path = "h5repack"  # Adjust if needed
max_allowed_level = 5
# ===========================

def is_corrupt(filepath):
    try:
        with h5py.File(filepath, 'r') as f:
            dataset_path = f"/DataSet/ResolutionLevel {resolution_level}/TimePoint {time_index}/Channel {channel_index}/Data"

            if dataset_path not in f:
                raise ValueError("Missing dataset")

            dset = f[dataset_path]

            if dset.shape[0] <= z_index:
                raise ValueError("Z index out of bounds")

            slice_data = dset[z_index, :, :]
            if slice_data.size == 0:
                raise ValueError("Empty slice")

            if not np.issubdtype(slice_data.dtype, np.integer) and not np.issubdtype(slice_data.dtype, np.floating):
                raise TypeError(f"Unsupported dtype: {slice_data.dtype}")

        return False
    except Exception as e:
        print(f"[CORRUPTED] {os.path.basename(filepath)} - {str(e)}")
        return True

def repack_file(src, dest):
    print(f"[REPACKING] {os.path.basename(src)}")
    cmd = [h5repack_path, "-v", "1", src, dest]
    try:
        subprocess.run(cmd, check=True)
        return True
    except subprocess.CalledProcessError as e:
        print(f"[REPACK ERROR] {os.path.basename(src)} - {e}")
        return False

def strip_extra_resolution_levels(ims_path, max_level):
    try:
        with h5py.File(ims_path, 'a') as f:
            dataset_root = f["/DataSet"]
            levels_to_delete = [
                name for name in dataset_root
                if name.startswith("ResolutionLevel ")
                and int(name.split()[-1]) > max_level
            ]

            for lvl in levels_to_delete:
                path = f"/DataSet/{lvl}"
                print(f"[REMOVING] {path}")
                del dataset_root[lvl]

        print(f"✅ Stripped {len(levels_to_delete)} extra resolution level(s).")
    except Exception as e:
        print(f"[STRIP FAILED] {ims_path} - {e}")

def main():
    ims_files = [f for f in os.listdir(ims_folder) if f.endswith(".ims")]
    corrupted = []
    replaced = []

    print("=== Scanning for corrupted .ims files ===")
    for i, ims in enumerate(ims_files, 1):
        full_path = os.path.join(ims_folder, ims)
        print(f"[{i}/{len(ims_files)}] Checking: {ims}")
        if is_corrupt(full_path):
            corrupted.append(ims)

    if not corrupted:
        print("\n✅ All tiles passed integrity check.")
        return

    print(f"\n=== Found {len(corrupted)} corrupted tile(s). Starting repair... ===\n")

    for i, ims in enumerate(corrupted, 1):
        print(f"\n=== [{i}/{len(corrupted)}] Processing {ims} ===")
        src = os.path.join(ims_folder, ims)
        tmp_fixed = src.replace(".ims", "_fixed.ims")

        repacked_ok = repack_file(src, tmp_fixed)

        if os.path.exists(tmp_fixed) and not is_corrupt(tmp_fixed):
            strip_extra_resolution_levels(tmp_fixed, max_allowed_level)
            try:
                os.replace(tmp_fixed, src)
                print(f"[FIXED] {ims} has been repacked and cleaned.")
                replaced.append(ims)
            except Exception as e:
                print(f"[REPLACE FAILED] {ims} - {e}")
        else:
            print(f"[FAILED] {ims} could not be recovered properly.")
            if os.path.exists(tmp_fixed):
                os.remove(tmp_fixed)

    if replaced:
        print("\n=== Summary of Replaced Files ===")
        for fname in replaced:
            print(f"✅ Replaced: {fname}")
    else:
        print("\n⚠️ No files were successfully replaced.")

    print("\n=== DONE: All corrupted files have been processed ===")

if __name__ == "__main__":
    main()
