"""
    This file is part of Sequence Bake.

    Sequence Bake is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or any later version.

    Sequence Bake is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with Sequence Bake. If not, see <http://www.gnu.org/licenses/>.

"""
import os
import re
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

IMAGE_EXTENSIONS = {
    ".png", ".jpg", ".jpeg", ".bmp", ".tif", ".tiff", ".tga",
    ".exr", ".hdr", ".cin", ".dpx", ".webp",
}

_UDIM_REGEX = __import__("re").compile(r"(?:^|[._-])(1\d{3}|2000)$")


class DirectoryImageItem(bpy.types.PropertyGroup):
    name: bpy.props.StringProperty(
        name="File Name",
        description="Image filename in the selected directory",
        default="",
    )
    filepath: bpy.props.StringProperty(
        name="File Path",
        description="Full path to the image file",
        default="",
        subtype='FILE_PATH',
    )
    udim: bpy.props.IntProperty(
        name="UDIM Tile",
        description="UDIM tile index (0 if non-UDIM)",
        default=0,
    )

def _get_udim_tile(filename):
    import os
    stem = os.path.splitext(filename)[0]
    match = _UDIM_REGEX.search(stem)
    if not match:
        return None
    tile = int(match.group(1))
    return tile if 1001 <= tile <= 2000 else None


def _get_udim_enum_items(self, context):
    """Dynamic items callback for the detected UDIM tiles dropdown."""
    raw = self.detected_udim_tiles
    if not raw:
        return [("NONE", "No UDIMs", "No UDIM tiles detected")]
    return [
        (tile, f"UDIM {tile}", f"Display images for UDIM tile {tile}")
        for tile in raw.split(",")
        if tile
    ]


def _on_udim_tile_changed(self, context):
    """Reset the active list index and update end_frame when switching UDIM tiles."""
    self.directory_images_index = 0
    if self.detected_udim_tiles and self.selected_udim_tile.isdigit():
        selected_udim = int(self.selected_udim_tile)
        count = sum(1 for item in self.directory_images if item.udim == selected_udim)
    else:
        count = len(self.directory_images)

    if count > 0:
        self.end_frame = count
        if self.start_frame > count:
            self.start_frame = 1


def populate_directory_image_list(props, context=None, preserve_order=True):
    """Scan the selected directory and populate directory_images (all UDIMs stored, filtered in UI)."""
    existing_order = {}
    if preserve_order and len(props.directory_images) > 0:
        existing_order = {
            item.name: idx for idx, item in enumerate(props.directory_images)
        }

    props.directory_images.clear()
    props.directory_images_index = 0

    directory = bpy.path.abspath(props.directory)
    if not directory or not os.path.isdir(directory):
        props.detected_udim_tiles = ""
        return

    try:
        subdirs = sorted(
            os.path.join(directory, name)
            for name in os.listdir(directory)
            if os.path.isdir(os.path.join(directory, name))
        )
    except OSError:
        subdirs = []

    target_dir = subdirs[0] if subdirs else directory

    try:
        files = os.listdir(target_dir)
    except OSError:
        props.detected_udim_tiles = ""
        return

    image_files = [
        f for f in files
        if os.path.splitext(f)[1].lower() in IMAGE_EXTENSIONS
    ]

    if not image_files:
        props.detected_udim_tiles = ""
        return

    buckets = {}
    for f in image_files:
        udim = _get_udim_tile(f)
        buckets.setdefault(udim, []).append(f)

    # ignore stray non-UDIM files if UDIM tiles exist
    if len(buckets) > 1 and None in buckets:
        del buckets[None]

    udim_keys = sorted(k for k in buckets.keys() if k is not None)

    if udim_keys:
        props.detected_udim_tiles = ",".join(str(k) for k in udim_keys)
        # Default to the first UDIM (e.g. 1001) if current selection is missing or invalid
        if props.selected_udim_tile not in [str(k) for k in udim_keys]:
            props.selected_udim_tile = str(udim_keys[0])
    else:
        props.detected_udim_tiles = ""

    natural_key = lambda f: tuple(int(p) if p.isdigit() else p for p in re.split(r"(\d+)", f.lower()))

    for udim_key in sorted(buckets.keys(), key=lambda x: (x is None, x)):
        tile_files = buckets[udim_key]
        if existing_order and any(f in existing_order for f in tile_files):
            tile_files.sort(
                key=lambda f: (
                    0 if f in existing_order else 1,
                    existing_order.get(f, 0),
                    natural_key(f),
                )
            )
        else:
            tile_files.sort(key=natural_key)

        for filename in tile_files:
            item = props.directory_images.add()
            item.name = filename
            item.filepath = os.path.join(target_dir, filename)
            item.udim = udim_key if udim_key is not None else 0

    if udim_keys and props.selected_udim_tile.isdigit():
        active_udim = int(props.selected_udim_tile)
        image_count = sum(1 for item in props.directory_images if item.udim == active_udim)
    else:
        image_count = len(props.directory_images)

    if image_count > 0:
        props.end_frame = image_count
        if props.start_frame > image_count:
            props.start_frame = 1


def _on_directory_updated(self, context):
    # Reset custom sort order when switching to a brand new directory
    populate_directory_image_list(self, context, preserve_order=False)


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

    # Paths:    
    directory: bpy.props.StringProperty(
        name="",
        description=(
            "Source and output directory for Image Sequence sprite sheets.\n"
            "If left blank, the material output path is used"
        ),
        default="",
        maxlen=1024,
        subtype='DIR_PATH',
        update=_on_directory_updated,
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
    
    # Directory Image List:
    detected_udim_tiles: bpy.props.StringProperty(
        name="Detected UDIM Tiles",
        description="Comma-separated list of detected UDIM tile indexes",
        default="",
    )
    selected_udim_tile: bpy.props.EnumProperty(
        name="UDIM Tile",
        description="Select which UDIM tile's image sequence to view and sort",
        items=_get_udim_enum_items,
        update=_on_udim_tile_changed,
    )
    directory_images: bpy.props.CollectionProperty(
        type=DirectoryImageItem,
        name="Directory Images",
        description="Ordered list of images found in the selected directory",
    )
    directory_images_index: bpy.props.IntProperty(
        name="Active Image Index",
        default=0,
        min=0,
    )

    # VSE:
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
    
    # Sprite Sheet Layout:
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

    # Frame Range:
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
    use_fixed_resolution: bpy.props.BoolProperty(
        name="Fixed Output Resolution",
        description="Constrain the sprite sheet to a fixed pixel resolution and split overflow frames across multiple sheets",
        default=False
    )
    output_width: bpy.props.IntProperty(
        name="Output Width",
        description="Maximum pixel width of each generated sprite sheet",
        default=1024,
        min=1
    )
    output_height: bpy.props.IntProperty(
        name="Output Height",
        description="Maximum pixel height of each generated sprite sheet",
        default=1024,
        min=1
    )
    
    # Output:
    sprite_sheet_is_alpha: bpy.props.BoolProperty(
        name="Use Alpha",
        description="Include alpha channel in the sprite sheet",
        default=True
    )
    sprite_sheet_image_format: bpy.props.EnumProperty(
        name="",
        description="Output image format",
        items=IMAGE_FORMATS,
        default="png"
    )
    file_name: bpy.props.StringProperty(
        name="",
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

    # Post Actions:
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
