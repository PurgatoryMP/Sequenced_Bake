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
        Node,
        NodeSocket,
        PropertyGroup,
        )

image_formats = [
    ("png", "PNG", "Save as PNG"),
    ("jpeg", "JPEG", "Save as JPEG"),
    ("bmp", "BMP", "Save as BMP"),
    ("tiff", "TIFF", "Save as TIFF"),
    ("tga", "TGA", "Save as TGA"),
    ("openexr", "OpenEXR", "Save as OpenEXR"),
    ("hdr", "Radiance HDR", "Save as Radiance HDR"),
    ("cineon", "Cineon", "Save as Cineon"),
    ("dpx", "DPX", "Save as DPX")
]

generated_images = []

class SpriteSheetProperties(PropertyGroup):
    source_type: bpy.props.EnumProperty(
        name="",
        description="Choose where frames are sourced from",
        items=[
            ('DIRECTORY', "Image Sequence", "Use image files from a directory"),
            ('VSE', "Video Sequencer", "Use frames from the Video Sequencer"),
            ('COMPOSITOR', "Compositor Output", "Use frames rendered from the compositor"),
        ],
        default='DIRECTORY'
    )
    directory: bpy.props.StringProperty(
        name="",
        description="Source and Output directory for sprite sheets generated from an Image Sequence source.\nIf left blank will use the material output path",
        default="",
        maxlen=1024,
        subtype='DIR_PATH'
    )
    vse_output_path: bpy.props.StringProperty(
        name="",
        description="Output directory for sprite sheets generated from the Video Sequencer",
        default="",
        maxlen=1024,
        subtype='DIR_PATH'
    )
    vse_channel: bpy.props.IntProperty(
        name="VSE Channel",
        description="Only render strips from this Video Sequencer channel",
        default=1,
        min=1
    )
    use_all_vse_channels: bpy.props.BoolProperty(
        name="Use All Channels",
        description="Use all enabled VSE channels instead of a specific channel",
        default=False
    )
    compositor_output_path: bpy.props.StringProperty(
        name="",
        description="Output directory for sprite sheets generated from the Compositor",
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
    file_overwrite: bpy.props.BoolProperty(
        name="Overwrite file",
        description="Overwrites all sprite sheet files if they exists in the path.",
        default=True
    )
    file_name: bpy.props.StringProperty(
        name="",
        description="Name of the saved file.\nIf no name is entered the file name defaults to Object name, Material name, Sprite_sheet",
        default=""
    )
    

class SpriteSheetCreatorSocket(NodeSocket):
    bl_idname = 'SpriteSheetCreatorSocket'
    bl_label = 'Sprite Sheet Creator Socket'

    # Optional: define socket data type
    def draw(self, context, layout, node, text):
        layout.label(text=text)

    def draw_color(self, context, node):
        return (0.8, 0.8, 0.2, 1.0)  # Yellow color
        

class SpriteSheetCreatorNode(Node):
    bl_idname = 'ShaderNodeSpriteSheetCreatorNode'
    bl_label = 'Sprite Sheet Creator'
    bl_description = 'Create Sprite Sheets.'
    bl_icon = 'NODE'

    def init(self, context):
        self.width = 300
        # self.inputs.new("SpriteSheetCreatorSocket", "Input")
        # self.outputs.new("SpriteSheetCreatorSocket", "Output")
        
    def draw_buttons(self, context, layout):
           
        scene = context.scene
        option_padding = 2.0
        
        sprite_sheet_props = scene.sprite_sheet_props

        # Sprite Sheet Creator Section        
        box = layout.box()
        col = box.column(align=True)
        row = box.row(align=True)
        
        col.label(text="Source:")
        col.prop(sprite_sheet_props, "source_type")

        if sprite_sheet_props.source_type == 'DIRECTORY':
            col.separator()
            col.label(text="Image Sequence Directory:")
            col.prop(sprite_sheet_props, "directory")
            
        if sprite_sheet_props.source_type == 'VSE':
            col.separator()
            col.prop(sprite_sheet_props, "use_all_vse_channels")            
            if not sprite_sheet_props.use_all_vse_channels:
                col.separator()
                col.prop(sprite_sheet_props, "vse_channel")
        
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

        col.label(text="Output File Name:")

        row = col.row(align=True)  # New row for file name and extension
        row.prop(sprite_sheet_props, "file_name")
        row.prop(sprite_sheet_props, "sprite_sheet_image_format")
        
        col.separator()
        
        if sprite_sheet_props.source_type == 'VSE':  
            col.label(text="VSE Output Directory:")
            col.prop(sprite_sheet_props, "vse_output_path")
            
        if sprite_sheet_props.source_type == 'COMPOSITOR':
            col.separator()
            col.label(text="Compositor Output Directory:")
            col.prop(sprite_sheet_props, "compositor_output_path")
        
        col.separator()

        col.prop(sprite_sheet_props, "file_overwrite")
        
        col.separator(factor=3.0, type='LINE')
        
        col.prop(sprite_sheet_props, "sprite_sheet_is_alpha")
        col.prop(sprite_sheet_props, "open_images")
        col.prop(sprite_sheet_props, "open_output_directory")
        col.prop(sprite_sheet_props, "clear_generated_images")
        
        col.separator(factor=3.0, type='LINE')
        
        # Generate Sprite Sheet Button        
        col.operator("object.create_sprite_sheet", text="Generate Sprite Sheet")
        
        
class SpriteSheetCreatorVSEPanel(Panel):
    bl_label = "Sprite Sheet Creator"
    bl_idname = "VSE_PT_Sprite_Sheet_Creator"
    bl_space_type = "SEQUENCE_EDITOR"
    bl_region_type = "UI"
    bl_category = "Sprite Sheet Creator"

    def draw(self, context):
    
        layout = self.layout        
        scene = context.scene
        sprite_sheet_props = scene.sprite_sheet_props

        # Sprite Sheet Creator Section        
        box = layout.box()
        col = box.column(align=True)
        row = box.row(align=True)
        
        col.label(text="Source:")
        col.prop(sprite_sheet_props, "source_type")

        if sprite_sheet_props.source_type == 'DIRECTORY':
            col.separator()
            col.label(text="Image Sequence Directory:")
            col.prop(sprite_sheet_props, "directory")
            
        if sprite_sheet_props.source_type == 'VSE':
            col.prop(sprite_sheet_props, "use_all_vse_channels")            
            if not sprite_sheet_props.use_all_vse_channels:
                col.prop(sprite_sheet_props, "vse_channel")
                        
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

        col.label(text="Output File Name:")

        row = col.row(align=True)  # New row for file name and extension
        row.prop(sprite_sheet_props, "file_name")
        row.prop(sprite_sheet_props, "sprite_sheet_image_format")
        
        col.separator()
        
        if sprite_sheet_props.source_type == 'VSE':  
            col.label(text="VSE Output Directory:")
            col.prop(sprite_sheet_props, "vse_output_path")
            
        if sprite_sheet_props.source_type == 'COMPOSITOR':
            col.separator()
            col.label(text="Compositor Output Directory:")
            col.prop(sprite_sheet_props, "compositor_output_path")
            
        col.separator()

        col.prop(sprite_sheet_props, "file_overwrite")
        
        # col.label(text="Image Format:")
        # row.prop(sprite_sheet_props, "sprite_sheet_image_format")
        
        col.separator(factor=3.0, type='LINE')
        
        col.prop(sprite_sheet_props, "sprite_sheet_is_alpha")
        col.prop(sprite_sheet_props, "open_images")
        col.prop(sprite_sheet_props, "open_output_directory")
        col.prop(sprite_sheet_props, "clear_generated_images")
        
        col.separator(factor=3.0, type='LINE')
        
        # Generate Sprite Sheet Button        
        col.operator("object.create_sprite_sheet", text="Generate Sprite Sheet")
        

class SpriteSheetCreatorPanel(Panel):
    bl_label = "Sprite Sheet Creator"
    bl_idname = "VIEW3D_PT_Sprite_Sheet_Creator"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Sequenced Bake"

    def draw(self, context):
    
        layout = self.layout        
        scene = context.scene
        sprite_sheet_props = scene.sprite_sheet_props

        # Sprite Sheet Creator Section        
        box = layout.box()
        col = box.column(align=True)
        row = box.row(align=True)
        
        col.label(text="Source:")
        col.prop(sprite_sheet_props, "source_type")

        if sprite_sheet_props.source_type == 'DIRECTORY':
            col.separator()
            col.label(text="Image Sequence Directory:")
            col.prop(sprite_sheet_props, "directory")
            
        if sprite_sheet_props.source_type == 'VSE':
            col.prop(sprite_sheet_props, "use_all_vse_channels")            
            if not sprite_sheet_props.use_all_vse_channels:
                col.prop(sprite_sheet_props, "vse_channel")
                
        
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

        col.label(text="Output File Name:")

        row = col.row(align=True)  # New row for file name and extension
        row.prop(sprite_sheet_props, "file_name")
        row.prop(sprite_sheet_props, "sprite_sheet_image_format")
        
        col.separator()
        
        if sprite_sheet_props.source_type == 'VSE':  
            col.label(text="VSE Output Directory:")
            col.prop(sprite_sheet_props, "vse_output_path")
            
        if sprite_sheet_props.source_type == 'COMPOSITOR':
            col.separator()
            col.label(text="Compositor Output Directory:")
            col.prop(sprite_sheet_props, "compositor_output_path")
            
        col.separator()

        col.prop(sprite_sheet_props, "file_overwrite")
        
        col.separator(factor=3.0, type='LINE')
        
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
        self._sb_props = context.scene.sequenced_bake_props

        if self._props.source_type == 'DIRECTORY':
            return self.execute_directory(context)
        elif self._props.source_type == 'VSE':
            return self.execute_vse(context)
        elif self._props.source_type == 'COMPOSITOR':
            return self.execute_compositor(context)
        
    def execute_directory(self, context):
        # Get the sprite sheet directory
        props = self._props
        if props.source_type == 'VSE':
            directory = bpy.path.abspath(props.vse_output_path)
        else:
            directory = bpy.path.abspath(props.directory)

        directory = bpy.path.abspath(self._props.directory)

        if not directory:
            self.report({'ERROR'}, "No image sequence directory specified")
            return {'CANCELLED'}

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
        
    def execute_vse(self, context):
        # Safety: ensure no modal timer is running
        if not self._props.vse_output_path:
            self.report({'ERROR'}, "VSE Output Path is required")
            return {'CANCELLED'}
    
        if self._timer:
            context.window_manager.event_timer_remove(self._timer)
            self._timer = None

        images = self.load_vse_frames(context)

        if self._props.is_reversed:
            images.reverse()

        return self.process_images(images, "VSE")
        
    def execute_compositor(self, context):
        props = self._props
        sb_props = self._sb_props

        if not props.compositor_output_path:
            self.report({'ERROR'}, "Compositor Output Path is required")
            return {'CANCELLED'}

        images = self.load_compositor_frames(context)

        if props.is_reversed:
            images.reverse()

        return self.process_images(images, "COMPOSITOR")
        
    
    def load_compositor_frames(self, context):
        scene = context.scene
        start = self._props.start_frame
        end = self._props.end_frame

        images = []

        output_dir = bpy.path.abspath(self._props.compositor_output_path)
        os.makedirs(output_dir, exist_ok=True)

        # Store original render settings
        original_filepath = scene.render.filepath
        original_format = scene.render.image_settings.file_format
        original_res_x = scene.render.resolution_x
        original_res_y = scene.render.resolution_y
        original_res_percent = scene.render.resolution_percentage

        # Set render settings to match sprite sheet cell
        scene.render.image_settings.file_format = 'PNG'
        scene.render.resolution_x = self._props.image_width
        scene.render.resolution_y = self._props.image_height
        scene.render.resolution_percentage = 100

        for frame in range(start, end + 1):
            scene.frame_set(frame)
            temp_path = os.path.join(output_dir, f"compositor_frame_{frame:05d}.png")
            scene.render.filepath = temp_path

            # Render frame at correct size
            bpy.ops.render.render(write_still=True)

            if os.path.exists(temp_path):
                img = bpy.data.images.load(temp_path)
                img.name = f"Compositor_Frame_{frame}"
                images.append(img)
            else:
                self.report({'WARNING'}, f"Failed to render compositor frame {frame}")

        # Restore original render settings
        scene.render.filepath = original_filepath
        scene.render.image_settings.file_format = original_format
        scene.render.resolution_x = original_res_x
        scene.render.resolution_y = original_res_y
        scene.render.resolution_percentage = original_res_percent

        return images
    
    def load_vse_frames(self, context):
        scene = context.scene
        props = self._props

        start = props.start_frame
        end = props.end_frame
        channel = props.vse_channel

        images = []

        # Ensure sequence editor exists
        seq = scene.sequence_editor
        if seq is None:
            seq = scene.sequence_editor_create()

        # Get all strips
        strips = seq.strips_all
        if not strips:
            self.report({'ERROR'}, "No strips found in the Video Sequencer")
            return images

        # Determine which strips to use
        if props.use_all_vse_channels:
            strips_to_render = [s for s in strips if not s.mute]  # all enabled strips
        else:
            strips_to_render = [s for s in strips if s.channel == channel]

        if not strips_to_render:
            msg = "No strips found in the VSE"
            msg += "" if props.use_all_vse_channels else f" channel {channel}"
            self.report({'ERROR'}, msg)
            return images

        # Store original mute states if using a specific channel
        original_mute = {}
        if not props.use_all_vse_channels:
            for strip in strips:
                original_mute[strip] = strip.mute
                strip.mute = (strip.channel != channel)

        temp_dir = bpy.app.tempdir
        os.makedirs(temp_dir, exist_ok=True)

        original_filepath = scene.render.filepath
        original_format = scene.render.image_settings.file_format
        scene.render.image_settings.file_format = 'PNG'

        try:
            for frame in range(start, end + 1):
                scene.frame_set(frame)
                temp_path = os.path.join(temp_dir, f"vse_frame_{frame:05d}.png")
                scene.render.filepath = temp_path

                bpy.ops.render.render(write_still=True)

                if os.path.exists(temp_path):
                    img = bpy.data.images.load(temp_path)
                    img.name = f"VSE_Frame_{frame}"
                    images.append(img)
                else:
                    self.report({'WARNING'}, f"Failed to render VSE frame {frame}")

        finally:
            # Restore render settings
            scene.render.filepath = original_filepath
            scene.render.image_settings.file_format = original_format

            # Restore mute states if using a single channel
            if not props.use_all_vse_channels:
                for strip, mute in original_mute.items():
                    strip.mute = mute

        return images
        

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
            self.report({'INFO'}, f"remove_images: {err}")
    
    def process_images(self, images, output_name):
        if not images:
            self.report({'WARNING'}, "No images provided to process_images()")
            return {'CANCELLED'}

        props = self._props
        sb_props = self._sb_props

        # Resolve output directory
        if props.source_type == 'DIRECTORY':
            directory = bpy.path.abspath(props.directory)
        elif props.source_type == 'VSE':
            directory = bpy.path.abspath(props.vse_output_path)
        elif props.source_type == 'COMPOSITOR':
            directory = bpy.path.abspath(props.compositor_output_path)
        else:
            directory = bpy.path.abspath(props.directory)

        if not directory:
            self.report({'ERROR'}, "No output directory specified")
            return {'CANCELLED'}

        columns = props.columns
        rows = props.rows
        image_width = props.image_width
        image_height = props.image_height
        start_frame = props.start_frame
        end_frame = props.end_frame
        sprite_sheet_is_alpha = props.sprite_sheet_is_alpha
        sprite_sheet_image_format = props.sprite_sheet_image_format
        open_images = props.open_images
        open_output_directory = props.open_output_directory
        clear_generated_images = props.clear_generated_images

        label_reversed = "_Reversed" if props.is_reversed else ""

        # Clamp frame range
        start_index = max(0, start_frame - 1)
        end_index = min(len(images) - 1, end_frame - 1)

        # Create sprite sheet image
        sprite_sheet = bpy.data.images.new(
            name=f"{output_name}_sprite_sheet",
            width=columns * image_width,
            height=rows * image_height,
            alpha=sprite_sheet_is_alpha
        )

        sprite_sheet.pixels = [0.0] * (columns * image_width * rows * image_height * 4)

        pixels = np.zeros(
            (rows * image_height, columns * image_width, 4),
            dtype=np.float32
        )

        position_index = 0

        for index in range(start_index, end_index + 1):
            if position_index >= columns * rows:
                break

            img = images[index]
            generated_images.append(img.name)

            x = (position_index % columns) * image_width
            y = (position_index // columns) * image_height

            original_width, original_height = img.size
            scale_x = image_width / original_width
            scale_y = image_height / original_height

            scaled_image = bpy.data.images.new(
                name=f"scaled_{output_name}_{index}",
                width=image_width,
                height=image_height,
                alpha=True
            )

            generated_images.append(scaled_image.name)

            original_pixels = np.array(
                img.pixels[:],
                dtype=np.float32
            ).reshape((original_height, original_width, 4))

            scaled_pixels = np.zeros(
                (image_height, image_width, 4),
                dtype=np.float32
            )

            for j in range(image_height):
                for i in range(image_width):
                    src_x = min(int(i / scale_x), original_width - 1)
                    src_y = min(int(j / scale_y), original_height - 1)
                    scaled_pixels[j, i] = original_pixels[src_y, src_x]

            scaled_image.pixels = scaled_pixels.flatten()

            pixels[
                pixels.shape[0] - y - image_height : pixels.shape[0] - y,
                x : x + image_width
            ] = scaled_pixels

            position_index += 1

        sprite_sheet.pixels = pixels.flatten()

        # File naming
        filename = props.file_name.strip()
        if not filename:
            base_name = f"{output_name}_SpriteSheet{label_reversed}"
        else:
            base_name = filename

        if base_name.lower().endswith(f".{sprite_sheet_image_format}"):
            base_name = os.path.splitext(base_name)[0]

        ext = f".{sprite_sheet_image_format}"
        sprite_sheet_path = os.path.join(directory, base_name + ext)

        # Overwrite handling
        if os.path.exists(sprite_sheet_path) and not props.file_overwrite:
            counter = 1
            new_base = base_name
            while os.path.exists(os.path.join(directory, new_base + ext)):
                new_base = f"{base_name} ({counter})"
                counter += 1
            sprite_sheet_path = os.path.join(directory, new_base + ext)

        sprite_sheet.filepath_raw = sprite_sheet_path
        sprite_sheet.save()

        if clear_generated_images:
            pattern = re.compile(r'^scaled_')
            for image in list(bpy.data.images):
                if pattern.search(image.name):
                    bpy.data.images.remove(image)

        bpy.ops.image.open(filepath=sprite_sheet_path)

        if open_output_directory:
            self.open_directory(sprite_sheet_path)

        self.report({'INFO'}, f"Sprite sheet saved: {sprite_sheet_path}")
        generated_images.clear()

        return {'FINISHED'}


    def process_subdir(self, subdir_path):
        file_names = os.listdir(subdir_path)

        image_files = []
        for f in file_names:
            name, _ = os.path.splitext(f)
            try:
                int(name)
                image_files.append(f)
            except ValueError:
                continue

        if not image_files:
            self.report({'WARNING'}, f"No images found in {subdir_path}")
            return {'CANCELLED'}

        image_files_sorted = sorted(
            image_files,
            key=lambda x: int(os.path.splitext(x)[0]),
            reverse=self._props.is_reversed
        )

        images = []
        for filename in image_files_sorted:
            img_path = os.path.join(subdir_path, filename)
            images.append(bpy.data.images.load(img_path))

        output_name = os.path.basename(subdir_path) or self.directory_name

        return self.process_images(images, output_name)

