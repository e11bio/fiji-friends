"""
This script reads a BigStitcher/SpimData XML file,
selects one active channel per tile (6 channels per tile) according to a channel offset,
and generates a BDV settings.xml file that exactly matches the expected structure.

When you copy it in and load the file, it might give you a java error — you can feel free to ignore that it doesn't really matter. Channels are starting at 0 (so 0-5, not 1-6).

In the working XML:
  - In <ViewerState>/<Sources> there are 72 Source entries,
    with the active flag set to true only for channel IDs
    0, 6, 12, 18, 24, 30, 36, 42, 48, 54, 60, and 66 (if offset=0).
  - The <SetupAssignments>/<ConverterSetups> section has 72 entries.
    For each tile of 6 channels:
      - The channel with (raw index – offset mod 6)==0 is "active" and gets:
          • if tile is even: min=100.0, max=125.0, color=-65281, groupId=0
          • if tile is odd:  min=100.0, max=150.0, color=16777215, groupId=1
      - All other channels get min=90.0, max=130.0, color=16777215, and groupId equal to their adjusted index (1–5).
  - The <SourceGroups> section groups the active channels:
      • In even tiles (tile%6==0) the active channel’s ID goes into group “green”
      • In odd tiles the active channel’s ID goes into group “magenta”
  - The <MinMaxGroups> section is generated with 6 groups:
      • Group 0: currentMin=0.0/currentMax=65535.0
      • Groups 1–5: currentMin=90.0/currentMax=130.0
  - <ManualSourceTransforms> always outputs exactly 4 transforms.
  
Optionally, a channel offset (an integer between 0 and 5) may be provided.
If not provided, it defaults to 0.
  
Dependencies:
    pip install pydantic-bigstitcher xmltodict
"""

import sys
import os
import xmltodict
from math import floor
from pydantic_bigstitcher import SpimData
import argparse
from xml.dom.minidom import parseString

# Colors and calibration values (as strings)
GREEN_COLOR = "65281"   # active channel in even tiles (green)
MAGENTA_COLOR = "16596405"  # active channel in odd tiles (magenta)
DEFAULT_MIN_ACTIVE_EVEN = "100.0"
DEFAULT_MAX_ACTIVE_EVEN = "125.0"
DEFAULT_MIN_ACTIVE_ODD  = "100.0"
DEFAULT_MAX_ACTIVE_ODD  = "150.0"
DEFAULT_MIN_NONACTIVE   = "90.0"
DEFAULT_MAX_NONACTIVE   = "130.0"

def text_elem(val):
    """Wrap a value as a text element for xmltodict."""
    return {"#text": str(val)}

def load_spimdata(xml_filename: str) -> SpimData:
    """Load the BigStitcher XML file into a SpimData object."""
    with open(xml_filename, "r", encoding="utf-8") as f:
        xml_content = f.read()
    spim_data = SpimData.from_xml(xml_content)
    return spim_data

def build_viewer_sources(view_setups, offset: int):
    """
    Build a list of Source dictionaries for the <ViewerState>/<Sources> section.
    Each view setup gets a <Source> with <active> set to "true" only if its adjusted index is 0.
    The adjusted index is defined as (raw_index - offset) mod 6.
    """
    sources = []
    # Assume view_setups are sorted by id
    sorted_setups = sorted(view_setups, key=lambda vs: int(vs.ident))
    for i, vs in enumerate(sorted_setups):
        raw = i % 6
        adjusted = (raw - offset) % 6
        active_flag = "true" if adjusted == 0 else "false"
        sources.append({"active": text_elem(active_flag)})
    return sources

def build_converter_setups(view_setups, offset: int):
    """
    Build a list of ConverterSetup entries for each channel (view setup).
    For each channel i (0-indexed):
      - Let tile = i // 6 and raw = i % 6.
      - Compute adjusted = (raw - offset) mod 6.
      - If adjusted == 0 (active channel):
          If tile is even, use min=100.0, max=125.0, color=GREEN_COLOR, groupId="0"
          If tile is odd,  use min=100.0, max=150.0, color=MAGENTA_COLOR, groupId="1"
      - Else (non-active):
          Use min=90.0, max=130.0, color=16777215, groupId = str(adjusted)
    Each entry’s fields are wrapped as elements.
    """
    converter_setups = []
    sorted_setups = sorted(view_setups, key=lambda vs: int(vs.ident))
    for i, vs in enumerate(sorted_setups):
        tile = i // 6
        raw = i % 6
        adjusted = (raw - offset) % 6
        if adjusted == 0:
            # Active channel in this tile
            if tile % 2 == 0:
                min_val = DEFAULT_MIN_ACTIVE_EVEN
                max_val = DEFAULT_MAX_ACTIVE_EVEN
                color = GREEN_COLOR
                groupId = "0"
            else:
                min_val = DEFAULT_MIN_ACTIVE_ODD
                max_val = DEFAULT_MAX_ACTIVE_ODD
                color = MAGENTA_COLOR
                groupId = "1"
        else:
            # Non-active channel
            min_val = DEFAULT_MIN_NONACTIVE
            max_val = DEFAULT_MAX_NONACTIVE
            color = "16777215"
            groupId = str(adjusted)
        entry = {
            "id": text_elem(vs.ident),
            "min": text_elem(min_val),
            "max": text_elem(max_val),
            "color": text_elem(color),
            "groupId": text_elem(groupId)
        }
        converter_setups.append(entry)
    return converter_setups

