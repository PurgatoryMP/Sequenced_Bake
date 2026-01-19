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
from bpy.types import PropertyGroup


IMAGE_FORMATS = [
    ("png", "PNG", "Save as PNG"),
    ("jpeg", "JPEG", "Save as JPEG"),
    ("bmp", "BMP", "Save as BMP"),
    ("tiff", "TIFF", "Save as TIFF"),
    ("tga", "TGA", "Save as TGA"),
    ("openexr", "OpenEXR", "Save as OpenEXR"),
    ("hdr", "Radiance HDR", "Save as Radiance HDR"),
    ("cineon", "Cineon", "Save as Cineon"),
    ("dpx", "DPX", "Save as DPX"),
]


class SpriteSheetProperties(PropertyGroup):

    source_type: bpy.props.EnumProperty(
        name="Source",
        description="Choose where frames are sourced from",
        items=[
            ('DIRECTORY', "Image Sequence", "Use image files from a directory"),
            ('VSE', "Video Sequencer", "Use frames from the Video Sequencer"),
            ('COMPOSITOR', "Compositor Output", "Use frames rendered from the compositor"),
        ],
        default='DIRECTORY'
    )

    # ---------- Paths ----------

    directory: bpy.props.StringProperty(
        name="Image Directory",
        description=(
            "Source and output directory for Image Sequence sprite sheets.\n"
            "If left blank, the material output path is used"
        ),
        default="",
        maxlen=1024,
        subtype='DIR_PATH'
    )

    vse_output_path: bpy.props.StringProperty(
        name="VSE Output Path",
        description="Output directory for sprite sheets generated from the Video Sequencer",
        default="",
        maxlen=1024,
        subtype='DIR_PATH'
    )

    compositor_output_path: bpy.props.StringProperty(
        name="Compositor Output Path",
        description="Output directory for sprite sheets generated from the Compositor",
        default="",
        maxlen=1024,
        subtype='DIR_PATH'
    )

    # ---------- VSE ----------

    vse_channel: bpy.props.IntProperty(
        name="VSE Channel",
        description="Only render strips from this Video Sequencer channel",
        default=1,
        min=1
    )

    use_all_vse_channels: bpy.props.BoolProperty(
        name="Use All Channels",
        description="Use all enabled Video Sequencer channels",
        default=False
    )

    # ---------- Sprite Sheet Layout ----------

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
        description="Width of each sprite cell",
        default=128,
        min=1
    )

    image_height: bpy.props.IntProperty(
        name="Cell Height",
        description="Height of each sprite cell",
        default=128,
        min=1
    )

    # ---------- Frame Range ----------

    start_frame: bpy.props.IntProperty(
        name="Start Frame",
        description="First frame to include",
        default=1,
        min=1
    )

    end_frame: bpy.props.IntProperty(
        name="End Frame",
        description="Last frame to include",
        default=64,
        min=1
    )

    is_reversed: bpy.props.BoolProperty(
        name="Reverse Order",
        description="Reverse the order frames are processed",
        default=False
    )

    # ---------- Output ----------

    sprite_sheet_is_alpha: bpy.props.BoolProperty(
        name="Use Alpha",
        description="Include alpha channel in the sprite sheet",
        default=False
    )

    sprite_sheet_image_format: bpy.props.EnumProperty(
        name="Image Format",
        description="Output image format",
        items=IMAGE_FORMATS,
        default="png"
    )

    file_name: bpy.props.StringProperty(
        name="File Name",
        description=(
            "Output file name.\n"
            "If empty, a default name is generated"
        ),
        default=""
    )

    file_overwrite: bpy.props.BoolProperty(
        name="Overwrite Existing",
        description="Overwrite existing files with the same name",
        default=True
    )

    # ---------- Post Actions ----------

    open_images: bpy.props.BoolProperty(
        name="Open Image",
        description="Open generated sprite sheets in the Image Editor",
        default=False
    )

    open_output_directory: bpy.props.BoolProperty(
        name="Open Output Directory",
        description="Open the output directory after generation",
        default=False
    )

    clear_generated_images: bpy.props.BoolProperty(
        name="Clear Temporary Images",
        description="Remove generated intermediate images from Blender",
        default=True
    )
