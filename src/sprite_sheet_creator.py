# This file is part of Sequence Bake.
# 
# Sequence Bake is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or any later version.
# 
# Sequence Bake is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
# 
# You should have received a copy of the GNU General Public License
# along with Sequence Bake. If not, see <http://www.gnu.org/licenses/>.

import bpy
import os
import re
import numpy as np
import platform
import subprocess
from bpy.types import (
        Operator,
        Panel,
        PropertyGroup,
        )

image_formats = [
    ("PNG", "PNG", "Save as PNG"),
    ("JPEG", "JPEG", "Save as JPEG"),
    ("BMP", "BMP", "Save as BMP"),
    ("TIFF", "TIFF", "Save as TIFF"),
    ("TGA", "TGA", "Save as TGA"),
    ("OPEN_EXR", "OpenEXR", "Save as OpenEXR"),
    ("HDR", "Radiance HDR", "Save as Radiance HDR"),
    ("CINEON", "Cineon", "Save as Cineon"),
    ("DPX", "DPX", "Save as DPX")
]

generated_images = []

class SpriteSheetProperties(PropertyGroup):
    directory: bpy.props.StringProperty(
        name="",
        description="Select the directory containing subdirectories of images\nIf left blank will use the material output path",
        default="",
        maxlen=1024,
        subtype='DIR_PATH'
    )
    columns: bpy.props.IntProperty(
        name="Columns",
        description="Number of columns in the sprite sheet",
        default=8,
        min=1
    )
    rows: bpy.props.IntProperty(
        name="Rows",
        description="Number of rows in the sprite sheet",
        default=8,
        min=1
    )
    image_width: bpy.props.IntProperty(
        name="Cell Width",
        description="Width of each frame or cell in the sprite sheet",
        default=128,
        min=1
    )
    image_height: bpy.props.IntProperty(
        name="Cell Height",
        description="Height of each frame or cell in the sprite sheet",
        default=128,
        min=1
    )
    start_frame: bpy.props.IntProperty(
        name="Start Frame",
        description="The frame to start the sequence with",
        default=1,
        min=1
    )
    end_frame: bpy.props.IntProperty(
        name="End Frame",
        description="The frame to end the sequence with",
        default=64,
        min=1
    )
    is_reversed: bpy.props.BoolProperty(
        name="Reversed Order",
        description="Reverse the order images are loaded onto the sprite sheet",
        default=False
    )
    sprite_sheet_is_alpha: bpy.props.BoolProperty(
        name="Use Alpha",
        description="Use alpha channel in the generated sprite sheet",
        default=False
    )
    sprite_sheet_image_format: bpy.props.EnumProperty(
        name="",
        description="Choose the image format",
        items=image_formats
    )
    open_images: bpy.props.BoolProperty(
        name="Open In Image Viewer",
        description="Open the generated sprite sheets in the image viewer",
        default=False
    )
    open_output_directory: bpy.props.BoolProperty(
        name="Open Output Directory",
        description="Opens the output directory of the generated sprite sheets",
        default=False
    )
    clear_generated_images: bpy.props.BoolProperty(
        name="Clear Generated Images",
        description="Clears the generated images from blenders image viewer list",
        default=True
    )

