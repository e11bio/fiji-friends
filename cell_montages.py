# This is a reimplemenation of the montaging script in python instead of fiji's macro languagdthis script is meant to be run on an single zed image (either a MIP or a single z) with many ROIs selected.
# This creates a grayscale montage of each ROI with labels on each panel,
# and saves it as a .png file. It saves an overview image with all channels and a montage of each individual channel.
# the png image is a single frame from the center of the stack, ish. it's pretty ugly whoopsies.

from ij import IJ, WindowManager
#from ij import ImagePlus, StackConverter
from ij.plugin.frame import RoiManager
from ij.gui import GenericDialog
import os
import sys
from datetime import datetime

from ij.gui import Overlay, TextRoi, Roi, GenericDialog
from java.awt import Font, Color, FontMetrics

#stuff for saving
from ij.io import FileSaver
import os

# in fiji the dialog is nice because i otherwise hardcode everyhting

from ij import IJ, WindowManager
from ij.gui import GenericDialog

# Function to create and show the dialog
def showParametersDialog(image):
    """
    Displays a dialog window for specifying image information.

    Parameters:
    - image: The open fiji image for which information is being specified.

    Returns:
    tuple: A tuple containing the following information:
        - date (str): Date in YYMMDD format.
        - roi_set_filename (str): Filename for the ROI set.
        - n_chans (int): Number of channels.
        - downsampling_scale (float): Downsampling scale. 
        - annotation_font_size (int): Annotation font size.
        - montage_rows (int): Number of montage rows.
        - pixel_adjust (int): Pixel adjustment.
        - col_offset (float): Column offset.
    """
    gd = GenericDialog("Specify Image Information") #name the window

    imgName = image.getTitle() # Get the title of the currently open window

    default_date = datetime.now().strftime("%y%m%d") 
    default_roi_set_filename = "RoiSet.zip"

    default_n_chans = image.getNChannels() if image else 6

    # Add input fields to the dialog
    gd.addStringField("Date (YYMMDD):", default_date)
    gd.addStringField("ROI Set Filename:", default_roi_set_filename)

    gd.addNumericField("Number of Channels:", default_n_chans, 0)
    gd.addNumericField("Downsampling Scale (when montaging):", 0.8, 2)
    gd.addNumericField("Annotation size\n(as fraction of image)", 10, 0)
    gd.addNumericField("Montage Rows:", 1, 0)
    gd.addNumericField("Pixel Adjustment (not used):", 3, 0)
    gd.addNumericField("Column Offset: (not used", 0.03, 2)

    # Show the dialog
    gd.showDialog()

    if gd.wasCanceled():
        print("Dialog canceled")
        sys.exit()

    # Retrieve values from the dialog
    date = gd.getNextString()
    roi_set_filename = gd.getNextString()

    n_chans = int(gd.getNextNumber())
    downsampling_scale = gd.getNextNumber()
    annotation_font_size = int(gd.getNextNumber())
    montage_rows = int(gd.getNextNumber())
    pixel_adjust = int(gd.getNextNumber())
    col_offset = gd.getNextNumber()

    return date, roi_set_filename, n_chans, downsampling_scale, annotation_font_size, montage_rows, pixel_adjust, col_offset

def getChannelNamesForm(image, n_chans):
    """
    Displays a dialog window for specifying channel names based on the image filename.

    Parameters:
    - image (ImagePlus): The image for which channel names are being specified.
    - n_chans (int): The number of channels.

    Returns:
    list or None: A list containing the specified channel names. Returns None if the dialog is canceled.
    """
    gd = GenericDialog("Specify Channel Names")

    name = image.getTitle() # Get the title of the currently open window

    # Extract default channel names from the filename
    filename_parts = name.split("_")
    default_channel_names = filename_parts[6:6+n_chans]

    for i, default_value in enumerate(default_channel_names, start=1):
        gd.addStringField("Channel {}:".format(i), default_value)

    gd.showDialog()

    if gd.wasCanceled():
        return None

    # Retrieve channel names from the form
    channel_names = [gd.getNextString() for _ in range(len(default_channel_names))]
    return channel_names

def createOutputFolders(directory):
    """
    Create TIFFs and PNGs folders in the specified directory.

    Parameters:
    - directory (str): The directory in which to create the folders.

    Returns:
    tuple: A tuple containing the paths to the TIFFs and PNGs folders.
    """
    tiff_folder = os.path.join(directory, "tiffs")
    png_folder = os.path.join(directory, "pngs")

    # Create folders if they don't exist
    for folder in [tiff_folder, png_folder]:
        if not os.path.exists(folder):
            print("Creating folder: {}".format(folder))
            os.makedirs(folder)

    return tiff_folder, png_folder

