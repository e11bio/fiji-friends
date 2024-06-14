"""
Briefly, steps are kind of similar and we can pull code from the montage maker, but for memory reasons we probably want to open files in serial, save, then open the next one.

We need to have two use cases:
*  series is saved as a single image
* series is saved as individual multipoints, might not be an issue since this always exists.

We also need to gracefully handle the metadata.


We likely need to:
* look at file, get number of series in the file -- DONE
* get directory  -- DONE
* open first series -- DONE
* save as tiff to directory
* set b&c to contrast the usual
* make MIP and remove brightfield channel
* save MIP as jpg and png
* close
* open next series if there is any left to repeat 
"""

from ij import IJ # standard
import re

import sys

# for the overlays
from ij.gui import Overlay, TextRoi, Roi, GenericDialog
from java.awt import Font, Color

# for saving and file paths
from ij.io import FileSaver
import os

from loci.plugins import BF
from loci.plugins.in import ImporterOptions
from ij import IJ
import os


from ij import IJ, WindowManager
from ij.gui import GenericDialog

from ij.io import OpenDialog

from loci.plugins import BF
from loci.plugins.in import ImporterOptions
from loci.formats import ImageReader
from loci.common import DebugTools
from ij import IJ
import os

def select_file():
    # Create a file open dialog
    od = OpenDialog("Select a File", None)
    
    # Get the selected file path
    directory = od.getDirectory()
    filename = od.getFileName()
    
    # If no file was selected, return None
    if filename is None:
        return None
    
    # Construct the full file path
    file_path = directory + filename
    return file_path


def get_series_count(file_path):
    '''Get the number of series in the file we loaded in'''
     # Check if the file exists
    if not os.path.isfile(file_path):
        IJ.log("File does not exist: " + file_path)
        return None
    
    # Disable Bio-Formats logging
    DebugTools.enableLogging("OFF")

    # Create an ImageReader instance
    reader = ImageReader()
    
    try:
        # Set the file path
        reader.setId(file_path)
        
        # Get the number of series
        num_series = reader.getSeriesCount()
    finally:
        # Always close the reader to release resources
        reader.close()  
    return num_series


def open_image(file_path, series_num):
    # Check if the file exists
    if not os.path.isfile(file_path):
        IJ.log("File does not exist: " + file_path)
        return None
    
    # Get the number of series in the file
    num_series = get_series_count(file_path)
    
    # Check if the series number is valid
    if series_num < 0 or series_num >= num_series:
        IJ.log("Invalid series number: " + str(series_num))
        return None
    
    IJ.log('opening series {}'.format(series_num))
    IJ.run("Bio-Formats Importer", "open={} autoscale color_mode=Composite series_{}".format(file_path, series_num))
    imp = IJ.getImage()
    IJ.log('Opened series {} with title '.format(series_num,
                                                 imp.getTitle()))    
    # If no images were imported, return None
    if not imp:
        IJ.log("No images found in series: " + str(series_num) + " in file: " + file_path)
        return None
    return imp

def save_as_tiff(imp, save_path):
    # Use FileSaver to save the image as a TIFF
    if imp is not None:
        fs = FileSaver(imp)
        if fs.saveAsTiff(save_path):
            IJ.log("Image saved as TIFF: " + save_path)
        else:
            IJ.log("Failed to save image as TIFF: " + save_path)
    else:
        IJ.log("No image to save")
# Example usage
# selected_file = select_file()
selected_file = '/Volumes/data-1/write/Brain-Screening-Data/i1350/240503_ID-i1350_slice-s15-s22_obj-10x_chs-BF-GFP.nd2' #hard coding for the moment

if selected_file:
    IJ.log("Selected file: " + selected_file)
else:
    IJ.log("No file selected")
    sys.exit(1)


directory = os.path.dirname(selected_file)
if directory:
     IJ.log("Save directory will be:" + directory)
else:
     IJ.log("No save directory, exiting.")
     sys.exit(1)


series_len = get_series_count(selected_file)
if series_len:
    IJ.log("Number of images in file: " + str(series_len))
else:
     IJ.log("Failed to retrieve series len.")



# a loop late but for now
imp = open_image(selected_file, 1) #open image and get the variable to refer to it
title = imp.getTitle()
imgName = title.split(" ")[0] # Extract the filename without extension
imgName= IJ.substring(imgName,0,lengthOf(imgName)-4)


if imp:
    save_path = os.path.join(directory, img_name, "_series-{}.tiff".format(1))
    print(save_path)
    # save_as_tiff(imp, save_path)


