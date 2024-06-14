//ImageJ script for batch conversion of ND2 to TIFF format
//Dependencies: Bio-Formats plugin needed (FIJI)
//Instructions: Copy ND2 files into dedicated folder (no other files can be present in the same folder). Run macro and select input/output folder
// Specify default values for variables
var inputDir = "~/Downloads/ND2_test"

// Create dialog to obtain input from user
Dialog.create("File conversion (tiff)");
Dialog.addDirectory("Input/Output Directory:", inputDir);
Dialog.show();

inputDir = Dialog.getString();

// Get file list in input directory
images = getFileList(inputDir);

setBatchMode(true);

print("Input Directory: " + inputDir);
print("Converting " + images.length + " images");

// Loop over each nd2 file and convert to tiff
for (i = 0; i < images.length; i++) {
	print("Processing " + images[i]);
	// Open images using Bio-Formats plugin
	run("Bio-Formats Importer", "open=[" + inputDir + File.separator() + images[i] + "] rois_import=[ROI manager] view=Hyperstack stack_order=XYCZT");
	saveAs("Tiff", inputDir + images[i]);
	close("*");
}

setBatchMode(false);

print("All Done");
