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


bl_info = {
    "name": "Sequenced Bake",
    "author": "Anthony OConnell",
    "version": (1, 0, 2),
    "blender": (4, 2, 0),
    "location": "View3D > Sidebar > Sequenced Bake",
    "description": "Tools for baking material sequences and generating sprite sheets",
    "category": "3D View"
}

import bpy
import os
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
        description="Select the directory containing subdirectories of images",
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
    is_alpha: bpy.props.BoolProperty(
        name="Use Alpha",
        description="Use alpha channel in the generated sprite sheet",
        default=False
    )
    image_format: bpy.props.EnumProperty(
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

class SequencedBakePanel(Panel):
    bl_label = "{} v{}".format("Sequenced Bake", bl_info["version"])
    bl_idname = "VIEW3D_PT_sequenced_bake"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'Sequenced Bake'

    def draw(self, context):
    
        layout = self.layout        
        scene = context.scene
        props = scene.sprite_sheet_props

        # Output Path
        box = layout.box()
        col = box.column(align=True)
        col.label(text="Material Output Path:")
        col.prop(context.scene, "sequenced_bake_output_path", text="")
        
        col.separator(factor=3.0, type='LINE')
        
        # Generated Image Size
        col.label(text="Generated Image Size:")
        row = col.row(align=True)
        row.prop(context.scene, "sequenced_bake_width")
        row.prop(context.scene, "sequenced_bake_height")
        
        col.separator(factor=3.0, type='LINE')
        
        # Bake Type Options
        col.label(text="Bake Type Options:")
        col.prop(context.scene, "sequenced_bake_normal", text="Normal")
        col.prop(context.scene, "sequenced_bake_roughness", text="Roughness")
        col.prop(context.scene, "sequenced_bake_glossy", text="Glossy")
        col.prop(context.scene, "sequenced_bake_emission", text="Emission")
        col.prop(context.scene, "sequenced_bake_ambient_occlusion", text="Ambient Occlusion")
        col.prop(context.scene, "sequenced_bake_shadow", text="Shadow")
        col.prop(context.scene, "sequenced_bake_position", text="Position")
        col.prop(context.scene, "sequenced_bake_uv", text="UV")
        col.prop(context.scene, "sequenced_bake_environment", text="Environment")
        col.prop(context.scene, "sequenced_bake_diffuse", text="Diffuse")
        col.prop(context.scene, "sequenced_bake_transmission", text="Transmission")
        col.prop(context.scene, "sequenced_bake_combined", text="Combined")
        
        col.separator(factor=3.0, type='LINE')
        
        # Baking Button
        col.operator("sequenced_bake.bake", text="Bake Material Sequence")  
        
        # Sprite Sheet Creator Section        
        box = layout.box()
        col = box.column(align=True)
        col.label(text="Sprite Sheet Creator:")
        
        col.separator()
        
        col.label(text="Image Sequence Direcotry:")
        col.prop(props, "directory")
        
        col.separator(factor=3.0, type='LINE')
        
        # Sprite Sheet Properties
        col.label(text="Sprite Sheet Properties:")
        
        col.prop(props, "columns")
        col.prop(props, "rows")        
        
        col.separator()
        
        col.prop(props, "image_width")
        col.prop(props, "image_height")
        
        col.separator()
        
        col.prop(props, "start_frame")
        col.prop(props, "end_frame")  
        
        col.separator()

        col.prop(props, "is_reversed")

        col.separator(factor=3.0, type='LINE')
        
        col.label(text="Image Format:")
        col.prop(props, "image_format")
        
        col.separator()
        
        col.prop(props, "is_alpha")
        col.prop(props, "open_images")
        col.prop(props, "open_output_directory")
        
        col.separator(factor=3.0, type='LINE')
        
        # Generate Sprite Sheet Button        
        col.operator("object.create_sprite_sheet", text="Generate Sprite Sheet")
        

class OBJECT_OT_CreateSpriteSheet(Operator):
    bl_label = "Generate Sprite Sheet"
    bl_idname = "object.create_sprite_sheet"
    _timer = None
    _subdirs = []
    _current_index = 0
    _props = None

    def execute(self, context):
        self._props = context.scene.sprite_sheet_props
        
        directory = self._props.directory
        if not directory:
            print(f"No image sequence directory provided, Defaulting to Material Output Path.")            
            directory = bpy.context.scene.sequenced_bake_output_path
            if not directory:
                print("Material output path provided.")
                return
        
        self._subdirs = [os.path.join(directory, subdir) for subdir in os.listdir(directory) if os.path.isdir(os.path.join(directory, subdir))]
        self._current_index = 0
        
        wm = context.window_manager
        self._timer = wm.event_timer_add(0.1, window=context.window)
        wm.modal_handler_add(self)
        return {'RUNNING_MODAL'}

    def modal(self, context, event):
        if event.type == 'TIMER':
            if self._current_index < len(self._subdirs):
                subdir_path = self._subdirs[self._current_index]
                print(f"Processing subdirectory: {subdir_path}")
                self.process_subdir(subdir_path)
                self._current_index += 1
            else:
                print("Sprite Sheets Created Successfully")
                self.report({'INFO'}, "Sprite Sheets Created Successfully")
                context.window_manager.event_timer_remove(self._timer)
                return {'FINISHED'}
        return {'PASS_THROUGH'}
        
    def open_images(self, image_paths):
        if not isinstance(image_paths, list):
            raise TypeError("image_paths must be a list of file paths.")
        
        for image_path in image_paths:
            if not os.path.isfile(image_path):
                print(f"File {image_path} does not exist.")
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
                print(f"An error occurred with file {image_path}: {e.args}")
    
    def open_directory(self, file_path): 
        # Get the directory part of the provided path
        directory_path = os.path.dirname(file_path.replace('\\', '\\\\'))
        
        print(f"Opening Directory: {directory_path}")
        
        # Check the system and open the directory
        system = platform.system()        
        if system == "Windows":
            os.startfile(directory_path)        
        if system == "Darwin":  # macOS
            subprocess.run(["open", directory_path])
        if system == "Linux":
            subprocess.run(["xdg-open", directory_path])

    def process_subdir(self, subdir_path):
    
        file_names = os.listdir(subdir_path)
    
        # Filter out only image files (assuming they are .png, .jpg, etc.)
        image_files = [f for f in file_names if f.endswith(('png', 'jpg', 'jpeg'))]
        
        is_reversed = self._props.is_reversed
        label_reversed = ""
        
        if is_reversed:
            label_reversed = "_Reversed"
        
        # Sort files numerically
        image_files_sorted = sorted(image_files, key=lambda x: int(x.split('.')[0]), reverse=is_reversed)
        
        print(f" ")
        print(f"~~~~~~~~~~~~~~ LOADED IMAGES ~~~~~~~~~~~~~~")
        print(f"Image File List Count: {len(image_files_sorted)}")
        print(f"Image Files Sort Order: {image_files_sorted}")

        images = []
        for filename in image_files_sorted:
            if filename.endswith(('.png', '.jpg', '.jpeg')):
                img_path = os.path.join(subdir_path, filename)
                image = bpy.data.images.load(img_path)
                images.append(image)


        if not images:
            print(f"No images found in {subdir_path}, skipping.")
            return
        
        # Get the current settings.
        directory = self._props.directory
        if not directory:
            print(f"No image sequence directory provided, Defaulting to Material Output Path.")            
            directory = bpy.context.scene.sequenced_bake_output_path
            if not directory:
                print("Material output path provided.")
                return
                
        columns = self._props.columns
        rows = self._props.rows
        image_width = self._props.image_width
        image_height = self._props.image_height
        start_frame = self._props.start_frame
        end_frame = self._props.end_frame
        total_frames = end_frame - start_frame + 1
        is_alpha = self._props.is_alpha
        image_format = self._props.image_format
        open_images = self._props.open_images
        open_output_directory = self._props.open_output_directory
        
        # Create new sprite sheet image
        sprite_sheet = bpy.data.images.new(
            name=f"{os.path.basename(subdir_path)}_sprite_sheet",
            width=columns * image_width,
            height=rows * image_height,
            alpha=is_alpha
            )
            
        sprite_sheet.pixels = [0] * (columns * image_width * rows * image_height * 4)

        # Initialize pixels array
        pixels = np.zeros((rows * image_height, columns * image_width, 4), dtype=np.float32)
        
        # Positioning index for the sprite sheet
        position_index = 0

        for index, img in enumerate(images):
            #print(f"Frame: {index}")
            
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

        # Update sprite sheet with new pixel data
        sprite_sheet.pixels = pixels.flatten()
        
        file_name = f"{os.path.basename(subdir_path)}_sprite_sheet{label_reversed}.{image_format}"
                
        sprite_sheet_path = os.path.join(directory, file_name)
        
        generated_images.append(sprite_sheet_path)
        
        if os.path.exists(sprite_sheet_path):
            os.remove(sprite_sheet_path)
        
        sprite_sheet.filepath_raw = sprite_sheet_path
        sprite_sheet.save()
        
        for img in bpy.data.images:
            if img.name not in generated_images:
                bpy.data.images.remove(img)
        
        # Open the generated sprite sheet in the image viewer.
        bpy.ops.image.open(filepath=sprite_sheet_path)
        print(f"Sprite sheet created and saved at: {sprite_sheet_path}")
               
        # if our list of images contains 3 images.
        
        if len(generated_images) == 3:
            if open_images:
                self.open_images(generated_images)            
            if open_output_directory:
                self.open_directory(directory)
                
            # Clear the list of image paths.
            generated_images.clear()
    
class SequencedBakeOperator(Operator):
    bl_idname = "sequenced_bake.bake"
    bl_label = "Sequenced Bake"
    bl_description = "Start the sequenced baking process"

    def execute(self, context):

        # Define the root directory.
        root_directory = bpy.context.scene.sequenced_bake_output_path

        # Define the bake types to bake out
        bake_types = []
        if bpy.context.scene.sequenced_bake_normal:
            bake_types.append('NORMAL')
        if bpy.context.scene.sequenced_bake_roughness:
            bake_types.append('ROUGHNESS')
        if bpy.context.scene.sequenced_bake_glossy:
            bake_types.append('GLOSSY')
        if bpy.context.scene.sequenced_bake_emission:
            bake_types.append('Emission')
        if bpy.context.scene.sequenced_bake_ambient_occlusion:
            bake_types.append('Ambient Occlusion')
        if bpy.context.scene.sequenced_bake_shadow:
            bake_types.append('SHADOW')
        if bpy.context.scene.sequenced_bake_position:
            bake_types.append('POSITION')
        if bpy.context.scene.sequenced_bake_uv:
            bake_types.append('UV')
        if bpy.context.scene.sequenced_bake_environment:
            bake_types.append('ENVIRONMENT')
        if bpy.context.scene.sequenced_bake_diffuse:
            bake_types.append('DIFFUSE')
        if bpy.context.scene.sequenced_bake_transmission:
            bake_types.append('TRANSMISSION')
        if bpy.context.scene.sequenced_bake_combined:
            bake_types.append('COMBINED')

        # Get the current frame range
        frame_range = range(bpy.context.scene.frame_start, bpy.context.scene.frame_end + 1)

        # Get the active object
        obj = bpy.context.active_object

        # Get the active material
        mat = obj.active_material

        # Define the image size
        image_width = bpy.context.scene.sequenced_bake_width
        image_height = bpy.context.scene.sequenced_bake_height

        # Define the function to remove the generated texture node rather than removing all the texture nodes
        def remove_generated_texture_node():
            material = bpy.context.active_object.active_material
            if material and material.node_tree:
                node_tree = material.node_tree
                nodes_to_remove = []
                for node in node_tree.nodes:
                    if node.type == 'TEX_IMAGE':
                        nodes_to_remove.append(node)
                for node in nodes_to_remove:
                    node_tree.nodes.remove(node)

        # Clear any existing image textures
        for image in bpy.data.images:
            if image.users == 0:
                bpy.data.images.remove(image)

        def bake_maps(bake_type):
            # Call the function to remove the generated texture node
            remove_generated_texture_node()

            for frame in frame_range:
                # Set the frame and update the scene
                bpy.context.scene.frame_set(frame)
                bpy.context.view_layer.update()

                # Create a new texture for the Image Texture node
                texture = bpy.data.images.new(name=bake_type, width=image_width, height=image_height, alpha=True)

                # Create a new Image Texture node
                image_node = mat.node_tree.nodes.new('ShaderNodeTexImage')
                
                # Set node position
                image_node.location = (400, -200)
                image_node.image = texture

                # Select the new Image Texture node
                mat.node_tree.nodes.active = image_node

                # Bake the texture
                bpy.ops.object.bake(type=bake_type)

                # Define the output path
                image_path = os.path.join(root_directory, bake_type, str(frame) + '.png')

                # Save the rendered image
                texture.save_render(image_path)
                
                # Update the Blender interface
                bpy.ops.wm.redraw_timer(type='DRAW_WIN_SWAP', iterations=1)

        # Start baking the different material map sequences
        for bake_type in bake_types:
            bake_directory = os.path.join(root_directory, bake_type)
            os.makedirs(bake_directory, exist_ok=True)

            # Begin baking
            bake_maps(bake_type)
            bpy.ops.wm.redraw_timer(type='DRAW_WIN_SWAP', iterations=1)

        # Call the function to remove the generated texture node
        remove_generated_texture_node()

        # Clear any existing image textures
        for image in bpy.data.images:
            if image.users == 0:
                bpy.data.images.remove(image)

        self.report({'INFO'}, "Sequenced bake completed successfully")
        return {'FINISHED'}


def register():
    bpy.types.Scene.sequenced_bake_output_path = bpy.props.StringProperty(
        name="Output Path", 
        subtype='DIR_PATH',
        description='Define the output path for the rendered images'
    )
    bpy.types.Scene.sequenced_bake_width = bpy.props.IntProperty(
        name="Width", default=1024, min=1, max=4096
    )
    bpy.types.Scene.sequenced_bake_height = bpy.props.IntProperty(
        name="Height", default=1024, min=1, max=4096
    )

    bpy.types.Scene.sequenced_bake_normal = bpy.props.BoolProperty(name="Normal")
    bpy.types.Scene.sequenced_bake_roughness = bpy.props.BoolProperty(name="Roughness")
    bpy.types.Scene.sequenced_bake_glossy = bpy.props.BoolProperty(name="Glossy")
    bpy.types.Scene.sequenced_bake_emission = bpy.props.BoolProperty(name="Emission")
    bpy.types.Scene.sequenced_bake_ambient_occlusion = bpy.props.BoolProperty(name="Ambient Occlusion")
    bpy.types.Scene.sequenced_bake_shadow = bpy.props.BoolProperty(name="Shadow")
    bpy.types.Scene.sequenced_bake_position = bpy.props.BoolProperty(name="Position")
    bpy.types.Scene.sequenced_bake_uv = bpy.props.BoolProperty(name="UV")
    bpy.types.Scene.sequenced_bake_environment = bpy.props.BoolProperty(name="Environment")
    bpy.types.Scene.sequenced_bake_diffuse = bpy.props.BoolProperty(name="Diffuse")
    bpy.types.Scene.sequenced_bake_transmission = bpy.props.BoolProperty(name="Transmission")
    bpy.types.Scene.sequenced_bake_combined = bpy.props.BoolProperty(name="Combined")
    
    bpy.utils.register_class(SequencedBakePanel)
    bpy.utils.register_class(SequencedBakeOperator)
    bpy.utils.register_class(SpriteSheetProperties)
    bpy.types.Scene.sprite_sheet_props = bpy.props.PointerProperty(type=SpriteSheetProperties)
    bpy.utils.register_class(OBJECT_OT_CreateSpriteSheet)


def unregister():
    bpy.utils.unregister_class(SequencedBakePanel)
    bpy.utils.unregister_class(SequencedBakeOperator)
    bpy.utils.unregister_class(SpriteSheetProperties)
    bpy.utils.unregister_class(OBJECT_OT_CreateSpriteSheet)

    del bpy.types.Scene.sequenced_bake_output_path
    del bpy.types.Scene.sequenced_bake_width
    del bpy.types.Scene.sequenced_bake_height

    del bpy.types.Scene.sequenced_bake_normal
    del bpy.types.Scene.sequenced_bake_roughness
    del bpy.types.Scene.sequenced_bake_glossy
    del bpy.types.Scene.sequenced_bake_emission
    del bpy.types.Scene.sequenced_bake_ambient_occlusion
    del bpy.types.Scene.sequenced_bake_shadow
    del bpy.types.Scene.sequenced_bake_position
    del bpy.types.Scene.sequenced_bake_uv
    del bpy.types.Scene.sequenced_bake_environment
    del bpy.types.Scene.sequenced_bake_diffuse
    del bpy.types.Scene.sequenced_bake_transmission
    del bpy.types.Scene.sequenced_bake_combined
    del bpy.types.Scene.sprite_sheet_props
    


if __name__ == "__main__":
    register()