def get_max_text_height(font_size):
    """
    Calculate the maximum height of a text rendered with a specified font size.

    Parameters:
    - font_size (int): The font size for which to calculate the maximum text height.

    Returns:
    int: The maximum height of the text bounding box for the given font size.
    """
    temp_roi = TextRoi(0, 0, "Sample Text", Font("SansSerif", Font.PLAIN, font_size))
    temp_roi.setStrokeColor(Color(0, 0, 0, 0))
    return temp_roi.getBounds().height

def define_widths(montage_file, montage_col, montage_row, offset,  annotation_font_size_percentage):
    """
    Calculate and print various dimensions and offsets for a montage of images.

    Parameters:
    - montage_col (int): Number of columns in the montage.
    - montage_row (int): Number of rows in the montage.
    - offset (float): Offset factor for column and height offsets.
    - annotation_font_size_percentage (float): Percentage of image size to use as font size.

    Returns:
    single_img_height, single_img_width, row_offset, col_offset, font_size

    Prints:
    - The entire montage size in pixels.
    - Size of each frame in the montage.
    - Column offset (from the left edge) and height offset.
    - Calculated font size and maximum text height for annotations.
    """
    # get the deets
    montage_width = IJ.getImage().getWidth()
    montage_height = IJ.getImage().getHeight()
    # figure out each individual space
    single_img_width = montage_width/montage_col
    single_img_height = montage_height/montage_row
    col_offset = offset * single_img_width #+ 40 # this should be how far out from the left edge it goes
    row_offset = offset* 2 * single_img_height   # this should be how far down it goes

    annotation_adjustment = 0.1  # Adjust this percentage based on your preference
    font_size = int(min(single_img_width, single_img_height) * annotation_adjustment)
    textHeight = get_max_text_height(font_size)
    row_offset = textHeight # offset * single_img_height + textHeight # this should be how far down it goes



    print(("The entire montage is {}x{} pixels."
            "\nEach frame is {}x{}."
            "\n The column offset from the edge is is {},"
             "and the offset from the bottom is {}.").format(montage_width, 
                                                    montage_height,
                                                    single_img_width,
                                                    single_img_height, 
                                                    col_offset, 
                                                    row_offset))

    return single_img_height, single_img_width, row_offset, col_offset, font_size

def generate_coordinates(montage_col, montage_row, single_img_width, single_img_height, row_offset, col_offset):
    """
    Generate coordinates for a grid of images in a montage.

    Parameters:
    - montage_col (int): Number of columns in the montage.
    - montage_row (int): Number of rows in the montage.
    - single_img_width (int): Width of each individual image frame.
    - single_img_height (int): Height of each individual image frame.
    - row_offset (int): Offset for adjusting the vertical position of the grid.
    - col_offset (int): Offset for adjusting the horizontal position of the grid.

    Returns:
    list: List of (x, y) coordinates for each image in the montage.
    """
    coordinates = []
    for row in range(montage_row):
        for col in range(montage_col):
            x = (col * single_img_width) + col_offset
            y = ((row + 1) * single_img_height) - row_offset  # Static offset for vertical position
            coordinates.append((x, y))
    print("Coordinates are: {}".format(coordinates))
    return coordinates

def add_overlays(imp, overlay, channels, coordinates, annotation_font_size):
    """
    Add text overlays to an ImagePlus object at specified coordinates.

    Parameters:
    - imp (ImagePlus): The ImagePlus object to which overlays are added.
    - overlay (Overlay): The Overlay object to store the text annotations.
    - channels (list): List of channel names corresponding to coordinates.
    - coordinates (list): List of (x, y) coordinates where text annotations are placed.
    - annotation_font_size (int): Font size for the text annotations.

    Returns:
    None

    Modifies:
    - Adds TextRoi overlays to the specified ImagePlus and Overlay objects.
    - Displays the ImagePlus with the added overlays.
    """
    font = Font("SanSerif", Font.PLAIN, annotation_font_size)  # Font set for all annotations

    for i, (x, y) in enumerate(coordinates):
        channel_name = channels[i]

        # Create TextRoi at the specified coordinates with the channel name
        roi = TextRoi(int(x), int(y), channel_name, font)

        # Set stroke color to yellow
        roi.setStrokeColor(Color.yellow)

        # Set fill color to semi-transparent black
        roi.setFillColor(Color(0, 0, 0, 0.5))

        # Add the TextRoi to the overlay
        overlay.add(roi)

        # Set the TextRoi as the active ROI in the ImagePlus
        imp.setRoi(roi)

    # Set the overlay with annotations to the ImagePlus
    imp.setOverlay(overlay)

    # Show the ImagePlus with annotations
    imp.show()


