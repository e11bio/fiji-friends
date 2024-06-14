### //// ####
# Wishlist:
# * specify the input shape of the montage
# * figure out how to deal with ordering slices correctly more robustly
# * figure out running headlessly e.g. don't set these variables hard coded.
# *  fix the offsets?
# *  scale bar (pull from original fiji script)

### //// ####
# This is a re-implementation of a previous fiji language script to montage a set of images with annotations on the slice information.
# It will have a third, and hopefully final, implementation in Napari.
# In the meantime.
# We assume we have opened a file with channels and different positions (Fiji reads these as z stacks or as timepoints. It doesn't matter.)
# B&C# Channels should be in sequential order. 
# The user inputs some information about the sample (slices, sample ID, # slices between slices) and output (downsampling, text sizes)
# The script takes the file, creates a montage, automatically places text ROIs with slice information, and saves it back as .JPG to the original image folder.


from ij import IJ # standard
import re

# stuff for the overlays
from ij.gui import Overlay, TextRoi, Roi, GenericDialog
from java.awt import Font, Color

#stuff for saving
from ij.io import FileSaver
import os

active_image = IJ.getImage() #handle for referring to image
originalName = active_image.getTitle() # Get the title of the currently open window


# some stuff to auto set directory
file_path = active_image.getOriginalFileInfo().filePath if active_image.getOriginalFileInfo() else None
existing_directory = os.path.dirname(file_path) if file_path else None

## HERE WE GO
def remove_non_numeric(string):
    return ''.join(c for c in string if c.isdigit() or c == '.')

def extract_variables_from_filename(filename, existing_directory=None):
    # Remove file extension if present
    filename, _ = os.path.splitext(filename)

    pairs = {}

    # Split the filename by "_"
    elements = filename.split("_")

    # Iterate through elements and split each by "-"
    for element in elements:
        key_value = element.split("-", 1)
        if len(key_value) == 2:
            key, value = key_value
            pairs[key] = value

    # Extract specific variables based on conditions
    sample_id = None
    try:
        sample_id = pairs.get('ID')
        if sample_id:
            sample_id = sample_id # Extract numeric part and convert to int
    except (ValueError, TypeError):
        print("Error: Unable to extract valid sample ID.")

    slice_values = pairs.get('slice')
    start_slice, end_slice = None, None
    
    if slice_values:
        slices = slice_values.split('-')
        start_slice_str = remove_non_numeric(slices[0])
        end_slice_str = remove_non_numeric(slices[1]) if len(slices) > 1 else None

        # Convert to float
        try:
            start_slice = float(start_slice_str)
            end_slice = float(end_slice_str) if end_slice_str else None
        except (ValueError, TypeError):
            print("Error: Unable to convert start or end slice to float.")

    # Save the key-value pairs to a JSON file in the specified directory
    if existing_directory:
        output_json_file = os.path.join(existing_directory, "output_file.json")
        with open(output_json_file, 'w') as json_file:
            json.dump(pairs, json_file, indent=2)
    
    return sample_id, start_slice, end_slice, pairs


# Example usage
# filename = "240105_ID-i1214_slice-s13-s24_obj-4x_chs-BF-GFP-tdTomato004"
# sample_name, start_slice, end_slice, pairs = extract_variables_from_filename(filename)

# actual usage
sample_name, start_slice, end_slice, pairs = extract_variables_from_filename(originalName)
sample_id = sample_name
print("Sample ID:", sample_id)
print("Start Slice:", start_slice)
print("End Slice:", end_slice)
print("Pairs:", pairs)

# Display a dialog to get user input
gd = GenericDialog("User Input")
gd.addStringField("Sample ID:", sample_id)
gd.addNumericField("Start Slice:", start_slice, 0)
gd.addNumericField("End Slice:", end_slice, 0)
gd.addNumericField("Skip Size:", 1, 0)
gd.addCheckbox("Image Cropped?:", False)
gd.addNumericField("Downsampling Scale:", 0.1, 2)
gd.addNumericField("Offset:", 0.1, 2)
gd.addStringField("Save Directory:", existing_directory)


gd.showDialog()




# Display a dialog to get user input
gd = GenericDialog("User Input")
gd.addStringField("Sample ID:", sample_name)
gd.addNumericField("Start Slice:", start_slice, 0)
gd.addNumericField("End Slice:", end_slice, 0)
gd.addNumericField("Skip Size:", 1, 0)
gd.addCheckbox("Image Cropped?:", False)
gd.addNumericField("Downsampling Scale:", 0.1, 2)
gd.addNumericField("Offset:", 0.1, 2)
gd.addStringField("Save Directory:", existing_directory)


gd.showDialog()

# Check if the user clicked OK
if not gd.wasOKed():
    print("User canceled the operation")
    exit()

# Assign user input to variables
start_slice = int(gd.getNextNumber())
end_slice = int(gd.getNextNumber())
skip_size = int(gd.getNextNumber())
sample_id = gd.getNextString()
crop = gd.getNextBoolean()
downsampling_scale = gd.getNextNumber()
offset = gd.getNextNumber()
directory = gd.getNextString()

