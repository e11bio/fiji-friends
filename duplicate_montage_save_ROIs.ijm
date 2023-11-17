// this script is meant to be run on an single zed image (either a MIP or a single z) with many ROIs selected.
// This creates a grayscale montage of each ROI with labels on each panel,
// and saves it as a .png file. It does not currently save the tiff file, and it does **not** save an overview image of your original file.


originalName = getTitle(); //gets the title of your currently open window so we can come back to it
directory = getDirectory(1);  // specify the place where we will save all of the .pngs we're about to make

Stack.setDisplayMode("grayscale");  //grayscale is best scale for the montage
n_chans = 6; //variable to set the number of channels we're working with. e.g. if you only want the first five (and the 6th is a null imaging channel because of the dual acquisition), set this to 5


//update channel names to reflect reality
ch1 = "HA";
ch2 = "AU5";
ch3 = "ALFA";
ch4 = "SPOT";
ch5 = "NWS";
ch6 = "S1";

downsampling_scale = 0.8;  //tweak this as needed. for res level three, i'd advice no downsampling at all
annotation_font_size = 12; //tweak as needed -- try running this on a single ROI first. The font doesn't auto set yet.
montage_cols = n_chans; //
montage_rows = 1;


//just some stuff for later
setFont("SansSerif", annotation_font_size, " antialiased");
setColor("white");

for (i = 1; i < roiManager('count'); i++) {
	selectWindow(originalName);
    roiManager('select', i); //select the next roi
    print(i); //sanity check
    run("Duplicate...", "duplicate channels=1-"+n_chans); //keep the first n_chans channels
    name = getTitle(); //just a placeholder for later because I don't understand Fiji window management
    print(name); // sanity check
	run("Make Montage...", "columns="+montage_cols+" rows="+montage_rows+" scale="+downsampling_scale+" border = 40 use"); 

//this is some stuff to automatically label in the same place in the panels, regardless of how wide the ROI is

	single_img_width = getWidth()/montage_cols;  // get the width of one column
	single_img_height = getHeight()/montage_rows; // get the height of one row

	row_offset = 0.03*single_img_height; // might need to vary but so far fine
	col_offset = 0.03; // might need to vary but so far fine

	x_1 = single_img_height - row_offset;

	y_1 = col_offset;
	y_2 = single_img_width + y_1;
	y_3 = 2*single_img_width + y_1;
	y_4 = 3*single_img_width + y_1;
	y_5 = 4*single_img_width + y_1;
	y_6 = 5*single_img_width + y_1;

	Overlay.drawString(ch1, y_1, x_1, 0.0);
	Overlay.drawString(ch2, y_2, x_1, 0.0);
	Overlay.drawString(ch3, y_3, x_1, 0.0);
	Overlay.drawString(ch4, y_4, x_1, 0.0);
	Overlay.drawString(ch5, y_5, x_1, 0.0);
	Overlay.drawString(ch6, y_6, x_1, 0.0);
	
	Overlay.show(); // show it

	print("new title is:");
	print(name);
	save_as = directory+name+"_ROI-"+i; //make name to save it
	print("saving as...." + save_as);
	saveAs("PNG", save_as); //actually save it
	close(); //close the png
	close(name); //close the tiff file we made along the way
//back to the beginning
};

print("Done saving thumbnails");

// saving an overlay image
// colors are gonna be set here for a minute because they shouldn't be touched really
colorArray = newArray("Red", "Green", "Blue", "Grays", "Cyan", "Magenta");

// Loop through channels and colors
for (i = 0; i < n_chans; i++) {
    channel = i + 1; // Channels start from 1
    // Set the channel
    Stack.setChannel(channel);
    // Run the command with the corresponding color
    run(colorArray[i]);
}

Stack.setDisplayMode("composite");
run("From ROI Manager"); //add the ROIs as an overlay
save_as = directory+originalName;
print(save_as)
saveAs("PNG", save_as); //actually save it
print("Done saving overlay image");

//close("\\Others");

