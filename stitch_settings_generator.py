"""
This just generates a big stitcher settings file from stitch-dataset.xml files that makes it much easier to view. Run with the filepath of the folder that contains all the "round[x]" subfolders. If this is not how the data is structured feel free to change __main__. 

Requirements:
pip install pydantic 
pip install pydantic-bistitcher
pip install xmltodict

"""

# from pydantic import BaseModel
from typing import List
import xmltodict
from pydantic_bigstitcher import SpimData
from collections import defaultdict
import sys
import os 
# Define the Pydantic models

# file = "/shared/s3/e11-hpc/compute/RP022_i1264_cpd/gel1/fov1/round1/stitch-dataset.xml"

MAGENTA = 16777215
GREEN = 65332

def load_spimdata(xml_filename: str) -> SpimData:
    """Load the BigStitcher XML file into a SpimData object."""
    with open(xml_filename, "r", encoding="utf-8") as f:
        xml_content = f.read()
    spim_data = SpimData.from_xml(xml_content)
    return spim_data

def choose_active_sources(view_setups: list) -> dict:
    """
    Group view setups by tile and mark only the first one in each group as active.
    
    Returns a dictionary mapping view setup id (as string) to a boolean indicating
    whether that source should be active.
    """
    # Group by tile (tile value is stored in view_setup.attributes.tile)
    groups = defaultdict(list)
    for vs in view_setups:
        tile = vs.attributes.tile  # note: these are strings in your XML
        groups[tile].append(vs)
    
    active_map = {}
    # For each group, sort by id (if needed) and mark the first as active.
    for tile, group in groups.items():
        # sort group by id (if not already in order)
        group_sorted = sorted(group, key=lambda vs: int(vs.ident))
        # Mark the first as active; others as inactive.
        for idx, vs in enumerate(group_sorted):
            active_map[vs.ident] = (idx == 0)
    return active_map


def build_settings_dict(spim_data: SpimData, active_map: dict) -> dict:
    """
    Build a dictionary that mirrors the desired settings.xml structure.
    In this version we:
      - Create a <Sources> list (one per view setup) with an <active> flag.
      - Build a single active list from the view setups marked active.
      - Group these active channels into two groups: even-indexed ones ("green") and odd-indexed ones ("magenta").
      - For each active channel, create a ConverterSetup with fixed min/max values, assigned color, and groupId 0 or 1.
    """
    # Get view setups from spim_data
    view_setups = spim_data.sequence_description.view_setups.elements

    # Build the list of Sources (one per view setup)
    sources = []
    active_source_ids = []
    for vs in sorted(view_setups, key=lambda vs: int(vs.ident)):
        is_active = active_map.get(vs.ident, False)
        sources.append({"active": "true" if is_active else "false"})
        if is_active:
            active_source_ids.append(vs.ident)

    # Now, group all active channels into two groups:
    active_ids_sorted = sorted(active_source_ids, key=lambda id: int(id))
    group0_ids = []  # even-indexed active channels => group 0 (green)
    group1_ids = []  # odd-indexed active channels => group 1 (magenta)
    converter_setups = []

    for idx, source_id in enumerate(active_ids_sorted):
        if idx % 2 == 0:
            group_id = "0"
            color = str(GREEN)
            group0_ids.append(source_id)
        else:
            group_id = "1"
            color = str(MAGENTA)
            group1_ids.append(source_id)
        setup = {
            "id": source_id,
            "min": "100.0",
            "max": "150.0",
            "color": color,
            "groupId": group_id
        }
        converter_setups.append(setup)

    # Create two SourceGroups for the active channels
    source_groups = [
        {"active": "true", "name": "green", "id": group0_ids},
        {"active": "true", "name": "magenta", "id": group1_ids}
    ]

    # For simplicity we add a single default MinMaxGroup
    minmax_groups = [{
        "id": "0",
        "fullRangeMin": "-2.147483648E9",
        "fullRangeMax": "2.147483647E9",
        "rangeMin": "0.0",
        "rangeMax": "65535.0",
        "currentMin": "90.0",
        "currentMax": "150.0"
    }]

    settings = {
        "Settings": {
            "ViewerState": {
                "Sources": {"Source": sources},
                # Instead of grouping by tile, we now use our two active channel groups:
                "SourceGroups": {"SourceGroup": source_groups},
                "DisplayMode": "fs",
                "Interpolation": "nearestneighbor",
                "CurrentSource": active_ids_sorted[0] if active_ids_sorted else "",
                "CurrentGroup": "0",
                "CurrentTimePoint": "0"
            },
            "SetupAssignments": {
                "ConverterSetups": {"ConverterSetup": converter_setups},
                "MinMaxGroups": {"MinMaxGroup": minmax_groups}
            },
            "ManualSourceTransforms": {
                # Add a default transform for each source
                "SourceTransform": [
                    {"@type": "affine", "affine": "1.0 0.0 0.0 0.0 0.0 1.0 0.0 0.0 0.0 0.0 1.0 0.0"}
                    for _ in range(len(sources))
                ]
            },
            "Bookmarks": ""
        }
    }
    return settings

def main():
    if len(sys.argv) < 2:
        print("Usage: python formatter.py <path/to/folder/with_rounds> <optional: output/folder")
        sys.exit(1)
    
    # file = "/shared/s3/e11-hpc/compute/RP022_i1264_cpd/gel1/fov1/"
    # spimdata_file = sys.argv[1]
    base_folder = sys.argv[1]
    # if len(sys.argv) == 3:
    #     output_settings_file = sys.argv[2]
    # else:
    #     output_settings_file = "stitch-dataset.settings.xml"
    def get_round_folders(base_folder: str) -> List[str]:
        """Get a list of round folders in the base folder."""
        return [os.path.join(base_folder, d) for d in os.listdir(base_folder) if d.startswith("round")]

    # base_folder = "/shared/s3/e11-hpc/compute/RP022_i1264_cpd/gel1/fov1"
    round_folders = get_round_folders(base_folder)

    print(round_folders)
    round_counter = 1

    for round_folder in round_folders:
        spimdata_file = os.path.join(round_folder, "stitch-dataset.xml")

        if len(sys.argv) == 3:
            output_settings_file = os.path.join(sys.argv[2], f"stitch-dataset{round_counter}.settings.xml")
            round_counter += 1
            print(f"Outputting to {output_settings_file}")
        else:
            output_settings_file = os.path.join(round_folder, "stitch-dataset.settings.xml")
        
        # 1. Load SpimData from XML.
        spim_data = load_spimdata(spimdata_file)
        
        # 2. Choose which view setups should be active.
        active_map = choose_active_sources(spim_data.sequence_description.view_setups.elements)
        
        # 3. Build the settings dictionary.
        settings_dict = build_settings_dict(spim_data, active_map)
        
        # 4. Convert the dictionary to XML.
        settings_xml = xmltodict.unparse(settings_dict, pretty=True)
        
        # 5. Write out the settings XML.
        with open(output_settings_file, "w", encoding="utf-8") as f:
            f.write(settings_xml)
        
        print(f"Settings XML written to {output_settings_file}")

if __name__ == "__main__":
    main()