def processROIs(image, 
                roi_manager, 
                n_chans, 
                tiff_folder, 
                montage_cols, 
                montage_rows, 
                downsampling_scale,
                pixel_adjust,
                annotation_font_size,
                slice_range=1):
    """
    Process ROIs using the specified parameters.

    Parameters:
    - originalName (str): The name of the original image.
    - roi_manager (RoiManager): The ROI manager instance.
    - n_chans (int): The number of channels.
    - tiff_folder (str): The folder to save TIFF images.
    - montage_cols (int): Number of columns in the montage.
    - montage_rows (int): Number of rows in the montage.
    - downsampling_scale (float): Downsampling scale.
    - pixel_adjust (float): Pixel adjustment.

    Returns:
    None
    """
    name = image.getTitle()  # Placeholder for later use

    default_n_chans = image.getNChannels() if image else 6

    for i in range(0, roi_manager.getCount()):
        # Get the ROI info
        IJ.selectWindow(name)
        imp = IJ.getImage()  # Assuming the image is the active image

        roi_manager.select(i)  # Select the next ROI
        channel = imp.getC()
        current_slice = imp.getZ()

        # set the slice range
        start_slice = max(1, current_slice - slice_range)
        end_slice = min(imp.getNSlices(), current_slice + slice_range)

        # # Make a duplicate image
        IJ.run("Duplicate...", "duplicate channels=1-" + str(n_chans) + " slices=" + str(start_slice) + "-" + str(end_slice))
        # # save the z stepped as a tiff to return back to this easily
        save_as_tiff = "{}/ROI-{}_Zpos-{}_{}".format(tiff_folder, i, current_slice, name)
        IJ.saveAs("Tiff", save_as_tiff)
        print("Saved{}".format(save_as_tiff))
        
        imp = IJ.getImage() # how does this shit work. what is an instance.
        # trim to get only the middle slice
        centerSlice = imp.getNSlices()
        cSlicefmt = str(int(centerSlice/2+1))

        IJ.run(imp, "Make Substack...", "channels=1-6 slices={}".format(cSlicefmt))
        # # # Resize to have enough pixels to write on
        IJ.run("Size...", "width=" + str(imp.getWidth() * pixel_adjust) + " depth=" + str(n_chans) + " constrain average interpolation=None")
        
        # # Make the montage
        IJ.run("Make Montage...", "columns=" + str(montage_cols) + " rows=" + str(montage_rows) + " scale=" + str(downsampling_scale) + " border=6 use")
        montage = IJ.getImage()

        single_img_height, single_img_width, row_offset, col_offset, font_size = define_widths(montage, montage_cols, montage_rows, .03, annotation_font_size)
        coordinates = generate_coordinates(montage_cols, montage_rows, single_img_width, single_img_height, row_offset, col_offset)

        overlay = Overlay()

        add_overlays(montage, overlay, channels, coordinates, font_size)
        
        save_as_png = "{}/ROI-{}_Zpos-{}_{}.png".format(png_folder, i, current_slice, name)
        FileSaver(montage).saveAsPng(save_as_png)
        print("Saved{}".format(save_as_png))
        

# Show the parameters dialog
active_image = IJ.getImage() #handle for referring to image
parameters = showParametersDialog(active_image)

# assign params to variables and do the channel name assignment. breaks if channels are empty
if parameters is not None:
    date, roi_set_filename, n_chans, downsampling_scale, annotation_font_size, montage_rows, pixel_adjust, col_offset = parameters
    montage_cols = n_chans/montage_rows
   # assign channel params
    channels = getChannelNamesForm(active_image, n_chans)
    if channels is None:
        sys.exit() 

    filePath = active_image.getOriginalFileInfo().filePath if active_image.getOriginalFileInfo() else None
    directory = os.path.dirname(filePath) if filePath else None
    
    tiff_folder, png_folder = createOutputFolders(directory)
    print("TIFFs Folder:", tiff_folder)
    print("PNGs Folder:", png_folder)
    # Use the retrieved parameters
    roi_manager = RoiManager.getInstance()  # Get the ROI manager instance
    
    if roi_manager is not None:
        roi_manager.runCommand("Save", os.path.join(directory, "{}_{}".format(date, roi_set_filename)))
    else:
        print("ROI Manager not open. Please open it and try again.")

    # Further use of the parameters...
    print("Active Image: {}".format(active_image))
    print("File Path: {}".format(filePath))
    print("Directory: {}".format(directory))
    print("Image Title: {}".format(active_image.getTitle()))

    print("Number of Channels: {}".format(n_chans))
    print("Downsampling Scale: {}".format(downsampling_scale))
    print("Annotation Font Size: {}".format(annotation_font_size))
    print("Montage Rows: {}".format(montage_rows))
    print("Pixel Adjustment: {}".format(pixel_adjust))
    print("Column Offset: {}".format(col_offset))
    print("Channels: {}".format(channels))
    print("Number of Channels: {}".format(n_chans))

## now we have made the paramters. hooray.

processROIs(active_image, roi_manager, n_chans, tiff_folder,
            montage_cols, montage_rows, downsampling_scale, 
            pixel_adjust, annotation_font_size, 3)