class SpriteSheetCreatorPanel(Panel):
    bl_label = "Sprite Sheet Creator"
    bl_idname = "VIEW3D_PT_Sprite_Sheet_Creator"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'Sequenced Bake'

    def draw(self, context):
    
        layout = self.layout        
        scene = context.scene
        sprite_sheet_props = scene.sprite_sheet_props

        # Sprite Sheet Creator Section        
        box = layout.box()
        col = box.column(align=True)
        
        col.label(text="Image Sequence Direcotry:")
        col.prop(sprite_sheet_props, "directory")
        
        col.separator(factor=3.0, type='LINE')
        
        # Sprite Sheet Properties
        col.label(text="Sprite Sheet Properties:")
        
        col.prop(sprite_sheet_props, "columns")
        col.prop(sprite_sheet_props, "rows")        
        
        col.separator()
        
        col.prop(sprite_sheet_props, "image_width")
        col.prop(sprite_sheet_props, "image_height")
        
        col.separator()
        
        col.prop(sprite_sheet_props, "start_frame")
        col.prop(sprite_sheet_props, "end_frame")  
        
        col.separator()

        col.prop(sprite_sheet_props, "is_reversed")

        col.separator(factor=3.0, type='LINE')
        
        col.label(text="Image Format:")
        col.prop(sprite_sheet_props, "sprite_sheet_image_format")
        
        col.separator()
        
        col.prop(sprite_sheet_props, "sprite_sheet_is_alpha")
        col.prop(sprite_sheet_props, "open_images")
        col.prop(sprite_sheet_props, "open_output_directory")
        col.prop(sprite_sheet_props, "clear_generated_images")
        
        col.separator(factor=3.0, type='LINE')
        
        # Generate Sprite Sheet Button        
        col.operator("object.create_sprite_sheet", text="Generate Sprite Sheet")
        