# WIP stuff but basically runs ok
annotation_text_size = int(400 * downsampling_scale) #we'll try it!
num_slices = (end_slice - start_slice + 1)/skip_size

## parsing our file info to name things later

if crop:
    originalNameWithoutExt = "crop_{}".format(originalName.split(" ")[0]) # Extract the filename without extension by first space
else:  
    originalNameWithoutExt = originalName.split(" ")[0] # Extract the filename without extension

print("Operating on: {}".format(originalNameWithoutExt))
print("Calculated {} slices".format(num_slices))

def define_montage(num_slices,
                   downsampling_scale = downsampling_scale,
                   scale_bar_text = 150,
                   annotation_text_size = annotation_text_size):
    if num_slices <= 11:
        montage_col = 2
        montage_row = num_slices/2
    else:
        montage_col = 3
    montage_row = num_slices/montage_col
    print("This montage will spread {} tiles in a {}x{} montage, downsampled by {}".format(num_slices,
                                                                                            montage_col,
                                                                                            montage_row,
                                                                                            downsampling_scale))
    return montage_col, montage_row, downsampling_scale, scale_bar_text, annotation_text_size

def define_widths(montage_file, montage_col, montage_row, offset=offset):
    # get the deets
    montage_width = IJ.getImage().getWidth()
    montage_height = IJ.getImage().getHeight()
    # figure out each individual space
    single_img_width = montage_width/montage_col
    single_img_height = montage_height/montage_row
    col_offset = offset * single_img_width #+ 40 # this should be how far out from the left edge it goes
    row_offset = offset * single_img_height  # this should be how far down it goes

    print("The entire montage is {}x{} pixels. \nEach frame is {}x{} pixels. \nLabel positions will be offset by {} pixels from the bottom right corner".format(montage_width, montage_height, single_img_width, single_img_height, offset))

    return single_img_height, single_img_width, row_offset, col_offset

montage_col, montage_row, downsampling_scale, scale_bar_text, annotation_text_size = define_montage(num_slices)
print("Making montage..." )
IJ.run("Make Montage...", 
       "columns=" + str(montage_col) + 
       " rows=" + str(montage_row) + 
       " scale=" + str(downsampling_scale) +
       " border=40 use")
print("Montage done! Getting information about the final image dimensions.\n")

montage_file = IJ.getImage().getTitle()
single_img_height, single_img_width, row_offset, col_offset = define_widths(montage_file, montage_col, montage_row)

def generate_coordinates(montage_col, montage_row, single_img_width, single_img_height, row_offset, col_offset):
    coordinates = []
    for row in range(montage_row):
        for col in range(montage_col):
            x = ((row + 1) * single_img_height) - row_offset
            y = (col * single_img_width) + col_offset
            coordinates.append((x, y))
    return coordinates

def set_channel_names(sample_id, start_slice, end_slice, skip_size):
    channels = ["s{}".format(i) for i in range(start_slice, end_slice + 1, skip_size)]
    img0 = "{}_{}".format(sample_id, channels[0]) if channels else None
    channels[0] = img0
    return channels

# imp = IJ.getImage()
# overlay = Overlay()

def add_overlays(imp, overlay, channels, coordinates, annotation_text_size):
    font = Font("SanSerif", Font.PLAIN, annotation_text_size) #this is set for everything

    for i, (x, y) in enumerate(coordinates):
        channel_name = channels[i]
        roi = TextRoi(int(y), int(x), channel_name, font)
        roi.setStrokeColor(Color.yellow)
        roi.setFillColor(Color(0,0,0,0.5))  
        overlay.add(roi)
        imp.setRoi(roi)
            
    #imp.overlay.add(roi)
    imp.setOverlay(overlay)
    imp.show()


# Generate coordinates
coordinates = generate_coordinates(montage_col, montage_row, single_img_width, single_img_height, row_offset, col_offset)
print("Coordinates set.")
# Set channel names

channels = set_channel_names(sample_id, start_slice, end_slice, skip_size)

print("Names set: {}".format(channels))
print("\nTime to add overlays...")
# Add overlays
imp = IJ.getImage()
overlay = Overlay()
add_overlays(imp, overlay, channels, coordinates, annotation_text_size)
print("Overlays of sample reference information done.")

## everything above this works! ok. yay!

print("\nSaving easily readable files...")

# # Define the result location
## result_loc = os.path.join(directory, originalNameWithoutExt + "_annotated")

# # Save as PNG
print("\nSaving files in directory: {}".format(directory))
if crop:
    save_as_png = os.path.join(os.path.join(directory, originalNameWithoutExt + "_crop_annotated.png"))
    save_as_jpg = os.path.join(os.path.join(directory, originalNameWithoutExt + "_crop_annotated.jpg"))
else:
    save_as_png = os.path.join(os.path.join(directory, originalNameWithoutExt + "_annotated.png"))
    save_as_jpg = os.path.join(os.path.join(directory, originalNameWithoutExt + "_annotated.jpg"))

FileSaver(IJ.getImage()).saveAsPng(save_as_png)
print("Saved PNG....")

# # Save as JPEG
FileSaver(IJ.getImage()).saveAsJpeg(save_as_jpg)
print("Saved jpg. Done!")

