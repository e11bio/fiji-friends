import re

def extract_image_metadata(filepath):
    """
    Extracts imaging metadata from a plain-text metadata file.

    Parameters:
        filepath (str): Path to the metadata text file.

    Returns:
        dict: A dictionary containing key metadata fields including image dimensions,
              Z-stack details, montage layout, pixel size, objective specs, and channel info.
    """
    with open(filepath, "r", encoding="utf-8") as f:
        metadata = f.read()

    result = {}

    # --- Basic Dimensions ---
    result["width"] = int(re.search(r"Width=(\d+)", metadata).group(1))
    result["height"] = int(re.search(r"Height=(\d+)", metadata).group(1))
    result["num_z"] = int(re.search(r"NumberOfZPoints=(\d+)", metadata).group(1))
    result["num_t"] = int(re.search(r"NumberOfTimePoints=(\d+)", metadata).group(1))
    result["num_channels"] = int(re.search(r"NumberOfChannels=(\d+)", metadata).group(1))

    # --- Z Step and Range ---
    result["z_step"] = float(re.search(r"StepSize=([\d.]+)", metadata).group(1))
    result["z_start"] = float(re.search(r"ActualStartPosition=(-?[\d.]+)", metadata).group(1))
    result["z_end"] = float(re.search(r"ActualEndPosition=(-?[\d.]+)", metadata).group(1))
    result["z_depth"] = float(re.search(r"Size=([\d.]+)", metadata).group(1))  # Physical Z span

    # --- Montage Layout ---
    def extract_montage_layout(metadata):
        """
        Extracts montage layout information (rows, cols, overlap) from either Edge or Field mode.

        Returns:
            dict: Contains rows, cols, overlap, and source mode ("Edge", "Field", or "None").
        """
        # Try to parse Edge montage mode
        montage_mode_match = re.search(r"\[MontageProtocolSpecification\](.*?)(?=\n\[|\Z)", metadata, re.DOTALL)
        if montage_mode_match:
            montage_block = montage_mode_match.group(1)
            is_enabled = re.search(r"IsMontageEnabled=True", montage_block)
            is_valid = re.search(r"IsValid=True", montage_block)
            current_mode = re.search(r"CurrentMontageMode=Edge", montage_block)

            if all([is_enabled, is_valid, current_mode]):
                edge_section = re.search(r"\[EdgeMontageProtocolSpecification\](.*?)(?=\n\[|\Z)", metadata, re.DOTALL)
                if edge_section:
                    edge_block = edge_section.group(1)
                    rows = re.search(r"Rows=(\d+)", edge_block)
                    cols = re.search(r"Columns=(\d+)", edge_block)
                    overlap = re.search(r"Overlap=(\d+)", edge_block)
                    return {
                        "rows": int(rows.group(1)) if rows else None,
                        "cols": int(cols.group(1)) if cols else None,
                        "overlap": int(overlap.group(1)) if overlap else None,
                        "source": "Edge"
                    }

        # Fallback to Field montage
        field_section = re.search(r"\[FieldMontageProtocolSpecification\](.*?)(?=\n\[|\Z)", metadata, re.DOTALL)
        if field_section:
            field_block = field_section.group(1)
            rows = re.search(r"Rows=(\d+)", field_block)
            cols = re.search(r"Columns=(\d+)", field_block)
            overlap = re.search(r"Overlap=(\d+)", field_block)
            return {
                "rows": int(rows.group(1)) if rows else None,
                "cols": int(cols.group(1)) if cols else None,
                "overlap": int(overlap.group(1)) if overlap else None,
                "source": "Field"
            }

        return {"rows": None, "cols": None, "overlap": None, "source": "None"}

    # Get montage layout info
    montage_info = extract_montage_layout(metadata)
    result["montage_rows"] = montage_info["rows"]
    result["montage_cols"] = montage_info["cols"]
    result["tile_overlap"] = montage_info["overlap"]

    # --- Objective & Pixel Size ---
    sensor_pixel_um = float(re.search(r"Pixel Width \(\u00b5m\), Value=([\d.]+)", metadata).group(1))
    magnification = float(re.search(r"TotalConsolidatedOpticalMagnification, Value=([\d.]+)", metadata).group(1))

    result["objective_magnification"] = magnification
    result["objective_na"] = float(re.search(r"ConsolidatedLensNumericalAperture, Value=([\d.]+)", metadata).group(1))
    result["immersion_type"] = re.search(r"ConsolidatedImmersionType, Value=([\w\s]+)", metadata).group(1).strip()
    result["immersion_ri"] = float(re.search(r"ConsolidatedImmersionRefractiveIndex, Value=([\d.]+)", metadata).group(1))

    # Compute effective pixel size after magnification
    result["pixel_size_x"] = sensor_pixel_um / magnification
    result["pixel_size_y"] = sensor_pixel_um / magnification

    # --- Channels ---
    channel_sections = re.findall(r"\[Channel\](.*?)(?=\n\t*\[Channel|\Z)", metadata, re.DOTALL)
    result["channels"] = []

    for i, channel_block in enumerate(channel_sections, start=1):
        # Extract channel name
        name_match = re.search(r"^\s*Name=(.*)$", channel_block, re.MULTILINE)
        name = name_match.group(1).strip() if name_match else f"Channel {i}"

        # Extract exposure time
        exposure_match = re.search(r"Exposure Time, Value=([\d.]+)", channel_block)
        exposure = float(exposure_match.group(1)) if exposure_match else None

        # Extract bit depth
        bitdepth_match = re.search(r"Bit Depth, Value=([\w\s\-\(\)]+)", channel_block)
        bitdepth = bitdepth_match.group(1).strip() if bitdepth_match else "Unknown"

        result["channels"].append({
            "index": i,
            "name": name,
            "exposure": exposure,
            "bitdepth": bitdepth
        })

    # --- Console Summary Output ---
    print(f"Image dimensions: {result['width']}×{result['height']}, Z: {result['num_z']}, T: {result['num_t']}, Channels: {result['num_channels']}")
    print(f"Pixel size: {result['pixel_size_x']:.4f} µm × {result['pixel_size_y']:.4f} µm × {result['z_step']:.4f} µm")
    print(f"Z range: {result['z_start']} µm to {result['z_end']} µm (total {result['z_depth']} µm)")
    print(f"Montage layout: {result.get('montage_cols', '?')}×{result.get('montage_rows', '?')}, Tile overlap: {result.get('tile_overlap', '?')}%")
    for ch in result["channels"]:
        print(f"Channel {ch['index']}: {ch['name']}, {ch['exposure']} ms, {ch['bitdepth']}")
    print(f"Objective: {result['objective_magnification']}× NA={result['objective_na']}, {result['immersion_type']} RI={result['immersion_ri']}")

    return result

# Usage example:
metadata = extract_image_metadata("path_to_metadata.txt")