class OBJECT_OT_CreateSpriteSheet(Operator):
    bl_label = "Generate Sprite Sheet"
    bl_idname = "object.create_sprite_sheet"
    _timer = None
    _subdirs = []
    _subdir_count = 0
    _current_index = 0
    _props = None
    _sb_props = None
    directory_name = ""
    
    def execute(self, context):
        self._props = context.scene.sprite_sheet_props
        self._sb_props = context.scene.sequence_bake_props

        # Get the sprite sheet directory
        directory = bpy.path.abspath(self._props.directory)
        if not directory:
            self.report({'WARNING'}, "No image sequence directory provided, Defaulting to Material Output Path.")
            directory = bpy.path.abspath(self._sb_props.sequenced_bake_output_path)
            if not directory:
                self.report({'ERROR'}, "A material output path was not provided.")
                return {"CANCELED"}

        # Check for subdirectories
        subdirs = [os.path.join(directory, subdir) for subdir in os.listdir(directory) if os.path.isdir(os.path.join(directory, subdir))]

        if subdirs:
            # If subdirectories are found, process them
            self._subdirs = subdirs
        else:
            # If no subdirectories, check for image files in the selected directory
            image_files = [f for f in os.listdir(directory) if os.path.isfile(os.path.join(directory, f))]
            self.directory_name = os.path.basename(os.path.normpath(directory))
            if image_files:
                # Treat the directory itself as a subdirectory
                self._subdirs = [directory]
            else:
                self.report({'ERROR'}, "No valid subdirectories or image sequences found in the selected directory.")
                return {"CANCELED"}

        self._subdir_count = len(self._subdirs)
        self._current_index = 0

        wm = context.window_manager
        self._timer = wm.event_timer_add(0.1, window=context.window)
        wm.modal_handler_add(self)
        return {'RUNNING_MODAL'}


    def modal(self, context, event):
        if event.type == 'ESC':
            # User pressed ESC, abort the process
            self.report({'INFO'}, "Process aborted by user")
            context.window_manager.event_timer_remove(self._timer)
            return {'CANCELLED'}
        
        if event.type == 'TIMER':
            if self._current_index < len(self._subdirs):
                subdir_path = self._subdirs[self._current_index]
                self.report({'INFO'}, f"Processing subdirectory: {subdir_path}") 
                self.process_subdir(subdir_path)
                self._current_index += 1
            else:
                self.report({'INFO'}, "Sprite Sheets Created Successfully")
                context.window_manager.event_timer_remove(self._timer)
                return {'FINISHED'}
        return {'PASS_THROUGH'}
        
    def open_images(self, image_paths):
        if not isinstance(image_paths, list):
            raise TypeError("image_paths must be a list of file paths.")
        
        for image_path in image_paths:
            if not os.path.isfile(image_path):
                self.report({'WARNING'}, f"File {image_path} does not exist.") 
                continue
            
            try:
                # For Windows
                if os.name == 'nt':
                    os.startfile(image_path)
                # For macOS
                elif os.name == 'posix' and 'darwin' in os.uname().sysname.lower():
                    subprocess.run(['open', image_path])
                # For Linux
                elif os.name == 'posix':
                    subprocess.run(['xdg-open', image_path])
                else:
                    raise OSError("Unsupported operating system")
            except Exception as e:
                self.report({'ERROR'}, f"An error occurred with file {image_path}: {e.args}") 
    
    def open_directory(self, file_path): 
        # Get the directory part of the provided path
        directory_path = os.path.dirname(file_path.replace('\\', '\\\\'))
        
        self.report({'INFO'}, f"Opening Directory: {directory_path}")  
        
        # Check the system and open the directory
        system = platform.system()        
        if system == "Windows":
            os.startfile(directory_path)        
        if system == "Darwin":  # macOS
            subprocess.run(["open", directory_path])
        if system == "Linux":
            subprocess.run(["xdg-open", directory_path])
   
    def remove_images():
        # Get the list of all images in the Blender file
        images = bpy.data.images
        
        # Regular expression pattern to match images with just a number or containing 'scaled_'
        pattern = re.compile(r'^\d+\.png$|scaled_')
        
        # Iterate through the images
        try:
            for image in list(images):
                if pattern.search(image.name):
                    print(f"Removing image: {image.name}")
                    bpy.data.images.remove(image)
        except Exception as err:
            print(f"remove_images: {err}")

    def process_subdir(self, subdir_path):
    
        file_names = os.listdir(subdir_path)
        
        # Filter and delte priviously generated sprite sheets before creating another one
        non_numeric_files = [f for f in file_names if not f.split('.')[0].isdigit()]
        if non_numeric_files:
            # Assuming we want to delete the first non-numeric file found
            file_to_delete = non_numeric_files[0]
            file_path = os.path.join(subdir_path, file_to_delete)
        
            # Delete the file
            os.remove(file_path)
        
        # Refresh the file list after removing any generated sprite sheets.
        file_names = os.listdir(subdir_path)
    
        # Get the images from the sub-directorys.
        image_files = [f for f in file_names]
        
        # Defined if the sequence is going to be reversed or not.
        is_reversed = self._props.is_reversed
        label_reversed = ""
        
        if is_reversed:
            label_reversed = "_Reversed"
        
        # Sort files numerically
        image_files_sorted = sorted(image_files, key=lambda x: int(x.split('.')[0]), reverse=is_reversed)
        
        # Debug info
        # print(f" ")
        # print(f"~~~~~~~~~~~~~~ LOADED IMAGES ~~~~~~~~~~~~~~")
        # print(f"Image File List Count: {len(image_files_sorted)}")
        # print(f"Image Files Sort Order: {image_files_sorted}")

        images = []
        for filename in image_files_sorted:
            img_path = os.path.join(subdir_path, filename)
            image = bpy.data.images.load(img_path)
            images.append(image)


        if not images:
            self.report({'WARNING'}, f"No images found in {subdir_path}, skipping.")  
            return {'CANCELLED'}
        
        # Get the current settings
        directory = bpy.path.abspath(self._props.directory) 
        if not directory:
            self.report({'ERROR'}, "No image sequence directory provided, Defaulting to Material Output Path.")            
            directory = bpy.path.abspath(self._sb_props.sequenced_bake_output_path)
            if not directory:
                self.report({'ERROR'}, "Material output was not provided")
                return {'CANCELLED'}

        # Get sprite sheet properties
        columns = self._props.columns
        rows = self._props.rows
        image_width = self._props.image_width
        image_height = self._props.image_height
        start_frame = self._props.start_frame
        end_frame = self._props.end_frame
        total_frames = end_frame - start_frame + 1
        sprite_sheet_is_alpha = self._props.sprite_sheet_is_alpha
        sprite_sheet_image_format = self._props.sprite_sheet_image_format
        open_images = self._props.open_images
        open_output_directory = self._props.open_output_directory
        clear_generated_images = self._props.clear_generated_images
        
        subdir_name = os.path.basename(subdir_path)
        if not subdir_name:
            subdir_name = self.directory_name
        
        # Create new sprite sheet image
        sprite_sheet = bpy.data.images.new(
            name=f"{subdir_name}_sprite_sheet",
            width=columns * image_width,
            height=rows * image_height,
            alpha=sprite_sheet_is_alpha
            )
            
        sprite_sheet.pixels = [0] * (columns * image_width * rows * image_height * 4)

        # Initialize pixels array
        pixels = np.zeros((rows * image_height, columns * image_width, 4), dtype=np.float32)
        
        # Positioning index for the sprite sheet
        position_index = 0

        for index, img in enumerate(images):
            
            # Add the images to the list.
            generated_images.append(img.name)
            
            if start_frame-1 <= index <= end_frame-1:                
                x = (position_index % columns) * image_width
                y = (position_index // columns) * image_height

                # Calculate scaling factors
                original_width, original_height = img.size
                scale_x = image_width / original_width
                scale_y = image_height / original_height

                # Create a new image for the scaled version
                scaled_image = bpy.data.images.new(f"scaled_{index}", width=image_width, height=image_height)
                scaled_pixels = np.zeros((image_height, image_width, 4), dtype=np.float32)
                
                # Add the generated image to the list.
                generated_images.append(scaled_image)
                
                # Load original image pixels
                original_pixels = np.array(img.pixels[:], dtype=np.float32).reshape((original_height, original_width, 4))
                
                for j in range(image_height):
                    for i in range(image_width):
                        src_x = min(int(i / scale_x), original_width - 1)
                        src_y = min(int(j / scale_y), original_height - 1)
                        scaled_pixels[j, i, :] = original_pixels[src_y, src_x, :]

                scaled_image.pixels = scaled_pixels.flatten()

                # Place the scaled image onto the sprite sheet
                pixels[pixels.shape[0] - y - image_height:pixels.shape[0] - y, x:x + image_width] = scaled_pixels
                
                # Increment the position index
                position_index += 1
                bpy.ops.wm.redraw_timer(type='DRAW_WIN_SWAP', iterations=1)

        # Update sprite sheet with new pixel data
        sprite_sheet.pixels = pixels.flatten()
            
        file_name = f"{subdir_name}_sprite_sheet{label_reversed}.{sprite_sheet_image_format}"
        
        print(f"File Name: {file_name}")
        
        sprite_sheet_path = os.path.join(directory, file_name)
        
        # generated_images.append(sprite_sheet_path)
        
        print(f"File Path: {sprite_sheet_path}")
        
        if os.path.exists(sprite_sheet_path):
            print(f"Path Exists: {sprite_sheet_path}")
            os.remove(sprite_sheet_path)
        
        sprite_sheet.filepath_raw = sprite_sheet_path
        sprite_sheet.save()
        
        # Clear the generated sprite sheets from the image list.
        if clear_generated_images:
            # Get the list of all images in the Blender file
            images = bpy.data.images
            
            # Regular expression pattern to match images with just a number or containing 'scaled_'
            pattern = re.compile(r'^\d+\.png(?:\.\d+)?$|scaled_')
            for image in list(images):
                if pattern.search(image.name):
                    bpy.data.images.remove(image)
        
        # Open the generated sprite sheet in the image viewer
        bpy.ops.image.open(filepath=sprite_sheet_path)
        self.report({'INFO'}, f"Sprite sheet created and saved at: {sprite_sheet_path}")
               
        if len(generated_images) == self._subdir_count:
            if open_images:
                self.open_images(generated_images)            
            
            if open_output_directory:
                self.open_directory(directory)                
            
            #Clear the list of image paths
            generated_images.clear()

