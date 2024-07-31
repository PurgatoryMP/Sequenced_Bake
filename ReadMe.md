# Sequenced Bake

## Description:
	
 - Sequenced Bake is a Blender 4.2 add-on designed to streamline the process of baking animated materials. With this add-on, users can efficiently bake out material sequences and pack them into sprite sheet or flipbook assets with a range of customizable options, enhancing their workflow and output quality.

## Key Features

 - **Animated Material Baking**: Seamlessly bake animated materials over a sequence of frames.
 - **Map Type Definition**: Select and define specific map types (e.g., combined, diffuse, normal, roughness, emission) to be baked.
 - **Customizable Output Resolution**: Set the desired resolution for the baked maps to meet your project needs.
 - **Organized Directory Structure**: Automatically saves baked maps into map type directory's for easy access and organization.
 - **Create sprite sheets or flipbook assets**: Pack any sequence of images into a sprite sheet or flipbook asset using this tool.

# Usage:

## Baking Material Map Sequences:

 1. Create your object and material.
 2. Animate your material using keyframes.
 3. Set the start and end frame in for the keyframes, the number of keyframes will be the number of images generated.
 4. Defined the output path in the sequence bake panel found in the 3D view N panel.
 5. Set the image size for the texture maps that will be baked out.
 6. Select the texture maps you want to be baked.
 7. Press Bake.
 
 - The material maps will be backed out one at a time and saved to subfolders in the output destination.

## Generating Sprite Sheets.

 1. First you will have had to bake out your material maps OR if you have existing images you want to pack into turn into a sprite sheet.
 2. Select the directory contaning the subfolders for the material maps or image sequences.
 3. Modify the settings for how many columns and rows and the size of the cells for each frame of animation.
 4. Choose a start and end frame for your animation. for example if I have 300 frames of animation but I only want to pack frames 150 to 250. start frame would be 150 and end frame would be 250.
 5. Click Generate Sprite Sheet.
 
 - This will pack all of the frames defined by the start and end frame onto the newly created sprite sheet.
 
 - The combined size of the cells will define how large the generated sprite sheet will be. Example: I have 64 cells of animation at 128x128 the generated sprite sheet will be 1024x1024.
 
# Notes: 

 - New directory's are created in the output path you defined for each of the map types to keep them organized. You can observe them populate during the baking process.
 
 - Blender might appear frozen or non-responsive while it bakes out the texture maps but you will see the UI update.
 
 - Depending on the output size you choose for the images and the complexity of the material, some bakes may take longer than others.
	
### Installation:
	
 - **Blender 3.1 -> 4.1**: 
 	-Preferences > Add-ons > Install from disk > Select the Sequenced_Bake.zip file
 	
 - **Blender 4.2**: 
 	
 	- **Option 1**: 
 	- Download the extension from extensions.blender.org which should put it in the proper directory and prompt you if you would like to enable it on installation.
 	
 	- **Option 2**: 
 	- Download the Sequenced_Bake.zip file and from the Preferences > Extensions create a custom directory in the extensions path ( appdata/roaming/Blender Foundation/4.2/extensions/ "Your custom Add-on directory name" /addons/ ) Then place the downloaded file into this path.