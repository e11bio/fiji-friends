// this script is meant to be run on an single zed image (either a MIP or a single z) with many ROIs selected.
// This creates a grayscale montage of each ROI with labels on each panel,
// and saves it as a .png file. It saves an overview image with all channels and a montage of each individual channel.


originalName = getTitle(); //gets the title of your currently open window so we can come back to it
directory = getDirectory(originalName);  // specify the place where we will save all of the .pngs we're about to make

// ** save the stuff so when i fuck up i can go back **//
date = "231204"
roiManager("Save", directory + date + "_RoiSet.zip");

Stack.setDisplayMode("grayscale");  //grayscale is best scale for the montage

// ** info about generating the images ** //

n_chans = 6; //variable to set the number of channels we're working with. e.g. if you only want the first five (and the 6th is a null imaging channel because of the dual acquisition), set this to 5

downsampling_scale = 1;  //tweak this as needed. for res level three, i'd advice no downsampling at all
annotation_font_size = 15; //tweak as needed -- try running this on a single ROI first. The font doesn't auto set yet.
montage_rows = 1;
montage_cols = n_chans/montage_rows; //
pixel_adjust = 3 // variable to scale up the image afterwards in case it's too tiny!! res level 3 needs biggers adjustment
col_offset = 0.03; // might need to vary but so far fine

// ** info about the channels ** //
ch1 = "HA"
ch2 = "AU5";
ch3 = "SPOT";
ch4 = "ALFA";
ch5 = "NWS";
ch6 = "S1";
ch7 = "HSV (r1)";

setFont("SansSerif", annotation_font_size, " antialiased");
setColor("white");

run("Colors...", "foreground=white");

n_chans = 6; //variable to set the number of channels we're working with. e.g. if you only want the first five (and the 6th is a null imaging channel because of the dual acquisition), set this to 5
for (i = 1; i < roiManager('count'); i++) {
	// get the ROI info
	selectWindow(originalName);
    roiManager('select', i); //select the next roi
    Stack.getPosition(channel, slice, frame);
    //make litte image
    run("Duplicate...", "duplicate channels=1-"+n_chans+" slices="+slice);
    
    //resize to have enough pixels to write on
    run("Size...", "width="+getWidth()*pixel_adjust+" depth="+n_chans+" constrain average interpolation=None"); //make it bigger for the pixel stuff later
    
    // make the montage
    name = getTitle(); //just a placeholder for later because I don't understand Fiji window management
	run("Make Montage...", "columns="+montage_cols+" rows="+montage_rows+" scale="+downsampling_scale+" border=6 use"); 
	
	//this is some stuff to automatically label in the same place in the panels, regardless of how wide the ROI is
	single_img_width = getWidth()/montage_cols;  // get the width of one column
	single_img_height = getHeight()/montage_rows; // get the height of one row
	row_offset = 0.03*single_img_height; // might need to vary but so far fine

	//make the positions now that we know how big the image is
	x_1 = single_img_height - row_offset;
	
	y_1 = col_offset;
	y_2 = single_img_width + y_1;
	y_3 = 2*single_img_width + y_1;
	y_4 = 3*single_img_width + y_1;
	y_5 = 4*single_img_width + y_1;
	y_6 = 5*single_img_width + y_1;
	y_7 = 6*single_img_width + y_1;

	Overlay.drawString(ch1, y_1, x_1, 0.0);
	Overlay.drawString(ch2, y_2, x_1, 0.0);
	Overlay.drawString(ch3, y_3, x_1, 0.0);
	Overlay.drawString(ch4, y_4, x_1, 0.0);
	Overlay.drawString(ch5, y_5, x_1, 0.0);
	Overlay.drawString(ch6, y_6, x_1, 0.0);
	// Overlay.drawString(ch7, y_7, x_1, 0.0);
	
	Overlay.show(); // show it
	print(name);
	save_as = directory+"ROI-"+i+"_Zpos-"+slice+"_"+name; //make name to save it
	saveAs("PNG", save_as); //actually save it
	close(); //close the png
	//close(name); //close the tiff file we made along the way
//back to the beginning
};

print("Done saving thumbnails");


//// ** saving a full view montage ** ///
selectWindow(originalName);
run("Z Project...", "projection=[Max Intensity]");
run("Make Montage...", "columns="+montage_cols+" rows="+montage_rows+" scale=.5 border = 40 use");

run("BIOP Channel Tools");

single_img_width = getWidth()/montage_cols;  // get the width of one column
single_img_height = getHeight()/montage_rows; // get the height of one row

row_offset = 0.03*single_img_height; // might need to vary but so far fine
//
//make the positions now that we know how big the image is
x_1 = single_img_height - row_offset;
//	
y_1 = col_offset;
y_2 = single_img_width + y_1;
y_3 = 2*single_img_width + y_1;
y_4 = 3*single_img_width + y_1;
y_5 = 4*single_img_width + y_1;
y_6 = 5*single_img_width + y_1;
y_7 = 6*single_img_width + y_1;
//
Overlay.drawString(ch1, y_1, x_1, 0.0);
Overlay.drawString(ch2, y_2, x_1, 0.0);
Overlay.drawString(ch3, y_3, x_1, 0.0);
Overlay.drawString(ch4, y_4, x_1, 0.0);
Overlay.drawString(ch5, y_5, x_1, 0.0);
Overlay.drawString(ch6, y_6, x_1, 0.0);
Overlay.drawString(ch7, y_7, x_1, 0.0);
//	
Overlay.show(); // show it
//
save_as = directory+"grayscale-montage_"+name; //make name to save it
saveAs("PNG", save_as); //actually save it
//
//NOW make the colorful overlay image
// colors are gonna be set here for a minute because they shouldn't be touched really
selectWindow(originalName);
colorArray = newArray("Red", "Green", "Blue", "Grays", "Cyan", "Magenta", "Yellow");
//
//// Loop through channels and colors
for (i = 0; i < n_chans; i++) {
    channel = i + 1; // Channels start from 1
    // Set the channel
    Stack.setChannel(channel);
    // Run the command with the corresponding color
    run(colorArray[i]);
}
//
Stack.setDisplayMode("composite");
run("From ROI Manager"); //add the ROIs as an overlay
save_as = directory+originalName;
print(save_as)
saveAs("PNG", save_as); //actually save it
print("Done saving overlay image");
//
//
//