def build_source_groups(view_setups, offset: int):
    """
    Build the <SourceGroups> section.
    We group active channels (those with adjusted index 0) into two groups:
      - "green": if tile is even
      - "magenta": if tile is odd
    We loop over all channels, and for each channel i (sorted by id),
    if its adjusted index is 0, we add its id to the corresponding group.
    """
    group_green = []
    group_magenta = []
    sorted_setups = sorted(view_setups, key=lambda vs: int(vs.ident))
    for i, vs in enumerate(sorted_setups):
        raw = i % 6
        adjusted = (raw - offset) % 6
        if adjusted == 0:
            tile = i // 6
            if tile % 2 == 0:
                group_green.append(vs.ident)
            else:
                group_magenta.append(vs.ident)
    groups = [
        {
            "active": text_elem("true"),
            "name": text_elem("green"),
            "id": [text_elem(id_) for id_ in group_green]
        },
        {
            "active": text_elem("true"),
            "name": text_elem("magenta"),
            "id": [text_elem(id_) for id_ in group_magenta]
        }
    ]
    return groups

def build_minmax_groups():
    """
    Build 6 MinMaxGroup entries.
      - Group 0 gets currentMin=0.0 and currentMax=65535.0.
      - Groups 1 through 5 get currentMin=90.0 and currentMax=130.0.
    Other fields are fixed.
    """
    groups = []
    # Group 0:
    groups.append({
        "id": text_elem("0"),
        "fullRangeMin": text_elem("-2.147483648E9"),
        "fullRangeMax": text_elem("2.147483647E9"),
        "rangeMin": text_elem("0.0"),
        "rangeMax": text_elem("65535.0"),
        "currentMin": text_elem("0.0"),
        "currentMax": text_elem("65535.0")
    })
    # Groups 1 to 5:
    for g in range(1, 6):
        groups.append({
            "id": text_elem(str(g)),
            "fullRangeMin": text_elem("-2.147483648E9"),
            "fullRangeMax": text_elem("2.147483647E9"),
            "rangeMin": text_elem("0.0"),
            "rangeMax": text_elem("65535.0"),
            "currentMin": text_elem("90.0"),
            "currentMax": text_elem("130.0")
        })
    return groups

def build_manual_source_transforms(num=4):
    """
    Build exactly num SourceTransform entries.
    We use an affine transform of "1.0 0.0 0.0 0.0 0.0 1.0 0.0 0.0 0.0 0.0 1.0 0.0".
    Note: In the working XML there are 4 such entries.
    """
    transform_text = "1.0 0.0 0.0 0.0 0.0 1.0 0.0 0.0 0.0 0.0 1.0 0.0"
    return [{"@type": "affine", "affine": text_elem(transform_text)} for _ in range(num)]

def build_settings_dict(spim_data: SpimData, offset: int) -> dict:
    """Build the full settings dictionary for output."""
    view_setups = spim_data.sequence_description.view_setups.elements

    sources = build_viewer_sources(view_setups, offset)
    converter_setups = build_converter_setups(view_setups, offset)
    source_groups = build_source_groups(view_setups, offset)
    minmax_groups = build_minmax_groups()
    manual_transforms = build_manual_source_transforms(4)

    # For CurrentSource we use the id of the first view setup.
    sorted_setups = sorted(view_setups, key=lambda vs: int(vs.ident))
    current_source = sorted_setups[0].ident if sorted_setups else ""

    settings = {
        "Settings": {
            "ViewerState": {
                "Sources": {"Source": sources},
                "SourceGroups": {"SourceGroup": source_groups},
                "DisplayMode": text_elem("fs"),
                "Interpolation": text_elem("nearestneighbor"),
                "CurrentSource": text_elem(current_source),
                "CurrentGroup": text_elem("0"),
                "CurrentTimePoint": text_elem("0")
            },
            "SetupAssignments": {
                "ConverterSetups": {"ConverterSetup": converter_setups},
                "MinMaxGroups": {"MinMaxGroup": minmax_groups}
            },
            "ManualSourceTransforms": {"SourceTransform": manual_transforms},
            "Bookmarks": ""
        }
    }
    return settings
def prettify_xml(xml_string):
    dom = parseString(xml_string)
    return dom.toprettyxml(indent="  ")

def main():
    parser = argparse.ArgumentParser(description="Generate BDV settings.xml from BigStitcher/SpimData XML.")
    parser.add_argument("spimdata_file", help="Path to the input SpimData XML file.")
    parser.add_argument("-o", "--output_settings_file", default ="stitch-dataset2.settings.xml", help="Path to the output settings XML file.")
    parser.add_argument("-c", "--channel_offset", type=int, default=0, help="Channel offset (default: 0).")
    parser.add_argument("-g","--generate_all", action="store_true", default=False, help="Generate a settings file for each channel offset (0-5).")

    args = parser.parse_args()

    if args.channel_offset < 0 or args.channel_offset > 7:
        print("channel_offset must be between 0 and 7")
        sys.exit(1)
    
    if args.generate_all:
        for offset in range(6):
            output_file = args.output_settings_file.replace(".xml", f"_offset_{offset}.xml")
            print(f"Generating settings for channel offset: {offset}")
            spim_data = load_spimdata(args.spimdata_file)
            settings_dict = build_settings_dict(spim_data, offset)
            settings_xml = xmltodict.unparse(settings_dict)
            pretty_xml = prettify_xml(settings_xml)
            with open(output_file, "w", encoding="utf-8") as f:
                f.write(pretty_xml)
            print(f"Settings XML written to {output_file}")
    else:
        print(f"Using channel offset: {args.channel_offset}")
        spim_data = load_spimdata(args.spimdata_file)
        settings_dict = build_settings_dict(spim_data, args.channel_offset)
        settings_xml = xmltodict.unparse(settings_dict)
        pretty_xml = prettify_xml(settings_xml)
        with open(args.output_settings_file, "w", encoding="utf-8") as f:
            f.write(pretty_xml)
        print(f"Settings XML written to {args.output_settings_file}")

if __name__ == "__main__":
    main()
